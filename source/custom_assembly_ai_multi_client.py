# custom_factory.py
from __future__ import annotations

import datetime
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from typing import Final

from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingEvents,
    BeginEvent,
    TurnEvent,
    StreamingError,
    TerminationEvent,
    StreamingParameters,
)

from source.chat.message import Message
from source.chat.word import AudioStream
from source.dev_logger import debug


@dataclass
class AAIRunner:
    client: StreamingClient
    audio_queue: Queue[bytes | object]
    writer_thread: Thread
    sentinel: object


class CustomAssemblyAiMultiClientFactory:
    SAMPLE_RATE: Final[int] = 16_000
    BYTES_PER_SAMPLE: Final[int] = 2
    MIN_CHUNK_MS: Final[int] = 50
    MIN_CHUNK_BYTES: Final[int] = int(
        SAMPLE_RATE * (MIN_CHUNK_MS / 1000) * BYTES_PER_SAMPLE
    )

    def __init__(self, api_key: str, conversation_id: str) -> None:
        self._api_key = api_key
        self._conversation_id = conversation_id
        self._runners: dict[str, AAIRunner] = {}
        self.messages_queue: Queue[Message] = Queue()
        
    
    def get_all_runners(self) -> list[AAIRunner]:
        """Returns a list of all current AAIRunners."""
        return list(self._runners.values())
    
    def get_or_create_client(self, speaker: str) -> AAIRunner:
        if speaker in self._runners:
            return self._runners[speaker]
        runner = self._create_runner(speaker)
        self._runners[speaker] = runner
        return runner

    def detach_client(self, speaker: str, stop_client: bool = True) -> None:
        runner = self._runners.pop(speaker, None)
        if not runner:
            return
        # signal end‐of‐stream
        runner.audio_queue.put(runner.sentinel)
        runner.writer_thread.join(timeout=2)

    def close_all(self) -> None:
        for spk in list(self._runners):
            self.detach_client(spk)

    def _create_runner(self, speaker: str) -> AAIRunner:
        # 1) Create client, point it at the streaming host
        client = StreamingClient(
            StreamingClientOptions(
                api_key=self._api_key,
                # api_host="streaming.assemblyai.com",
            )
        )

        # 2) Register callbacks that debug so you can see when they fire
        def on_begin(_c: StreamingClient, e: BeginEvent) -> None:
            debug(f"[AAI][{speaker}] SESSION BEGIN: {e.id!r}")

        def on_turn(_c: StreamingClient, e: TurnEvent) -> None:
            if e.transcript and e.end_of_turn:
                for word in e.words:
                    if not word.word_is_final:
                        return
                debug(
                    f"[AAI][{speaker}] TURN → transcript={e.transcript!r}, "
                    f"end_of_turn={e.end_of_turn}"
                )
                msg = Message.from_assembly_ai(
                    event=e,
                    speaker=speaker,
                    conversation_id=self._conversation_id,
                    audio_stream=AudioStream(start_time_absolute=datetime.datetime.now()),
                )
                assert msg is not None, "Message must not be None"
                self.messages_queue.put(msg)
                debug(
                    f"[AAI][{speaker}] queued Message, queue size="
                    f"{self.messages_queue.qsize()}"
                )

        def on_error(_c: StreamingClient, err: StreamingError) -> None:
            debug(f"[AAI][{speaker}] ERROR: {err!r}")

        def on_term(_c: StreamingClient, e: TerminationEvent) -> None:
            debug(f"[AAI][{speaker}] TERMINATED after {e.audio_duration_seconds}s")

        client.on(StreamingEvents.Begin, on_begin)
        client.on(StreamingEvents.Turn, on_turn)
        client.on(StreamingEvents.Error, on_error)
        client.on(StreamingEvents.Termination, on_term)

        # 3) Open the websocket (this will trigger on_begin)
        client.connect(
            StreamingParameters(
                sample_rate=self.SAMPLE_RATE,
                format_turns=True,   # change to False to get un‐formatted partials earlier
            )
        )

        # 4) Spin up a writer thread that feeds the socket in 50 ms chunks
        audio_queue: Queue[bytes | object] = Queue()
        sentinel: object = object()

        def writer() -> None:
            debug(f"[AAI][{speaker}] writer thread started")
            buf = bytearray()
            while True:
                pkt = audio_queue.get()
                if pkt is sentinel:
                    break
                buf.extend(pkt)
                if len(buf) >= self.MIN_CHUNK_BYTES:
                    client.stream([bytes(buf)])
                    buf.clear()
            # flush remainder
            if buf:
                client.stream([bytes(buf)])
            debug(f"[AAI][{speaker}] writer stopping → disconnecting client")
            client.disconnect(terminate=True)

        thread = Thread(target=writer, daemon=True)
        thread.start()

        return AAIRunner(
            client=client,
            audio_queue=audio_queue,
            writer_thread=thread,
            sentinel=sentinel,
        )
    

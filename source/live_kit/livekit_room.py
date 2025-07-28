from __future__ import annotations

import asyncio
import time

import numpy as np
from livekit.rtc import Room, TrackKind
from livekit.rtc.audio_stream import AudioStream  # AsyncIterator[AudioFrameEvent]

from source.custom_assembly_ai_multi_client import CustomAssemblyAiMultiClientFactory, global_custom_assembly_ai_multi_client_factory
from source.dev_logger import debug
from source.live_kit.generate_livekit_token import make_token
from source.locations_and_config import (  config,
)

SAMPLE_RATE_IN = 48_000


class LiveKitRoom:
	def __init__(self, live_kit_url: str, live_kit_token: str) -> None:
		self.room = Room()
		self.custom_assembly_ai_multi_client_factory = global_custom_assembly_ai_multi_client_factory
		self.live_kit_url = live_kit_url
		self.live_kit_token = live_kit_token
		# self._setup(self.room)
		debug(f"[LiveKit] Initialized LiveKitRoom with URL: {self.live_kit_url}, Token: {self.live_kit_token}")
		
	@classmethod
	async def create(cls, live_kit_url: str, live_kit_jwt: str) -> LiveKitRoom:
		room = cls(live_kit_url = live_kit_url, live_kit_token = live_kit_jwt)
		await room._setup()
		debug(f"[LiveKit] Connected to LiveKit room: {room.room.name}")
		return room
	
	async def _setup(self):
		room = self.room  # type: ignore[assignment]
		@room.on("connected")
		def _on_connected() -> None:
			debug(f"[LiveKit] Python joined room: {room.name}")
			debug(f"[LiveKit] initial remotes: {list(room.remote_participants.keys())}")
		
		@room.on("participant_connected")
		def _on_pc(participant) -> None:
			debug(f"[LiveKit] participant_connected: {participant.identity}")
		
		@room.on("track_published")
		def _on_tp(pub, participant) -> None:
			debug(f"[LiveKit] track_published {pub.kind} from {participant.identity} (sid={pub.sid})")
		
		@room.on("track_subscription_failed")
		def _on_fail(participant, sid, err) -> None:
			debug(f"[LiveKit] track_subscription_failed: {sid} {err}")
		
		@room.on("track_subscribed")
		def handle_track(track, pub, participant) -> None:
			debug(f"[LiveKit] track_subscribed: {participant.identity} ")
			
			if track.kind != TrackKind.KIND_AUDIO:
				return
			
			speaker = participant.identity
			runner = self.custom_assembly_ai_multi_client_factory.get_or_create_client(speaker = speaker)
			
			audio_stream = AudioStream(track, sample_rate = self.custom_assembly_ai_multi_client_factory.SAMPLE_RATE, num_channels = 1)
		
			async def pump() -> None:
				try:
					t=time.time()
					async for evt in audio_stream:
						raw = bytes(evt.frame.data)
						runner.audio_queue.put(raw)
						if time.time() - t > 1:
							t = time.time()
							volume = np.frombuffer(raw, dtype = np.int16).max()
							debug(f"[LiveKit] Audio frame from {speaker} ({pub.sid}), volume: {volume:.2f}")
						# down = downsample_pcm16(raw, SAMPLE_RATE_IN, self.custom_assembly_ai_multi_client_factory.SAMPLE_RATE)
						# runner.audio_queue.put(down) Hopefully this works now.
				finally:
					runner.audio_queue.put(runner.sentinel)  # type: ignore[attr-defined]
			
			debug(f"[LiveKit] Starting audio pump for {speaker} ({pub.sid})")
			asyncio.create_task(pump())
		
		@room.on("track_unsubscribed")
		def unsubscribed(_track, pub, participant) -> None:
			debug(f"[LiveKit] track_unsubscribed from {participant.identity} ({pub.sid})")
			# when a track goes away, shut down its runner (if any)
			self.custom_assembly_ai_multi_client_factory.detach_client(speaker = participant.identity)
	
	async def run(self):
		
		try:
			debug("[LiveKit] Connecting to LiveKit…")
			await self.room.connect(self.live_kit_url, self.live_kit_token)
			debug(f"[LiveKit] Connected—awaiting audio… to {self.room.name}")
			await asyncio.Event().wait()
		except asyncio.CancelledError:
			pass
		except Exception as e:
			debug("[LiveKit] Connection failed:", e)
		finally:
			await self.room.disconnect()
			# Ensure all runners stopped
			for runner in self.custom_assembly_ai_multi_client_factory.get_all_runners():
				runner.audio_queue.put(runner.sentinel)  # type: ignore[attr-defined]
			for runner in self.custom_assembly_ai_multi_client_factory.get_all_runners():
				await asyncio.to_thread(runner.writer_thread.join, timeout=2)


 

async def create_and_run_livekit_room():
	debug("[LiveKit] Creating LiveKitRoom instance…")
	livekit_room = await LiveKitRoom.create(
		live_kit_url = config.livekit_ws_url,
		live_kit_jwt =make_token(identity=config.assembly_ai_listener_name, room=config.livekit_room_name, hours=6),#  live_kit_jwt,
	)
	await livekit_room.run()

if __name__ == "__main__":
	asyncio.run(create_and_run_livekit_room())
	# livekit_room = LiveKitRoom(
	# 	live_kit_url = live_kit_url,
	# 	live_kit_token = live_kit_jwt,
	# 	assemblyai_api_key = assemblyai_api_key,
	# )
	# asyncio.run(livekit_room.run())

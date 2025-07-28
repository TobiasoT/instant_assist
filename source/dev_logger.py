from __future__ import annotations

import inspect
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple



class DevLogger:
    """
    A convenience logger mimicking your old debug(), measure_time(), and mexit()
    functions, but using the standard `logging` framework.

    Parameters
    ----------
    name : str
        Name of the logger (defaults to "DevLogger").
    to_stdout : bool
        If True, logs will be emitted to standard output.
    to_file : bool
        If True, logs will also be written to `file_path`.
    file_path : str | Path | None
        Path for the log file when `to_file` is True.
    level : int
        Logging level (defaults to logging.DEBUG).
    """

    _TIME_BUF: Dict[int, float] = {}

    def __init__(
        self,
        name: str = "DevLogger",
        *,
        to_stdout: bool = True,
        to_file: bool = False,
        file_path: str | Path | None = None,
        level: int = logging.DEBUG,
    ) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        fmt = logging.Formatter("%(message)s")
        if to_stdout:
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(fmt)
            self.logger.addHandler(sh)
        if to_file:
            if file_path is None:
                raise ValueError("file_path must be supplied when to_file=True")
            fh = logging.FileHandler(str(file_path), encoding="utf-8")
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)

    # ──────────────────────────────────────────────────────────────────────── #
    # Internal helpers                                                       #
    # ──────────────────────────────────────────────────────────────────────── #
    @staticmethod
    def _stack_frames(skip: int, depth: int) -> List[inspect.FrameInfo]:
        """
        Return a list of `depth+1` frames from the call stack,
        skipping the first `skip` frames (to remove logger internals).
        """
        return inspect.stack()[skip : skip + depth + 1]

    @staticmethod
    def _fmt_line_no(n: int) -> str:
        """Return a 3-character right-aligned line number, padded with '_'."""
        s = str(n)
        return "_" * max(0, 3 - len(s)) + s

    def _fmt_header(self, msg: str, frame: inspect.FrameInfo) -> str:
        """
        One-line header with full file path (clickable in IDEs) and line number.
        If the message is long or contains quotes, emits a multi-line style.
        """
        file_path, line = frame.filename, frame.lineno
        if len(msg) > 500 or '"' in msg:
            return f'{self._fmt_line_no(line)}: File "{file_path}", line {line}:\n{msg}'
        padded = msg.ljust(max(60 - len(msg), 0) + len(msg))
        return (
            f'{self._fmt_line_no(line)}: {padded}'
            f'\tFile "{file_path}", line {line}'
        )

    @staticmethod
    def _fmt_trace(frames: List[inspect.FrameInfo]) -> str:
        """
        Produce a mini-traceback of the given frames, in the form:
          File "path", line N, in function
        """
        lines: List[str] = []
        for fr in frames:
            lines.append(
                f'  File "{fr.filename}", line {fr.lineno}, in {fr.function}'
            )
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────── #
    # Public API                                                             #
    # ──────────────────────────────────────────────────────────────────────── #
    def debug(self, *message: Any, depth: int = 0) -> None:
        """
        Log a debug-level message.

        Parameters
        ----------
        *message : Any
            One or more objects to stringify and join with commas.
        depth : int
            Number of additional stack frames to include in the mini-trace.
            0 = only the immediate file+line; 1 = include the caller; etc.
        """
        frames = self._stack_frames(skip=2, depth=max(0, depth))
        header = self._fmt_header(", ".join(map(str, message)), frames[0])
        trace = self._fmt_trace(frames[1:])
        output = f"{header}\n{trace}" if trace else header
        self.logger.debug(output)

    def measure_time(
        self,
        text: str | None = "",
        *,
        id: int = 0,
        print_if_greater_than: float = 0.0,
        depth: int = 0,
    ) -> None:
        """
        Measure elapsed time between calls with the same `id`.

        On the first call with `id`, stores a timestamp. On the second,
        computes the delta and logs it if >= print_if_greater_than.

        Parameters
        ----------
        text : str | None
            Optional label to include with the timing.
        id : int
            Identifier for pairing start/end calls.
        print_if_greater_than : float
            Minimum duration (in seconds) to actually log.
        depth : int
            Number of additional stack frames to include in the mini-trace.
        """
        now = time.time()
        if id not in self._TIME_BUF:
            self._TIME_BUF[id] = now
            return

        elapsed = now - self._TIME_BUF[id]
        self._TIME_BUF[id] = now
        if elapsed < print_if_greater_than or text in ("no print", None, False):
            return

        frames = self._stack_frames(skip=2, depth=max(0, depth))
        msg = f"{elapsed:.5f} sec (ID {id})"
        if text:
            msg += f" → {text}"
        header = self._fmt_header(msg, frames[0])
        trace = self._fmt_trace(frames[1:])
        output = f"{header}\n{trace}" if trace else header
        self.logger.debug(output)

    def mexit(self, *message: Any, depth: int = 0, code: int =0) -> None:
        """
        Log an error-level message and exit the process.

        Parameters
        ----------
        *message : Any
            Objects to stringify and join as the exit message.
        depth : int
            Stack-trace depth for the mini-trace.
        code : int
            Exit code to use with sys.exit().
        """
        frames = self._stack_frames(skip=2, depth=max(0, depth))
        text = ", ".join(map(str, message)) or "mexit called"
        header = self._fmt_header(f"Mexit: {text}", frames[0])
        self.logger.debug(header)
        sys.exit(code)



global_logger = DevLogger()
debug = global_logger.debug
mexit = global_logger.mexit
measure_time = global_logger.measure_time

if __name__ == "__main__":
    
    debug("DevLogger initialized", depth=1)
    def test_logger(depth: int = 1) -> None:
        """
        Test the logger functionality.
        """
        debug("This is a debug message", depth=3)
        measure_time("Starting measurement", id=1)
        time.sleep(0.5)
        measure_time("Finished measurement", id=1, print_if_greater_than=0.1)
        if depth == 0:
            mexit("Exiting with no error", depth=0)
        else:
            test_logger(depth - 1)
            
    test_logger(depth=2)

"""Portable, dependency-free interprocess file lock.

Used to serialize read-modify-write cycles against shared on-disk config files
(``config.yaml``, ``.env``) so two backend processes — e.g. a running gateway and
a parallel dev/CLI session — cannot lose each other's updates or produce
duplicate entries.

Uses ``fcntl.flock`` on POSIX and ``msvcrt.locking`` on Windows. Both release
automatically when the owning process exits, so a crash never leaves a stale
lock behind. Best-effort by design: if no backend is available the lock degrades
to a no-op rather than raising, so callers are never broken by the locking layer.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import fcntl  # type: ignore

    _BACKEND = "fcntl"
except ImportError:  # pragma: no cover - platform dependent
    fcntl = None  # type: ignore
    try:
        import msvcrt  # type: ignore

        _BACKEND = "msvcrt"
    except ImportError:  # pragma: no cover - platform dependent
        msvcrt = None  # type: ignore
        _BACKEND = "noop"


@contextlib.contextmanager
def interprocess_lock(target: Path | str) -> Iterator[None]:
    """Hold an exclusive lock on ``<target>.lock`` for the duration of the block.

    The lock file sits next to the target and is never deleted (deleting it would
    reintroduce a race); it simply acts as the lock token. Blocks until the lock
    is acquired.
    """
    lock_path = Path(str(target) + ".lock")
    try:
        handle = open(lock_path, "a+")  # noqa: SIM115 - released in finally
    except OSError:
        # If we cannot even open the lock file, do not block the operation.
        logger.debug("interprocess_lock: cannot open %s; proceeding unlocked", lock_path, exc_info=True)
        yield
        return

    try:
        _acquire(handle)
        try:
            yield
        finally:
            _release(handle)
    finally:
        with contextlib.suppress(OSError):
            handle.close()


def _acquire(handle) -> None:
    if _BACKEND == "fcntl":
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    elif _BACKEND == "msvcrt":
        handle.seek(0)
        # LK_LOCK retries internally for ~10s then raises; loop until acquired.
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                return
            except OSError:
                continue
    # noop backend: nothing to do.


def _release(handle) -> None:
    try:
        if _BACKEND == "fcntl":
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        elif _BACKEND == "msvcrt":
            handle.seek(0)
            with contextlib.suppress(OSError):
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:  # pragma: no cover - defensive
        logger.debug("interprocess_lock: release failed", exc_info=True)

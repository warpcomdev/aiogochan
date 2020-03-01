"""Channel type implements golang-like channels for python async"""

import asyncio
from typing import Tuple, Optional, Generic, Protocol, TypeVar, cast
from collections import deque


class Closed(Exception):
    """Closed exception is raised when pushing to a closed channel"""


# pylint: disable=invalid-name
T = TypeVar('T')


class _onceProtocol(Protocol[T]):
    """Once is a protocol for values that can be set or get once"""
    async def __aenter__(self) -> None:
        """Implements AsyncContextManager"""

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        """Implements AsyncContextManager"""

    def used(self) -> bool:
        """Used returns True if the object has already been get or set"""

    async def get_once(self, index: int) -> Optional[T]:
        """Get the initial value, once"""

    async def set_once(self, index: int, value: Optional[T]):
        """Set the value, once"""


class _once(Generic[T]):
    """Once is a wrapper for a value that can be set or get once"""
    def __init__(self, value: Optional[T] = None):
        """Init the wrapper with an optional value"""
        self.value = value

    async def __aenter__(self):
        """__aenter__ implements Context manager protocol"""

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        """__aexit__ implements Context manager protocol"""
        return False

    # pylint: disable=no-self-use
    def used(self) -> bool:
        """Used returns True if the object has already been get or set"""
        return False

    # pylint: disable=unused-argument
    async def get_once(self, index: int) -> Optional[T]:
        """Get the initial value, once"""
        return self.value

    # pylint: disable=unused-argument
    async def set_once(self, index: int, value: Optional[T]):
        """Set the value, once"""
        self.value = value


class Channel(Generic[T]):
    """buffered channel"""
    def __init__(self, size: int):
        """Initialize a channel with the given buffer size"""
        self._queue = deque(cast(Tuple[Optional[T], ...], tuple()),
                            maxlen=size)
        self._size = size
        self._lock = asyncio.Lock()
        self._pushers = asyncio.Condition(self._lock)
        self._poppers = asyncio.Condition(self._lock)
        self._done = False

    async def _push(self, once: _onceProtocol[T], index: int):
        """Push an item to the channel, raise Closed if closed"""
        async with self._lock:
            while len(self._queue) >= self._size and not self._done:
                # Test if the value is still present.
                async with once:
                    if once.used():
                        self._pushers.notify()
                        return
                await self._pushers.wait()
            if self._done:
                raise Closed()
            async with once:
                if not once.used():
                    # Consume the value and notify the poppers.
                    self._queue.append(await once.get_once(index))
                    self._poppers.notify()
                else:  # give up our slot
                    self._pushers.notify()

    async def push(self, item: T):
        """Push an item to the channel, raise Closed if closed"""
        await self._push(_once(item), 0)

    async def _pop(self, once: _onceProtocol[T], index: int):
        """Pop an item from the channel, None if closed"""
        async with self._lock:
            while len(self._queue) <= 0 and not self._done:
                async with once:
                    # If value no longer needed, propagate notify.
                    if once.used():
                        self._poppers.notify()
                        return
                await self._poppers.wait()
            async with once:
                if not once.used():
                    value = self._queue.popleft() if len(
                        self._queue) > 0 else None
                    await once.set_once(index, value)
                    self._pushers.notify()
                else:
                    self._poppers.notify()
            return once

    async def pop(self) -> Optional[T]:
        """Pop an item from the channel, None if Valueclosed"""
        return (await self._pop(_once(), 0)).value

    async def _notify(self):
        """Notify all waiting coros"""
        async with self._lock:
            self._pushers.notify_all()
            self._poppers.notify_all()

    async def __aiter__(self):
        """Iterate on the channel until it is closed"""
        while True:
            item = await self.pop()
            if item is None:
                return
            yield item

    async def __aenter__(self):
        """__aenter__ implements context manager"""
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        """__aexit__ implements context manager"""
        await self.close()

    async def close(self):
        """Close the channel"""
        async with self._lock:
            self._done = True
            self._pushers.notify_all()
            self._poppers.notify_all()

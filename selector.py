"""Selector implements go-like select for channels"""

import asyncio
from typing import Tuple, TypeVar, Any

from channel import Channel

# pylint: disable=invalid-name
T = TypeVar('T')


class _onceSelect(asyncio.Lock):
    """Select_Once can be pushed or popped once"""
    def __init__(self):
        """Init the wrapper with an optional value"""
        super().__init__()
        self._index = -1
        self._values = list()
        self._set = False
        self._chans = list()

    async def _notify(self, index: int):
        """Notify all channels once the selector is done"""
        for idx, chan in enumerate(self._chans):
            if idx != index:
                # pylint: disable=protected-access
                await chan._notify()

    def used(self) -> bool:
        """Used returns True if the object has already been get or set"""
        return self._index >= 0

    async def get_once(self, index: int) -> Any:
        """Get the initial value, once"""
        self._index = index
        await self._notify(index)
        return self._values[index]

    async def set_once(self, index: int, value: Any):
        """Set the value, once"""
        self._index = index
        self._values[index] = value
        await self._notify(index)
        self._set = True

    def add(self, chan: Channel[T], value: T) -> int:
        """Add the channel and value to the list"""
        index = len(self._values)
        if self._index < 0:
            self._values.append(value)
            self._chans.append(chan)
        return index

    def gather(self) -> Tuple[int, Any]:
        """
        Return the index and value of the channel that won.
        If the operation that won is a push, then the value
        is just the boolean 'True'
        """
        value = self._values[self._index]
        return (self._index, value if self._set else True)


class Selector:
    """Selector manages operations on several channels"""
    def __init__(self):
        self._once = _onceSelect()
        self._tasks = list()

    def push(self, chan: Channel[T], item: T) -> int:
        """Adds chan.push(item) to selector"""
        index = self._once.add(chan, item)
        # pylint: disable=protected-access
        self._tasks.append(chan._push(self._once, index))
        return index

    def pop(self, chan: Channel[T]) -> int:
        """Adds chan.pop() to selector"""
        index = self._once.add(chan, None)
        # pylint: disable=protected-access
        self._tasks.append(chan._pop(self._once, index))
        return index

    async def gather(self) -> Tuple[int, Any]:
        """Gather the result from the elected channels"""
        await asyncio.gather(*self._tasks)
        return self._once.gather()

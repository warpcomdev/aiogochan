"""WaitGroup implements golang-like wait groups"""

import asyncio
from typing import Awaitable


class WaitGroup:
    """Async waitgroup"""
    def __init__(self):
        """Initialize workgroup"""
        self._cond = asyncio.Condition()
        self._jobs = 0
        self._tasks = list()

    async def _go(self, coro: Awaitable):
        """_Go awaits for the coro, and releases the task"""
        try:
            await coro
        finally:
            async with self._cond:
                self._jobs -= 1
                if self._jobs == 0:
                    self._cond.notify_all()

    # pylint: disable=invalid-name
    async def go(self, coro):
        """Go schedules the coroutine in the loop"""
        async with self._cond:
            self._jobs += 1
            self._tasks.append(asyncio.ensure_future(self._go(coro)))

    async def wait(self):
        """Wait for all tasks to complete"""
        async with self._cond:
            while self._jobs > 0:
                await self._cond.wait()
        await asyncio.gather(*self._tasks)
        for task in self._tasks:
            if task.exception() is not None:
                raise task.Exception

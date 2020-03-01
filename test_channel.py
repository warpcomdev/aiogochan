"""Test channels"""

import unittest
import asyncio
from typing import Sequence, List

import aiounittest

from channel import Channel


class TestChannel(aiounittest.AsyncTestCase):
    """Test channel"""
    async def test_push_nowait(self):
        """Push up to channel size should not block"""
        async with Channel(2) as chan:
            await chan.push(10)
            await chan.push(11)
        self.assertEqual(await chan.pop(), 10)
        self.assertEqual(await chan.pop(), 11)

    async def test_push_wait(self):
        """Push over channel size should wait"""
        result = []

        async def popper(chan: Channel):
            async for item in chan:
                result.append(item)

        async with Channel(2) as chan:
            task = asyncio.ensure_future(popper(chan))
            await chan.push(12)
            await chan.push(11)
            await chan.push(10)
        await task
        self.assertEqual(result, [12, 11, 10])

    @staticmethod
    async def pusher(chan, items: Sequence[int]):
        """Push all items in list"""
        for item in items:
            await chan.push(item)

    @staticmethod
    async def popper(chan, result: List[int]):
        """Pop all items from list"""
        async for item in chan:
            result.append(item)

    async def test_multi(self):
        """Test multiple push and pops"""
        result = []
        async with Channel(2) as chan:

            async def pushers(chan: Channel):
                await asyncio.gather(
                    TestChannel.pusher(chan, [1, 2, 3, 4, 5]),
                    TestChannel.pusher(chan, [6, 7, 8, 9, 10]),
                    TestChannel.pusher(chan, [11, 12, 13, 14, 15]),
                    TestChannel.pusher(chan, [16, 17, 18, 19, 20]),
                    TestChannel.pusher(chan, [21, 22, 23, 24, 25]),
                    TestChannel.pusher(chan, [26, 27, 28, 29, 30]),
                    TestChannel.pusher(chan, [31, 32, 33, 34, 35]),
                    TestChannel.pusher(chan, [36, 37, 38, 39, 40]),
                    TestChannel.pusher(chan, [41, 42, 43, 44, 45]),
                )
                await chan.close()

            async def poppers(chan: Channel):
                await asyncio.gather(
                    TestChannel.popper(chan, result),
                    TestChannel.popper(chan, result),
                    TestChannel.popper(chan, result),
                    TestChannel.popper(chan, result),
                    TestChannel.popper(chan, result),
                )

            await asyncio.gather(pushers(chan), poppers(chan))
        self.assertEqual(frozenset(result), frozenset(range(1, 46)))


if __name__ == "__main__":
    unittest.main()

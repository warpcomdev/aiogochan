"""Test selector"""

import unittest
from typing import List

import aiounittest

from channel import Channel
from wg import WaitGroup


class TestWaitGroup(aiounittest.AsyncTestCase):
    """Test WaitGroup"""
    async def test_empty(self):
        """Empty wait group should return inmediately"""
        wgroup = WaitGroup()
        await wgroup.wait()

    async def test_tasks(self):
        """Test several tasks running in parallel"""
        result = list()

        async def task(value: int):
            result.append(value)

        wgroup = WaitGroup()
        await wgroup.go(task(3))
        await wgroup.go(task(5))
        await wgroup.go(task(7))
        await wgroup.wait()
        self.assertEqual(frozenset(result), frozenset((3, 5, 7)))

    async def test_chain(self):
        """Test a chain of events"""
        chan = Channel(1)
        data = list()

        async def save(chan: Channel, data: List):
            data.append(await chan.pop())

        wgroup = WaitGroup()
        await wgroup.go(save(chan, data))
        await wgroup.go(chan.push(5))
        await wgroup.wait()
        self.assertEqual(data, [5])


if __name__ == "__main__":
    unittest.main()

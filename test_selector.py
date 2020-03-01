"""Test selector"""

import unittest
import aiounittest

from channel import Channel
from selector import Selector


class TestSelector(aiounittest.AsyncTestCase):
    """Test Selector"""
    async def test_select_closed(self):
        """Select on a closed channel should return None"""
        sel = Selector()
        chan = Channel(2)
        await chan.close()
        sel.pop(chan)
        val = await sel.gather()
        self.assertEqual(val, (0, None))

    async def test_select_pop(self):
        """Popping on two channels should return the one with data"""
        sel1, sel2 = Selector(), Selector()
        async with Channel(1) as chan1, Channel(1) as chan2:
            # Pop from C2 first
            sel1.pop(chan1)
            sel1.pop(chan2)
            await chan2.push(10)
            val = await sel1.gather()
            self.assertEqual(val, (1, 10))
            # Now pop from C1
            sel2.pop(chan1)
            sel2.pop(chan2)
            await chan1.push(20)
            val = await sel2.gather()
            self.assertEqual(val, (0, 20))

    async def test_select_push(self):
        """Pushing on two channels should return the one with room"""
        sel = Selector()
        async with Channel(1) as chan1, Channel(1) as chan2:
            # Push to C2 first
            sel.push(chan1, 10)
            sel.push(chan2, 20)
            await chan1.push(11)
            val = await sel.gather()
            await chan1.close()
            self.assertEqual(val, (1, True))
            self.assertEqual(await chan1.pop(), 11)
            self.assertEqual(await chan1.pop(), None)
            self.assertEqual(await chan2.pop(), 20)

    async def test_select_both_pop(self):
        """Push and popping should perform the first available op"""
        sel1, sel2 = Selector(), Selector()
        async with Channel(1) as chan1, Channel(1) as chan2:
            # c1 will be full (cannot push)
            await chan1.push(10)
            await chan2.push(20)
            sel1.push(chan1, 20)
            sel1.pop(chan2)
            val = await sel1.gather()
            self.assertEqual(val, (1, 20))
            # c2 will be full (cannot push)
            await chan2.push(30)
            sel2.pop(chan1)
            sel2.push(chan2, 40)
            val = await sel2.gather()
            self.assertEqual(val, (0, 10))

    async def test_select_both_push(self):
        """Push and popping should perform the first available op"""
        sel1, sel2 = Selector(), Selector()
        async with Channel(1) as chan1, Channel(1) as chan2:
            # c1 will be empty (cannot pop)
            sel1.pop(chan1)
            sel1.push(chan2, 10)
            val = await sel1.gather()
            self.assertEqual(val, (1, True))
            # c2 will be empty (cannot pop)
            self.assertEqual(await chan2.pop(), 10)
            sel2.push(chan1, 20)
            sel2.pop(chan2)
            val = await sel2.gather()
            self.assertEqual(val, (0, True))


if __name__ == "__main__":
    unittest.main()

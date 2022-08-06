import unittest
import itertools
import caltime
import tzresolve
from event import *
from test_mock import mock_class


class TestMerge(unittest.TestCase):

    def test_event_state_merge(self):
        XSTATE = EventState('XSTATE')
        for t in [TODO, CANCELLED, DONE, XSTATE]:
            self.assertEqual(t, t.merge(t))

        def dtest(expected, l, r):
            self.assertEqual(expected, l.merge(r))
            self.assertEqual(expected, r.merge(l))

        for t in [CANCELLED, TODO, XSTATE]:
            dtest(DONE, DONE, t)

        for t in [TODO, XSTATE]:
            dtest(XSTATE, XSTATE, t)


    def test_event_string_list_merge(self):
        e = EventStringList()
        self.assertEqual(e, e.merge(e))

        one = EventStringList(['1'])
        self.assertEqual(one, one.merge(one))
        self.assertEqual(one, one.merge(e))
        self.assertEqual(one, e.merge(one))

        self.assertEqual(0, len(e))
        self.assertEqual(1, len(one))

        two = EventStringList(['2', 'foo'])
        self.assertEqual(two, two.merge(two))
        self.assertEqual(two, two.merge(e))
        self.assertEqual(two, e.merge(two))

        for l,r in [(one, two), (two, one)]:
            m = l.merge(r)
            self.assertEqual(3, len(m))
            for n in ['1', '2', 'foo']:
                self.assertTrue(n in m)

        three = EventStringList(['3', 'foo', 'bar'])

        for l,r in [(two, three), (three, two)]:
            m = l.merge(r)
            self.assertEqual(4, len(m))
            for n in ['2', '3', 'foo', 'bar']:
                self.assertTrue(n in m)


class TestEvent(unittest.TestCase):

    def test_nothing(self):
        pass

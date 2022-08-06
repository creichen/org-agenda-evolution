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


cconv = caltime.CalConverter(tzresolve.TZResolver(None))

def daily(count=None):
    return cconv.daily_recurrence(count=count)

def dt(s):
    return cconv.time_from_str(s)

def mk_event(evid, name, start, end, **args):
    ev = EventRepeater(evid, name, start)
    ev.end = end
    for k, v in args.items():
        setattr(ev, k, v)
    return ev


class TestEvent(unittest.TestCase):

    def test_nonrecur(self):
        ev = mk_event('I0', 'Test',
                      start=dt('2022-01-01T10:00/UTC'),
                      end=dt(  '2022-01-01T11:00/UTC'),
                      recurrences=[])

        evs = list(ev.in_interval(start=None, end=dt('2022-01-03T15:00/UTC')))
        self.assertEqual(1, len(evs))
        seq_expected = 0
        for e in evs:
            seq_expected += 1
            self.assertEqual(seq_expected, e.sequence_nr)
            self.assertEqual('I0', e.event_id)
            self.assertEqual('Test', e.name)
            self.assertEqual(seq_expected, e.start.day)
            self.assertEqual(seq_expected, e.end.day)
            self.assertEqual(10, e.start.hour)
            self.assertEqual(11, e.end.hour)

    def test_recur_start_window(self):
        ev = mk_event('I0', 'Test',
                      start=dt('2022-01-01T10:00/UTC'),
                      end=dt(  '2022-01-01T11:00/UTC'),
                      recurrences=[daily()])

        evs = list(ev.in_interval(start=None, end=dt('2022-01-03T15:00/UTC')))
        self.assertEqual(3, len(evs))
        seq_expected = 0
        for e in evs:
            seq_expected += 1
            self.assertEqual(seq_expected, e.sequence_nr)
            self.assertEqual('I0', e.event_id)
            self.assertEqual('Test', e.name)
            self.assertEqual(seq_expected, e.start.day)
            self.assertEqual(seq_expected, e.end.day)
            self.assertEqual(10, e.start.hour)
            self.assertEqual(11, e.end.hour)

    def test_recur_later_window(self):
        ev = mk_event('I0', 'Test',
                      start=dt('2022-01-01T10:00/UTC'),
                      end=dt(  '2022-01-01T11:00/UTC'),
                      recurrences=[daily(20)])

        evs = list(ev.in_interval(start=dt('2022-01-17T00:00/UTC'), end=dt('2022-01-23T15:00/UTC')))
        self.assertEqual(4, len(evs))

        seq_expected = 16
        for e in evs:
            seq_expected += 1
            self.assertEqual(seq_expected, e.sequence_nr)
            self.assertEqual('I0', e.event_id)
            self.assertEqual('Test', e.name)
            self.assertEqual(seq_expected, e.start.day)
            self.assertEqual(seq_expected, e.end.day)
            self.assertEqual(10, e.start.hour)
            self.assertEqual(11, e.end.hour)


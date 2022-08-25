# This file is Copyright (C) 2022 Christoph Reichenbach
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
#   Free Software Foundation, Inc.
#   59 Temple Place, Suite 330
#   Boston, MA  02111-1307
#   USA
#
# The author can be reached as "creichen" at the usual gmail server.

from __future__ import annotations

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

def noswap(x, y):
    return (x, y)

def doswap(x, y):
    return (y, x)


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

    def test_diff_trivial(self):
        ev0 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       recurrences=[])

        self.assertEqual({}, ev0.diff(ev0))

    def test_diff_merge(self):
        ev0 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='Potato salad',
                       status=TODO,
                       recurrences=[])

        ev1 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       status=DONE,
                       recurrences=[])

        for el, er in [(ev0, ev1), (ev1, ev0)]:
            diff = el.diff(er)
            self.assertEqual((True, DONE), diff['status'])
            self.assertEqual((True, 'Potato salad'), diff['description'])
            self.assertEqual(2, len(diff))

    def test_diff_conflict(self):
        ev0 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='A',
                       status=TODO,
                       recurrences=[])

        ev1 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='B',
                       status=TODO,
                       recurrences=[])

        for el, er, swap_if_needed in [(ev0, ev1, noswap), (ev1, ev0, doswap)]:
            diff = el.diff(er)
            self.assertEqual((False, swap_if_needed("A", "B")), diff['description'])
            self.assertEqual(1, len(diff))

    def test_merge_trivial(self):
        ev0 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       recurrences=[])

        m = ev0.merge(ev0)
        self.assertEqual(None, m.get_conflict_event())
        self.assertEqual(dt('2022-01-01T10:00/UTC'), m.start)
        self.assertEqual(dt('2022-01-01T11:00/UTC'), m.end)
        self.assertEqual('I0', m.event_id)
        self.assertEqual('Test', m.name)

    def test_merge_merge(self):
        ev0 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='Potato salad',
                       status=TODO,
                       recurrences=[])

        ev1 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       status=DONE,
                       recurrences=[])

        m = ev0.merge(ev1)
        self.assertEqual(None, m.get_conflict_event())
        self.assertEqual(dt('2022-01-01T10:00/UTC'), m.start)
        self.assertEqual(dt('2022-01-01T11:00/UTC'), m.end)
        self.assertEqual('I0', m.event_id)
        self.assertEqual('Test', m.name)
        self.assertEqual('Potato salad', m.description)
        self.assertEqual(DONE, m.status)

    def test_merge_conflict(self):
        ev0 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='A',
                       status=TODO,
                       recurrences=[])

        ev1 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='B',
                       status=DONE,
                       recurrences=[])

        m = ev0.merge(ev1, explain_conflicts=False)
        self.assertEqual(dt('2022-01-01T10:00/UTC'), m.start)
        self.assertEqual(dt('2022-01-01T11:00/UTC'), m.end)
        self.assertEqual('I0', m.event_id)
        self.assertEqual('Test', m.name)
        self.assertEqual('A', m.description)
        self.assertEqual(DONE, m.status)
        self.assertIs(ev1, m.get_conflict_event())

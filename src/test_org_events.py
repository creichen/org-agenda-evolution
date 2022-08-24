from __future__ import annotations

import io
import unittest
import itertools
import caltime
import tzresolve
import event
from org_events import *
from test_mock import mock_class

cconv = caltime.CalConverter(tzresolve.TZResolver(None))

def daily(count=None):
    return cconv.daily_recurrence(count=count)

def dt(s):
    return cconv.time_from_str(s)

def mk_event(evid : str, name : str, start, end, **args):
    ev = event.EventRepeater(evid, name, start)
    ev.end = end
    for k, v in args.items():
        setattr(ev, k, v)
    return ev

class TestUnparse(unittest.TestCase):

    @staticmethod
    def mk_unparser(**kwd):
        if 'local_timezone' not in kwd:
            kwd['local_timezone'] = None
        if 'emit_debug' not in kwd:
            kwd['emit_debug'] = False

        def fgen():
            f = io.StringIO()
            u = OrgEventUnparser(f, **kwd)
            return (u, f.getvalue)
        return fgen

    # ----------------------------------------
    def test_simple(self):
        '''Simple event unparsing'''
        ev = mk_event('I0', 'Test',
                      start=dt('2022-01-01T10:00/UTC'),
                      end=dt(  '2022-01-01T11:00/UTC'),
                      recurrences=[])
        ugen = TestUnparse.mk_unparser(today=dt('2022-01-01'))
        oup, getstr = ugen()
        oup.unparse_event(ev)
        self.assertEqual(
            '''** TODO Test
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :CALEVENT-UID: I0
  :END:

''', getstr())

    # ----------------------------------------
    def test_conflict(self):
        '''Unparse an event generated from a conflict'''
        ev0 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='A',
                       status=event.TODO,
                       recurrences=[])

        ev1 = mk_event('I0', 'Test',
                       start=dt('2022-01-01T10:00/UTC'),
                       end=dt(  '2022-01-01T11:00/UTC'),
                       description='B',
                       status=event.DONE,
                       recurrences=[])

        ev = ev0.merge(ev1, explain_conflicts=False)
        ugen = self.mk_unparser(today=dt('2022-01-01'))
        oup, getstr = ugen()
        oup.unparse_event(ev)
        self.assertEqual(
            '''** DONE Test
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :CALEVENT-UID: I0
  :END:
A
*** DONE !CONFLICT! Test
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :CALEVENT-UID: I0
  :END:
B
''', getstr())


class TestParse(unittest.TestCase):

    @staticmethod
    def parser(**kwd):
        if 'local_timezone' not in kwd:
            kwd['local_timezone'] = None
        if 'emit_debug' not in kwd:
            kwd['emit_debug'] = False

        return OrgEventParser(**kwd)

    # ----------------------------------------
    def test_simple(self):
        cals = TestParse.parser().loads('''* CAL0
  :PROPERTIES:
  :CAL-UID: C0
  :END:
** TODO Test
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :CALEVENT-UID: I0
  :END:
''')
        self.assertEqual(1, len(cals))
        c = cals['C0']
        self.assertEqual('CAL0', c.name)
        self.assertEqual(1, len(c.events))
        self.assertEqual('C0', c.uid)
        e = c.events['I0'] # implicitly assert existence below:
        self.assertEqual('I0', e.event_id)
        self.assertEqual('Test', e.name)
        self.assertEqual(dt('2022-01-01T10:00/UTC'), e.start)
        self.assertEqual(dt('2022-01-01T11:00/UTC'), e.end)


class TestRemerge(unittest.TestCase):
    '''Test cases for making sure that unparse-reparse works without spurious conflicts'''

    def assertRemergeIsTrivial(self, ev, **kw):
        ugen = TestUnparse.mk_unparser(**kw)
        src_cal = OrgCalendar('id-00000', 'X', [ev])
        oup, getstr = ugen()
        oup.unparse_calendar(src_cal)
        s = getstr()
        cals = TestParse.parser().loads(s)
        self.assertEqual(1, len(cals))
        cal = list(cals.values())[0]
        self.assertEqual(1, len(cal.events))
        ev2 = list(cal.events.values())[0]

        # print(f'\n[new] {ev.full_str}')
        # print(f'[old] {ev2.full_str}')

        diffs = ev.diff(ev2)
        for suppress_prop in event.Event.UNDIFFABLE_PROPERTIES:
            if suppress_prop in diffs:
                del diffs[suppress_prop]

        differences_nr = 0

        for k, v in diffs.items():
            resolved, result = v
            if not resolved:
                if not differences_nr:
                    print('')
                differences_nr += 1
                print(f'difference #{differences_nr}\t[old {k}] "{repr(result[0])}" : {type(result[0])}')
                print(f'            \t[new {k}] "{repr(result[1])}" : {type(result[1])}')

        self.assertEqual(0, differences_nr)

    # ----------------------------------------
    def test_attendees(self):
        '''Simple event unparsing'''
        ev = mk_event('I0', 'Test',
                      start=dt('2022-01-01T10:00/UTC'),
                      end=dt(  '2022-01-01T11:00/UTC'),
                      attendees = ['foo@bar.com', 'user@email.com'],
                      status = event.TODO,
                      recurrences=[])
        self.assertRemergeIsTrivial(ev,
                                    today=dt('2022-01-01'))

    # ----------------------------------------
    def test_repeat(self):
        '''Simple event unparsing'''
        ev = mk_event('I0', 'Test',
                      start=dt('2022-01-01T10:00/CET'),
                      end=dt(  '2022-01-01T11:00/CET'),
                      attendees = ['foo@bar.com', 'user@email.com'],
                      status = event.TODO,
                      recurrences=[daily()])
        # summer time
        self.assertRemergeIsTrivial(ev,
                                    today=dt('2022-05-21/CET'),
                                    past_events = False)


class TestIntegrate(unittest.TestCase):

    def test_two_calendars(self):
        cals_0 = TestParse.parser().loads('''
* CAL0
  :PROPERTIES:
  :CAL-UID: C0
  :END:
** TODO C0-Alpha
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :CALEVENT-UID: I0
  :LOCATION: loc-A
  :END:
** DONE C0-Beta
  SCHEDULED: <2022-01-01 Sat 12:00-13:00>
  :PROPERTIES:
  :CALEVENT-UID: I1
  :END:
* CAL1
  :PROPERTIES:
  :CAL-UID: C1
  :END:
** TODO C1-Gamma
  SCHEDULED: <2022-01-01 Sat 09:00-09:30>
  :PROPERTIES:
  :CALEVENT-UID: I2
  :END:
A Comment
** TODO C1-Delta
  SCHEDULED: <2022-01-01 Sat 09:30-09:45>
  :PROPERTIES:
  :CALEVENT-UID: I3
  :END:
''')
        cals_1 = TestParse.parser().loads('''
* CAL0
  :PROPERTIES:
  :CAL-UID: C0
  :END:
** TODO C0-Alpha
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :LOCATION: loc-A
  :CALEVENT-UID: I0
  :END:
A comment from over here
* CAL1
  :PROPERTIES:
  :CAL-UID: C1
  :END:
** TODO C1-Epsilon
  SCHEDULED: <2022-01-01 Sat 19:30-19:45>
  :PROPERTIES:
  :CALEVENT-UID: I4
  :END:
** CANCELLED C1-Gamma
  SCHEDULED: <2022-01-01 Sat 09:00-09:30>
  :PROPERTIES:
  :CALEVENT-UID: I2
  :END:
** TODO C1-Delta
  SCHEDULED: <2022-01-01 Sat 09:30-09:45>
  :PROPERTIES:
  :LOCATION: loc-D
  :CALEVENT-UID: I3
  :END:
''')
        cals = cals_0.merge(cals_1)
        ugen = TestUnparse.mk_unparser(today=dt('2022-01-01'))
        oup, getstr = ugen()
        oup.unparse_all(cals)

        self.maxDiff=4096

        self.assertEqual(OUTPUT_HEADER +
'''
* CAL0
  :PROPERTIES:
  :CAL-UID: C0
  :END:
** TODO C0-Alpha
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :LOCATION: loc-A
  :CALEVENT-UID: I0
  :END:
A comment from over here
** DONE C0-Beta
  SCHEDULED: <2022-01-01 Sat 12:00-13:00>
  :PROPERTIES:
  :CALEVENT-UID: I1
  :END:

* CAL1
  :PROPERTIES:
  :CAL-UID: C1
  :END:
** CANCELLED C1-Gamma
  SCHEDULED: <2022-01-01 Sat 09:00-09:30>
  :PROPERTIES:
  :CALEVENT-UID: I2
  :END:
A Comment
** TODO C1-Delta
  SCHEDULED: <2022-01-01 Sat 09:30-09:45>
  :PROPERTIES:
  :LOCATION: loc-D
  :CALEVENT-UID: I3
  :END:

** TODO C1-Epsilon
  SCHEDULED: <2022-01-01 Sat 19:30-19:45>
  :PROPERTIES:
  :CALEVENT-UID: I4
  :END:

''', getstr())

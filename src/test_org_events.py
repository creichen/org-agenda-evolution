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

    def mk_unparser(self, **kwd):
        if 'local_timezone' not in kwd:
            kwd['local_timezone'] = None
        if 'emit_debug' not in kwd:
            kwd['emit_debug'] = False

        def fgen():
            f = io.StringIO()
            u = OrgEventUnparser(f, **kwd)
            return (u, f.getvalue)
        return fgen

    def test_simple(self):
        ev = mk_event('I0', 'Test',
                      start=dt('2022-01-01T10:00/UTC'),
                      end=dt(  '2022-01-01T11:00/UTC'),
                      recurrences=[])
        ugen = self.mk_unparser(today=dt('2022-01-01'))
        oup, getstr = ugen()
        oup.unparse_event(ev)
        self.assertEqual(
            '''** TODO Test
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :CALEVENT-UID: I0
  :END:

''', getstr())


class TestParse(unittest.TestCase):

    def parser(self, **kwd):
        if 'local_timezone' not in kwd:
            kwd['local_timezone'] = None
        if 'emit_debug' not in kwd:
            kwd['emit_debug'] = False

        return OrgEventParser(**kwd)

    def test_simple(self):
            cals = self.parser().loads('''* CAL0
** TODO Test
  SCHEDULED: <2022-01-01 Sat 10:00-11:00>
  :PROPERTIES:
  :CALEVENT-UID: I0
  :END:
''')
            self.assertEqual(1, len(cals))
            c = cals[0]
            self.assertEqual('CAL0', c.name)
            self.assertEqual(1, len(c.events))
            e = c.events['I0'] # implicitly assert existence below:
            self.assertEqual('I0', e.event_id)
            self.assertEqual('Test', e.name)
            self.assertEqual(dt('2022-01-01T10:00/UTC'), e.start)
            self.assertEqual(dt('2022-01-01T11:00/UTC'), e.end)

from __future__ import annotations

import sys
import io
import gi
import sys
import orgparse
import argparse
from caltime import CalTime, CalConverter
import event
from event import EventSet
from tzresolve import TZResolver
from zoneinfo import ZoneInfo

EMPTY_EVENT_NAME = '(nameless event)'
'''Use org-agenda repetition ("+1w" etc.) to avoid duplicating events, if possible'''
ORG_AGENDA_NATIVE_RECURRENCE_ALLOWED = True
'''When emitting recurring events, generate events from today to this many days in the future:'''
RECURRENCE_EMIT_FUTURE_DAYS = 7
'''Timezone to convert input into'''
LOCAL_TIMEZONE=None # UTC
'''Include one-time events earlier than today'''
PAST_EVENTS=True
'''Header for output file'''
OUTPUT_HEADER='#+STARTUP: content\n#+FILETAGS: :@calendar:\n'

EMIT_DEBUG=True

def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class OrgProc:
    SCHEDULED = 'SCHEDULED'
    PROPERTIES = 'PROPERTIES'
    ATTENDEES = 'ATTENDEES'
    LOCATION = 'LOCATION'
    EVENT_UID = 'CALEVENT-UID'

    def __init__(self,
                 output_header=OUTPUT_HEADER,
                 empty_event_name=EMPTY_EVENT_NAME,
                 org_agenda_native_recurrence_allowed = ORG_AGENDA_NATIVE_RECURRENCE_ALLOWED,
                 recurrence_emit_future_days = RECURRENCE_EMIT_FUTURE_DAYS,
                 local_timezone = LOCAL_TIMEZONE,
                 past_events = PAST_EVENTS,
                 emit_debug = EMIT_DEBUG,
                 today = None,
                 ):
        self.output_header = output_header
        self.empty_event_name = empty_event_name
        self.org_agenda_native_recurrence_allowed = org_agenda_native_recurrence_allowed
        self.recurrence_emit_future_days = recurrence_emit_future_days
        self.local_timezone = ZoneInfo('UTC' if local_timezone is None else local_timezone)
        self.past_events = past_events
        self.emit_debug = emit_debug
        self.today = CalTime.today(local_timezone) if today is None else today


class OrgEventUnparser(OrgProc):
    '''Translate Events into org files'''

    def __init__(self, file, **kwargs):
        super().__init__(**kwargs)
        self.f = file

    def print_header(self):
        if self.output_header:
            self.pr(self.output_header)

    def pr(self, *args):
        print(*args, file=self.f)

    def unparse_timespec_recurrence(self, recurrence, start, end):
        start = start.astimezone(self.local_timezone)
        if end is None:
            return f'{start.timespec(recurrence)}'
        end = end.astimezone(self.local_timezone)
        if (start.year, start.month, start.day) == (end.year, end.month, end.day):
            return f'{start.timespec(recurrence, untiltime=end)}'
        else:
            return f'{start.timespec(recurrence)}--{end.timespec(recurrence)}'

    def unparse_event(self, event, recur_spec=None, start=None, end=None):
        if start is None:
            start = event.start
        if end is None:
            end = event.end

        self.pr(f'** {event.status} {event.name}')
        timespec = self.unparse_timespec_recurrence(recur_spec, start, end)
        self.pr(f'  {OrgProc.SCHEDULED}: {timespec}')

        self.pr(f'  :{OrgProc.PROPERTIES}:')
        if event.location:
            self.pr(f'  :{OrgProc.LOCATION}: ' + event.location)
        if event.attendees:
            self.pr(f'  :{OrgProc.ATTENDEES}: ' + ' '.join(event.attendees))
        self.pr(f'  :{OrgProc.EVENT_UID}: {event.event_id}')
        if start.tzinfo != self.local_timezone:
            self.pr(f'  :CONVERTED-FROM-TZID: {start.tzinfo}')

        if self.emit_debug:
            self.pr(f'  :ORIGINAL-START: {repr(event.start)}')
            self.pr(f'  :ORIGINAL-END: {repr(event.end)}')
            sep = ', '
            self.pr(f'  :ORIGINAL-RECURRENCES: {sep.join(str(e) for e in event.recurrences)}')
            for k, v in event.debuginfo:
                self.pr(f'  :{k}: {v}')

        self.pr('  :END:')


        def prdescription(description):
            for s in description.split('\n'):
                if s.startswith('*'):
                    self.pr(' ', s)
                else:
                    self.pr(s)

        self.pr(event.description)

    def unparse_calendar(self, calendar : EvolutionCalendar):
        today = self.today

        self.pr(f'* {calendar.name}')
        for event in calendar.events.values():
            if not event.recurrences:
                # Only one event, non-recurring
                if PAST_EVENTS or event.end.astimezone(self.local_timezone) > today:
                    self.unparse_event(event)
            for recurrence in event.recurrences:
                if recurrence.spec and self.org_native_recurrence_allowed:
                    # org can express the recurrence natively?
                    self.unparse_event(event, recur_spec=recurrence.spec)
                else:
                    # Repeat by hand
                    start_recur = recurrence.range_from(event.start).starting(today)
                    end_recur = None
                    end = None

                    try:
                        for start in start_recur:
                            # Since we don't have a means to initialise by recurrence count right now,
                            # instead use the first recurrence of "end" at or after "start", which should
                            # always be the right one
                            if end_recur is None and event.end:
                                end_recur = recurrence.range_from(event.end).starting(start)

                            if (start.astimezone(self.local_timezone) - today).days > self.recurrence_emit_future_days:
                                # Far enough into the future
                                break

                            if end_recur:
                                end = end_recur.__next__()
                            self.unparse_event(event, start=start, end=end)

                    except StopIteration:
                        pass


class OrgCalendar:
    '''One calendar representation loaded from an org file'''

    def __init__(self, name : str, events : list[Event]):
        self._events = EventSet()
        for e in events:
            self._events.add(e)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def events(self) -> EventSet:
        return self._events


class OrgEventParser(OrgProc):
    '''Translate org files into calendars and events'''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load(self, file):
        return self.translate(orgparse.load(file))

    def loads(self, str):
        return self.translate(orgparse.loads(str))

    def translate(self, root):
        return [self.translate_calendar(c) for c in root.children]

    def translate_calendar(self, cal):
        return OrgCalendar(cal.heading,
                           [self.translate_event(e) for e in cal.children])

    def translate_datetime(self, dt):
        if dt is None:
            return None
        return CalTime.from_datetime(dt, tzinfo=self.local_timezone)

    def translate_event(self, orgev):
        ev = event.CalEvent(orgev.get_property(OrgProc.EVENT_UID))
        ev.name = orgev.heading
        ev.status = event.EventState.get(str(orgev.todo))
        ev.start = self.translate_datetime(orgev.scheduled.start)
        ev.end = self.translate_datetime(orgev.scheduled.end)
        ev.description = orgev.body
        ev.attendees = orgev.get_property(OrgProc.ATTENDEES)
        ev.location = orgev.get_property(OrgProc.LOCATION)
        return ev

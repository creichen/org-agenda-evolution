from __future__ import annotations

import sys
import io
import gi
import sys
import orgparse
import argparse
from caltime import CalTime, CalConverter
import event
from event import EventSet, MergingDict
from tzresolve import TZResolver
from zoneinfo import ZoneInfo

EMPTY_EVENT_NAME = event.EMPTY_EVENT_NAME
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

EMIT_DEBUG=event.EMIT_DEBUG


TODOS=[event.TODO_STR, 'WAITING']
DONES=[event.DONE_STR, event.CANCELLED_STR]


def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class OrgProc:
    SCHEDULED = 'SCHEDULED'
    PROPERTIES = 'PROPERTIES'
    ATTENDEES = 'ATTENDEES'
    LOCATION = 'LOCATION'
    EVENT_UID = 'CALEVENT-UID'

    CONFLICT_HEADING = '!CONFLICT!' # extra string added to heading of conflicts

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

    def unparse_all(self, caldict : MergingDict):
        self.print_header()
        for cal in caldict.values():
            self.unparse_calendar(cal)

    def unparse_timespec_recurrence(self, recurrence, start, end):
        start = start.astimezone(self.local_timezone)
        if end is None:
            return f'{start.timespec(recurrence)}'
        end = end.astimezone(self.local_timezone)
        if (start.year, start.month, start.day) == (end.year, end.month, end.day):
            return f'{start.timespec(recurrence, untiltime=end)}'
        else:
            return f'{start.timespec(recurrence)}--{end.timespec(recurrence)}'

    def unparse_event(self, event, recur_spec=None, start=None, end=None, depth='**', conflict_marker=None):
        if start is None:
            start = event.start
        if end is None:
            end = event.end

        conflict = '' if conflict_marker is None else f'{conflict_marker} '

        self.pr(f'{depth} {event.status} {conflict}{event.name}')
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

        if event.get_conflict_event():
            self.unparse_event(event.get_conflict_event(), depth=depth+'*', conflict_marker=OrgProc.CONFLICT_HEADING)


    def unparse_calendar(self, calendar : EvolutionCalendar):
        today = self.today

        self.pr(f'* {calendar.name}')
        self.pr(f'  :{OrgProc.PROPERTIES}:')
        self.pr(f'  :{OrgCalendar.CALID}: {calendar.uid}')
        self.pr('  :END:')
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

    CALID = 'CAL-UID'

    def __init__(self, name : str, caluid : str, events):
        self._uid = caluid
        if type(events) is EventSet:
            self._events = events
        else:
            self._events = EventSet()
            for e in events:
                self._events.add(e)
        self._name = name

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def name(self) -> str:
        return self._name

    @property
    def events(self) -> EventSet:
        return self._events

    def merge(self, other):
        return OrgCalendar(self.name, self.uid, self.events.merge(other.events))


class OrgEventParser(OrgProc):
    '''Translate org files into calendars and events'''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def org_env(self, filename):
        return orgparse.OrgEnv(todos=TODOS, dones=DONES, filename=filename)

    def load(self, file):
        return self.translate(orgparse.load(file, env=self.org_env(filename)))

    def loads(self, str):
        return self.translate(orgparse.loads(str, env=self.org_env('<string>')))

    def translate(self, root):
        result = MergingDict()
        for calnode in root.children:
            cal = self.translate_calendar(calnode)
            result[cal.uid] = cal
        return result

    def translate_calendar(self, cal):
        return OrgCalendar(cal.heading,
                           cal.get_property(OrgCalendar.CALID),
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
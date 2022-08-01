# deps:
#  - gir1.2-ecalendar-1.2
#  - gir1.2-ecal-2.0
#  - orgparse
#  - running and preconfigured evolution-server

# With thanks to GabLeRoux for outlining the main approach:
# https://askubuntu.com/questions/193954/coding-own-application-for-gnome-shell-calendar-evolution-calendar

from __future__ import annotations

import gi
import sys
#import orgparse
from caltime import CalTime, Recurrence
from tzresolve import TZResolver

gi.require_version('EDataServer', '1.2')
from gi.repository import EDataServer

gi.require_version('ECal', '2.0')
from gi.repository import ECal, Gio

# Config
'''Seconds to wait for connection'''
WAIT_TO_CONNECT_SECS = 5
'''sexp filter for events; "#t" finds all events'''
EVENT_FILTER_SEXP = '#t'
'''Name that we fill in for events whose name/summary is empty'''
EMPTY_EVENT_NAME = '(nameless event)'
'''Use org-agenda repetition ("+1w" etc.) to avoid duplicating events, if possible'''
ORG_AGENDA_NATIVE_RECURRENCE_ALLOWED = True
'''When emitting recurring events, generate events from today to this many days in the future:'''
RECURRENCE_EMIT_FUTURE_DAYS = 7
'''Timezone to convert input into'''
LOCAL_TIMEZONE=None # UTC
'''Include one-time events earlier than today'''
PAST_EVENTS=False
'''Header for output file'''
OUTPUT_HEADER='#+STARTUP: content\n#+FILETAGS: :@calendar:\n'

# TODO type markers
TODO='TODO'
DONE='DONE'
CANCELLED='CANCELLED'

'''What status should the event status be translated to? (Default is the one for None)'''
EVENT_STATUS_MAPPING = {
    None                     : TODO,
    'I_CAL_STATUS_CONFIRMED' : TODO,
    'I_CAL_STATUS_CANCELLED' : CANCELLED,
    'I_CAL_STATUS_NONE'      : TODO,
}

def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Event:
    '''A calendar event (which may describe a recurring event)'''
    def __init__(self, uid : str, name : str, start):
        self.uid = uid
        self.name = name
        self.description_local = ''
        self.description_remote = ''
        self.status = EVENT_STATUS_MAPPING[None]
        self.attendees = []
        self.start = start
        self.end = None
        self.recurrences = []
        self.last_modified_remote = None
        self.organizer = None
        self.evo_event = None

    @staticmethod
    def from_evolution(evo_event, tzresolver=None):
        '''Translates evolution event in to an Event'''

        name = evo_event.get_summary()
        name = EMPTY_EVENT_NAME if name is None else name.get_value()
        start = CalTime.from_evolution_cdt(evo_event.get_dtstart(), tzresolver=tzresolver)
        event = Event(evo_event.get_id().get_uid(), name, start)

        event.evo_event = evo_event

        # Optional features:
        if evo_event.get_dtend():
            event.end = CalTime.from_evolution_cdt(evo_event.get_dtend(), tzresolver=tzresolver)

        if evo_event.get_last_modified():
            event.end = CalTime.from_evolution(evo_event.get_last_modified(), tzresolver=tzresolver)

        if evo_event.get_status() is not None:
            event.status = EVENT_STATUS_MAPPING[evo_event.get_status().value_name]

        if evo_event.has_organizer():
            event.organizer = evo_event.get_organizer().get_value()

        # Also potentially interesting: attendee.get_rsvp() : bool
        event.attendees = [attendee.get_value() for attendee in evo_event.get_attendees()]

        event.description_remote = '\n'.join(d.get_value() for d in evo_event.get_descriptions())

        for rec in evo_event.get_rrules():
            zzz = evo_event.get_dtstart().get_value()
            tz = zzz.get_timezone()
            tzoff = '-' if tz is None else tz.get_utc_offset()
            #print(f'## {start} {tz} {tzoff}')
            # print(name)
            # print(Recurrence.evolution_rec_as_mock(rec))
            rrec = Recurrence.from_evolution(rec)
            if type(rrec) is Recurrence:
                event.recurrences.append(rrec)
            elif type(rrec) is str:
                # Can't express directly, noting as string
                #print(f'#WARNING for repetition of event {event}: {rrec}')
                if event.description_remote == '':
                    event.description_remote = rrec
                else:
                    event.description_remote = rrec + '\n' + event.description_remote

        return event

    def merge(self, other):
        '''Merge an event with an identical ID'''
        pass

    @property
    def status_str(self):
        if self.status is None:
            return TODO
        return self.status

    def __str__(self):
        return f'{self.status_str} {self.name} at: {self.start}'


class EventSet(dict):
    '''A set of calendar events, indexed by their UIDs'''
    def __init__(self):
        super(dict, EventSet).__init__(self)

    def add(self, event):
        if event.uid in self:
            self[event.uid].merge(event)
        else:
            self[event.uid] = event


class EvolutionCalendar:
    '''One Evolution calendar, including its events'''

    def __init__(self, evocalendar, gio_cancellable):
        self._evocalendar = evocalendar
        self._cancellable = gio_cancellable
        self._events = None

    @property
    def evocal(self):
        return self._evocalendar

    @property
    def name(self) -> str:
        '''The calendar's name'''
        return self._evocalendar.get_display_name()


    @property
    def events(self) -> EventSet:
        '''The EventSet for this calendar'''
        if self._events is None:
            # https://lazka.github.io/pgi-docs/ECal-2.0/classes/Client.html#ECal.Client.connect_sync
            client = ECal.Client()
            # timezone = client.get_default_timezone()
            # print(f'default timezone:{timezone} ->\n\tid={timezone.get_tzid()}\n\ttznames={timezone.get_tznames()}\n\tutc_offset={timezone.get_utc_offset(None)}')
            client = client.connect_sync(source = self._evocalendar,
                                         source_type = ECal.ClientSourceType.EVENTS,
                                         wait_for_connected_seconds = WAIT_TO_CONNECT_SECS,
                                         cancellable = self._cancellable)
            self._events = EventSet()
            success, values = client.get_object_list_as_comps_sync(sexp = EVENT_FILTER_SEXP,
                                                                   cancellable = self._cancellable)
            if not success:
                # Assume that calendar is empty
                return self._events

            tzresolver = TZResolver(client)
            for v in values:
                if v is not None:
                    self._events.add(Event.from_evolution(v, tzresolver=tzresolver))

        return self._events


class EvolutionEvents:
    '''All Evolution calendars and events'''
    _singleton = None

    def __new__(classobj):
        if classobj._singleton is None:
            classobj._singleton = super(EvolutionEvents, classobj).__new__(classobj)
        return classobj._singleton

    def __init__(self):
        self._calendars = None

        # Handle asynchronous GIO cancellations
        # https://lazka.github.io/pgi-docs/Gio-2.0/classes/Cancellable.html#Gio.Cancellable
        self._cancellable = Gio.Cancellable.new()

    @property
    def calendars(self):
        if self._calendars == None:
            reg_sync = EDataServer.SourceRegistry.new_sync(self._cancellable)
            calendars = EDataServer.SourceRegistry.list_sources(reg_sync, EDataServer.SOURCE_EXTENSION_CALENDAR)
            # reuse cancellation stack
            self._calendars = [EvolutionCalendar(c, self._cancellable) for c in calendars]
        return self._calendars


class OrgUnparser:
    def __init__(self, file):
        self.f = file

    def print_header(self):
        if OUTPUT_HEADER:
            self.pr(OUTPUT_HEADER)

    def pr(self, *args):
        print(*args, file=self.f)

    def unparse_timespec_recurrence(self, recurrence, start, end):
        start = start.astimezone(LOCAL_TIMEZONE)
        if end is None:
            return f'{start.timespec(recurrence)}'
        end = end.astimezone(LOCAL_TIMEZONE)
        return f'{start.timespec(recurrence)}--{end.timespec(recurrence)}'

    def unparse_event(self, event, recur_spec=None, start=None, end=None):
        if start is None:
            start = event.start
        if end is None:
            end = event.end

        self.pr(f'** {event.status_str} {event.name}')
        timespec = self.unparse_timespec_recurrence(recur_spec, start, end)
        self.pr(f'  SCHEDULED: {timespec}')

        self.pr('  :PROPERTIES:')
        if event.attendees:
            self.pr(f'  :ATTENDEES: ' + ' '.join(event.attendees))
        self.pr(f'  :CALENDAR-UID: {event.uid}')
        if start.tzinfo != LOCAL_TIMEZONE:
            self.pr(f'  :CONVERTED-FROM-TZID: {start.tzinfo}')
        self.pr(f'  :ORIGINAL-START: {repr(event.start)}')
        self.pr(f'  :ORIGINAL-END: {repr(event.end)}')
        self.pr(f'  :ORIGINAL-RECURRENCES: {str(event.recurrences)}')
        self.pr('  :END:')


        def prdescription(description):
            for s in description.split('\n'):
                if s.startswith('*'):
                    self.pr(' ', s)
                else:
                    self.pr(s)

        if not event.description_remote:
            if event.description_local:
                prdescription(event.description_local)
        elif not event.description_local or event.description_local == event.description_remote:
            prdescription(event.description_remote)
        else:
            # have both remote and local, and they differ!
            self.pr('*** Local description')
            prdescription(event.description_local)
            self.pr('*** Remote calendar description')
            prdescription(event.description_remote)

    def unparse_calendar(self, calendar : EvolutionCalendar):
        today = CalTime.today(LOCAL_TIMEZONE)

        self.pr(f'* {calendar.name}')
        for event in calendar.events.values():
            if not event.recurrences:
                # Only one event, non-recurring
                if PAST_EVENTS or event.end.astimezone(LOCAL_TIMEZONE) > today:
                    self.unparse_event(event)
            for recurrence in event.recurrences:
                if recurrence.spec and ORG_NATIVE_RECURRENCE_ALLOWED:
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

                            if (start.astimezone(LOCAL_TIMEZONE) - today).days > RECURRENCE_EMIT_FUTURE_DAYS:
                                # Far enough into the future
                                break

                            if end_recur:
                                end = end_recur.__next__()
                            self.unparse_event(event, start=start, end=end)

                    except StopIteration:
                        pass


if __name__ == '__main__':
    events = EvolutionEvents()

    import sys
    unparser = OrgUnparser(sys.stdout)
    unparser.print_header()
    for cal in events.calendars:
        unparser.unparse_calendar(cal)


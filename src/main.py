# deps:
#  - gir1.2-ecalendar-1.2
#  - gir1.2-ecal-2.0
#  - orgparse
#  - running and preconfigured evolution-server

# With thanks to GabLeRoux for outlining the main approach:
# https://askubuntu.com/questions/193954/coding-own-application-for-gnome-shell-calendar-evolution-calendar

import gi
#import orgparse
from caltime import CalTime, Recurrence

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

    @staticmethod
    def from_evolution(evo_event):
        '''Translates evolution event in to an Event'''

        name = evo_event.get_summary()
        name = EMPTY_EVENT_NAME if name is None else name.get_value()
        start = CalTime.from_evolution(evo_event.get_dtstart().get_value())
        event = Event(evo_event.get_id().get_uid(), name, start)

        # Optional features:
        if evo_event.get_dtend():
            event.end = CalTime.from_evolution(evo_event.get_dtend().get_value())

        if evo_event.get_last_modified():
            event.end = CalTime.from_evolution(evo_event.get_last_modified())

        if evo_event.get_status() is not None:
            event.status = EVENT_STATUS_MAPPING[evo_event.get_status().value_name]

        # Also potentially interesting: attendee.get_rsvp() : bool
        event.attendees = [attendee.get_value() for attendee in evo_event.get_attendees()]

        event.description_remote = '\n'.join(d.get_value() for d in evo_event.get_descriptions())

        for rec in evo_event.get_rrules():
            print(name)
            print(Recurrence.evolution_rec_as_mock(rec))
            rrec = Recurrence.from_evolution(rec)
            if type(rrec) is Recurrence:
                event.recurrences.append(rrec)
            elif type(rrec) is list:
                for r in rrec:
                    event.recurrences.append(r)
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
    def name(self) -> str:
        '''The calendar's name'''
        return self._evocalendar.get_display_name()


    @property
    def events(self) -> EventSet:
        '''The EventSet for this calendar'''
        if self._events is None:
            # https://lazka.github.io/pgi-docs/ECal-2.0/classes/Client.html#ECal.Client.connect_sync
            client = ECal.Client().connect_sync(source = self._evocalendar,
                                                source_type = ECal.ClientSourceType.EVENTS,
                                                wait_for_connected_seconds = WAIT_TO_CONNECT_SECS,
                                                cancellable = self._cancellable)
            self._events = EventSet()
            success, values = client.get_object_list_as_comps_sync(sexp = EVENT_FILTER_SEXP,
                                                                   cancellable = self._cancellable)
            if not success:
                # Assume that calendar is empty
                return self._events

            for v in values:
                if v is not None:
                    self._events.add(Event.from_evolution(v))

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

    def pr(self, *args):
        print(*args, file=self.f)

    def unparse_timespec_recurrence(self, recurrence, start, end):
        (start, delta) = recurrence.adjust_time(start)
        if end is None:
            return start.timespec(recurrence)
        end += delta
        return f'{start.timespec(recurrence)}--{end.timespec(recurrence)}'

    def unparse_timespec(self, start, end):
        if end is None:
            return start.timespec()
        return f'{start.timespec()}--{end.timespec()}'

    def unparse_event(self, event):
        self.pr(f'** {event.status_str} {event.name}')
        self.pr('  :PROPERTIES:')
        if event.attendees:
            self.pr(f'  :ATTENDEES: ' + ' '.join(event.attendees))
        self.pr(f'  :CALENDAR-UID: {event.uid}')
        self.pr('  :END:')
        if event.recurrences:
            # Print out one SCHEDULED entry per recurrence
            for recurrence in event.recurrences:
                timespec = self.unparse_timespec_recurrence(recurrence, event.start, event.end)
                self.pr(f'  SCHEDULED: {timespec}')
        else:
            # No recurrence
            timespec = self.unparse_timespec(event.start, event.end)
            self.pr(f'  SCHEDULED: {timespec}')

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

    def unparse_calendar(self, calendar):
        self.pr(f'* {calendar.name}')
        for event in calendar.events.values():
            self.unparse_event(event)
            # eventnode = orgparse.node.OrgNode(self.rootenv)
            # calnode.children.


if __name__ == '__main__':
    events = EvolutionEvents()

    import sys
    unparser = OrgUnparser(sys.stdout)
    for cal in events.calendars:
        unparser.unparse_calendar(cal)


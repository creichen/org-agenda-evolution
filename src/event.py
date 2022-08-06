from __future__ import annotations

from caltime import CalTime, Recurrence, CalConverter

# TODO type markers
TODO_STR='TODO'
DONE_STR='DONE'
CANCELLED_STR='CANCELLED'

def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class MergeableEventProperty:
    '''Type that tags event properties that are 'mergeable' (part of a lattice)'''

    def merge(self, other : MergeableEventProperty) -> (MergeableEventProperty) :
        '''Attempts to merge (join) two event properties'''
        raise Exception('Implement Me')


class EventState(MergeableEventProperty):
    '''TODO state'''
    def __init__(self, name : str):
        self.name = name

    def merge(self, other : EventState) -> EventState:
        if self == other:
            return self

        # DONE > CANCELLED > (misc) > TODO

        if self == DONE or other == DONE:
            return DONE
        if self == CANCELLED or other == CANCELLED:
            return CANCELLED

        # Preserve local states that are not among the main three
        if self not in [TODO, CANCELLED, DONE]:
            return self
        if other not in [TODO, CANCELLED, DONE]:
            return other
        return TODO

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class EventStringList(list, MergeableEventProperty):
    '''List of strings (used for attendee names)'''

    def EventStringList(self, args):
        super().__init__(self, args)

    def merge(self, other : EventStringList) -> EventStringList:
        if self == other:
            return self
        rlist = list(self)
        for item in other:
            if item not in self:
                rlist.append(item)
        return EventStringList(rlist)


TODO = EventState(TODO_STR)
CANCELLED = EventState(CANCELLED_STR)
DONE = EventState(DONE_STR)

'''What status should the event status be translated to? (Default is the one for None)'''
EVENT_STATUS_MAPPING = {
    None                       : TODO,
    'I_CAL_STATUS_CANCELLED'   : CANCELLED,
    'I_CAL_STATUS_COMPLETED'   : DONE,
    'I_CAL_STATUS_CONFIRMED'   : TODO,
    'I_CAL_STATUS_DELETED'     : CANCELLED,
    'I_CAL_STATUS_DRAFT'       : TODO,
    'I_CAL_STATUS_FAILED'      : CANCELLED,
    'I_CAL_STATUS_FINAL'       : TODO,
    'I_CAL_STATUS_INPROCESS'   : TODO,
    'I_CAL_STATUS_NEEDSACTION' : TODO,
    'I_CAL_STATUS_NONE'        : TODO,
    'I_CAL_STATUS_PENDING'     : TODO,
    'I_CAL_STATUS_SUBMITTED'   : TODO,
    'I_CAL_STATUS_TENTATIVE'   : TODO,
    'I_CAL_STATUS_X'           : TODO,
}

class Event:
    '''An abstract calendar event (which may describe a recurring event or an individual occurrence)'''

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
        self.exceptions = []
        self.last_modified_remote = None
        self.organizer = None
        self.evo_event = None
        self.debuginfo = []

    @staticmethod
    def from_evolution(evo_event, cconverter : CalConverter):
        '''Translates evolution event in to an Event'''

        name = evo_event.get_summary()
        name = EMPTY_EVENT_NAME if name is None else name.get_value()
        start = cconverter.time_from_evolution(evo_event.get_dtstart())
        event = CalEvent(evo_event.get_id().get_uid(), name, start)

        event.evo_event = evo_event

        # Optional features:
        if evo_event.get_dtend():
            event.end = cconverter.time_from_evolution(evo_event.get_dtend())

        if evo_event.get_last_modified():
            event.last_modified_remote = cconverter.time_from_evolution(evo_event.get_last_modified())

        if evo_event.get_status() is not None:
            key = evo_event.get_status().value_name
            event.status = EVENT_STATUS_MAPPING[key]
            event.debuginfo.append(('ORIGINAL-GET-STATUS', key))


        if EMIT_DEBUG:
            event.debuginfo.append(('ORIGINAL-GET-CATEGORIES', str(evo_event.get_categories_list())))
            event.debuginfo.append(('AS-STR', str(evo_event.get_as_string())))
            event.debuginfo.append(('ICAL', str(evo_event.get_icalcomponent())))

        if evo_event.has_organizer():
            event.organizer = evo_event.get_organizer().get_value()

        # Also potentially interesting: attendee.get_rsvp() : bool
        event.attendees = [attendee.get_value() for attendee in evo_event.get_attendees()]

        event.description_remote = '\n'.join(d.get_value() for d in evo_event.get_descriptions())

        for rec in evo_event.get_rrules():
            # print(name)
            # print(Recurrence.evolution_rec_as_mock(rec))
            rrec = cconverter.recurrence_from_evolution(rec)
            if type(rrec) is Recurrence:
                event.recurrences.append(rrec)
            elif type(rrec) is str:
                # Can't express directly, noting as string
                #print(f'#WARNING for repetition of event {event}: {rrec}')
                if event.description_remote == '':
                    event.description_remote = rrec
                else:
                    event.description_remote = rrec + '\n' + event.description_remote

        for exrule in evo_event.get_exrules():
            perr('  -- exrule : %s : %s (%s)' % (exrule, type(exrule), dir(exrule)))
            rexrule = cconverter.recurrence_from_evolution(exrule)
            if type(rexrule) is Recurrence:
                event.exceptions.append(rexrule)
            elif type(rexrule) is str:
                # Can't express directly, noting as string
                if event.description_remote == '':
                    event.description_remote = rrec
                else:
                    event.description_remote = 'Except: ' + rrec + '\n' + event.description_remote

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


class CalEvent(Event):
    '''A calendar event that may contain one or more event occurrences'''
    def __init__(self, uid : str, name : str, start):
        super().__init__(uid, name, start)
        self.occurrences : list[Event] = [] # Only for "top-level events": Sequence IDs


class EventOccurrence(Event):
    def __init__(self, uid : str, name : str, start):
        super().__init__(uid, name, start)

    @property
    def recurrences(self):
        return []

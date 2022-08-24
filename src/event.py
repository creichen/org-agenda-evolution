from __future__ import annotations

import collections
from typing import Generator, Optional
import sys

from caltime import CalTime, Recurrence, CalConverter

EMPTY_EVENT_NAME='(nameless event)'

# TODO type markers
TODO_STR='TODO'
DONE_STR='DONE'
CANCELLED_STR='CANCELLED'

EMIT_DEBUG=False
EMIT_CONFLICT_DEBUG=True

def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class MergeableEventProperty:
    '''Type that tags event properties that are 'mergeable' (part of a lattice)'''

    def merge(self, other : MergeableEventProperty) -> (MergeableEventProperty) :
        '''Attempts to merge (join) two event properties'''
        raise Exception('Implement Me')


class EventState(MergeableEventProperty):
    '''TODO state'''

    STATES = {}

    def __init__(self, name : str):
        self.name = name
        assert name not in EventState.STATES
        EventState.STATES[name] = self

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

    @staticmethod
    def get(s):
        assert(s is not None)
        if s not in EventState.STATES:
            return EventState(s)
        return EventState.STATES[s]


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


def from_evolution(evo_event, cconverter : CalConverter) -> EventRepeater:
    '''Translates evolution event in to an EventRepeater'''

    name = evo_event.get_summary()
    name = EMPTY_EVENT_NAME if name is None else name.get_value()
    start = cconverter.time_from_evolution(evo_event.get_dtstart())
    event = EventRepeater(evo_event.get_id().get_uid(), name, start)

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
    else:
        event.status = TODO

    if EMIT_DEBUG:
        event.debuginfo.append(('ORIGINAL-GET-CATEGORIES', str(evo_event.get_categories_list())))
        event.debuginfo.append(('AS-STR', str(evo_event.get_as_string())))
        event.debuginfo.append(('ICAL', str(evo_event.get_icalcomponent())))

    if evo_event.get_location():
        event.location = evo_event.get_location()

    if evo_event.has_organizer():
        event.organizer = evo_event.get_organizer().get_value()

    # Also potentially interesting: attendee.get_rsvp() : bool
    event.attendees = sorted([attendee.get_value() for attendee in evo_event.get_attendees()])

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


class Event:
    '''An abstract calendar event (which may describe a recurring event or an individual occurrence)'''

    PROPERTIES = {
        'name'                 : (str, '(event)'),
        'description'          : (str, ''),
        'location'             : (str, ''),
        'status'               : (EventState, TODO),
        'attendees'            : (EventStringList, EventStringList()),
        'start'                : (CalTime, None),
        'end'                  : (CalTime, None),
        'recurrences'          : (list[Recurrence], []),
        'last_modified_remote' : (CalTime, None),
        'organizer'            : (Optional[str], None),
        'evo_event'            : (object, None),
        'debuginfo'            : (list[str], []),
    }

    UNDIFFABLE_PROPERTIES = ['debuginfo', 'recurrences']

    def __init__(self, event_id : str, sequence_nr : int):
        self._event_id = event_id
        self._sequence_nr = sequence_nr

    def get_conflict_event(self):
        return None

    def populate_properties(self):
        for p, (_, default) in Event.PROPERTIES.items():
            if not hasattr(self, p):
                setattr(self, p, default)

    @property
    def event_id(self):
        return self._event_id

    @property
    def sequence_nr(self):
        return self._sequence_nr

    def __hash__(self):
        return hash(self.uid, self.sequence_nr)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.event_id}, seq:{self.sequence_nr})'

    @property
    def full_str(self):
        s = f'ID={self.event_id}'
        for n in Event.PROPERTIES:
            if hasattr(self, n):
                v = getattr(self, n)
                s += f'\n\t{n} = "{v}"'
        return s

    def diff(self, other_event : Event) -> map[str, object]:
        '''
        Find differences between all event attributes.  Conflicts are reported as (False, (self_elt, other_elt)),
        merges as (True, merged).
        '''
        output = {}
        for prop, (proptype, _) in Event.PROPERTIES.items():
            pself = getattr(self, prop)
            pother = getattr(other_event, prop)

            if proptype is str and pself is not None and pother is not None:
                if pself.strip() == pother.strip():
                    continue
            elif proptype is CalTime and pself is not None and pother is not None:
                if pself.equivalent(pother):
                    continue
            else:
                if pself == pother:
                    continue

            v = (False, (pself, pother))

            if pself is None or pself == '':
                v = (True, pother)
            elif pother is None or pother == '':
                v = (True, pself)
            elif pself != None and pother != None:
                if isinstance(pself, MergeableEventProperty):
                    v = (True, pself.merge(pother))
            # Otherwise we have a proper conflict
            output[prop] = v

        return output

    def merge(self, other, explain_conflicts=True) -> ProxyEvent:
        '''
        Tries to merge in another event.  If complete merging is not possible, set up "get_conflict_event()"
        to return "other".  Returns ProxyEvent with conflict_event set to either 'None' or "other".
        '''
        conflict_event = None
        updates = { }
        diffs = self.diff(other)

        for suppress_prop in Event.UNDIFFABLE_PROPERTIES:
            if suppress_prop in diffs:
                del diffs[suppress_prop]

        for k, v in diffs.items():
            resolved, result = v
            if not resolved:
                conflict_event = other
            else:
                updates[k] = result

        if conflict_event and explain_conflicts:
            conflict_event = ProxyEvent(conflict_event, conflict_event.sequence_nr)
            b = conflict_event.description
            if b is None:
                b = ''
            b += ('\nLocal/remote calendar Conflict:\n')
            for k, v in diffs.items():
                resolved, result = v
                if not resolved:
                    suffix = ''
                    if EMIT_CONFLICT_DEBUG:
                        suffix = f': "{result[0]}" vs "{result[1]}"'
                    b += (f'- {k}{suffix}\n')
            conflict_event.description = b

        return ProxyEvent(self, self.sequence_nr, conflict_event=conflict_event, **updates)


class ProxyEvent(Event):
    '''Answer queries from base event, any changes are local'''
    def __init__(self, base_event, seq_nr, conflict_event=None, **overrides):
        super().__init__(base_event.event_id, seq_nr)
        self._base = base_event
        self._seq_nr = seq_nr
        self._overrides = overrides
        self._conflict_event = conflict_event

    def get_conflict_event(self):
        return self._conflict_event

    def __getattr__(self, attrname):
        if attrname[0] == '_':
            return super().__getattr__(attrname)

        if attrname in self._overrides:
            return self._overrides[attrname]
        return getattr(self._base, attrname)

    def __setattr__(self, attrname, v):
        if attrname[0] == '_':
            return super().__setattr__(attrname, v)

        if attrname in Event.PROPERTIES.keys():
            self._overrides[attrname] = v
        else:
            raise Exception('Invalid field: {attrname}')


class EventRepeater(Event):
    '''An event generator '''

    def __init__(self, event_id : str, name : str, start):
        super().__init__(event_id, None)
        self.name = name
        self.description = ''
        self.location = ''
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

    def in_interval(self, start : Optional[CalTime], end : CalTime) -> Generator[Event]:
        '''All events that intersect with this interval. 'start' may be None.'''

        if start is None:
            start = self.start

        seq_nr = 0
        ev_start = self.start
        ev_end = self.end
        repeater = None

        if self.recurrences == []:
            seq_nr += 1
            if ev_end >= start:
                yield ProxyEvent(self, seq_nr, start=ev_start, end=ev_end)

        else:
            for rec in self.recurrences:
                ev_end_it = rec.range_from(self.end).starting(ev_end)
                for ev_start in rec.range_from(self.start).starting(ev_start):
                    ev_end = ev_end_it.__next__()
                    if ev_end is None:
                        break

                    if ev_start > end:
                        return None # Passed the specified range

                    seq_nr += 1
                    if ev_end >= start:
                        yield ProxyEvent(self, seq_nr, start=ev_start, end=ev_end)

    def __str__(self):
        return f'{self.status} {self.name} at: {self.start}'


class CalEvent(Event):
    '''A calendar event that may contain one or more event occurrences'''
    def __init__(self, uid : str):
        super().__init__(uid, None)
        self.populate_properties()


class EventOccurrence(Event):
    def __init__(self, uid : str):
        super().__init__(uid, None)

    @property
    def recurrences(self):
        return []


# ----------------------------------------
# An order-preserving dict that supports merging
class MergingDict(collections.OrderedDict):
    '''Ordered dict with the ability to merge another MergingDict'''
    def __init__(self):
        super().__init__()

    def merge(self, other) -> MergingDict:
        result = self.__class__()
        for k, v in self.items():
            if k in other:
                v = v.merge(other[k])
            result[k] = v
        for k, v in other.items():
            if k not in self:
                result[k] = v
        return result

# ----------------------------------------
# EventSet
class EventSet(MergingDict):
    '''A set of calendar events, indexed by their event IDs'''
    def __init__(self):
        super().__init__()

    def add(self, event):
        if event.event_id in self:
            self[event.event_id].merge(event)
        else:
            self[event.event_id] = event





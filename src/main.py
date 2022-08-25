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
# deps:
#  - gir1.2-ecalendar-1.2
#  - gir1.2-ecal-2.0
#  - orgparse
#  - running and preconfigured evolution-server

# With thanks to GabLeRoux for outlining the main approach:
# https://askubuntu.com/questions/193954/coding-own-application-for-gnome-shell-calendar-evolution-calendar

from __future__ import annotations

import sys
import io
import gi
import sys
import argparse
from caltime import CalTime, CalConverter
import event
import org_events
from event import EventSet, MergingDict
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

def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class EvolutionCalendar:
    '''One Evolution calendar, including its events'''

    def __init__(self, evocalendar, gio_cancellable):
        self._evocalendar = evocalendar
        self._cancellable = gio_cancellable
        self._events = None
        self._uid = evocalendar.get_uid()

    @property
    def uid(self):
        return self._uid

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

            cconverter = CalConverter(TZResolver(client))
            for v in values:
                if v is not None:
                    self._events.add(event.from_evolution(v, cconverter=cconverter))

        return self._events

    def merge(self, other):
        oc = org_events.OrgCalendar(self.name, self.uid, self.events)
        return oc.merge(other)


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

            self._calendars = MergingDict()
            for c in calendars:
                # reuse cancellation stack
                self._calendars[c.get_uid()] = EvolutionCalendar(c, self._cancellable)

        return self._calendars


def fetch(orgfile_name):
    '''Get and write events'''
    buf = io.StringIO()
    events = EvolutionEvents()
    unparser = org_events.OrgEventUnparser(buf)
    unparser.unparse_all(events.calendars)

    with open(orgfile_name, 'w') as output:
        output.write(buf.getvalue())

def update(orgfile_name):
    '''Get and write events'''
    buf = io.StringIO()
    events = EvolutionEvents()

    parse = org_events.OrgEventParser()
    local_cals = parse.load(orgfile_name)
    remote_cals = events.calendars

    merged_cals = local_cals.merge(remote_cals)

    unparser = org_events.OrgEventUnparser(buf)
    unparser.unparse_all(merged_cals)

    with open(orgfile_name, 'w') as output:
        output.write(buf.getvalue())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Synchronise running Evolution server with Emacs org-agenda file (read-only, for now)')
    parser.add_argument('orgfile', metavar='ORGFILE', type=str, help='Org file to write to or synchronise with')
    parser.add_argument('--fetch', '-F', action='store_const', dest='activity', const=fetch, default=fetch,
                        help='Load from Evolution and overwrite org file (default)')
    parser.add_argument('--update', '-U', action='store_const', dest='activity', const=update, default=fetch,
                        help='Load from Evolution and merge with existing org file (experimental)')
    parser.add_argument('--debug', action='store_const', dest='conf_EMIT_DEBUG', const=True, default=False,
                        help='Enable debug output (may not produce well-formed org files)')

    args = parser.parse_args()
    EMIT_DEBUG=args.conf_EMIT_DEBUG

    args.activity(orgfile_name=args.orgfile)

    # events = EvolutionEvents()
    # unparser = OrgUnparser(sys.stdout)
    # unparser.print_header()
    # for cal in events.calendars:
    #     unparser.unparse_calendar(cal)


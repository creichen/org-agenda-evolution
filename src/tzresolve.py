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

import gi
import sys
from zoneinfo import ZoneInfo

gi.require_version('ICal', '3.0')
from gi.repository import ICal


def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

BAD_TIMEZONES = []

class TZResolver:
    FREEASSOCIATION_MAGIC_PREFIX = '/freeassociation.sourceforge.net/'

    def __init__(self, ecal_client):
        self.cache = {}
        self.ecal_client = ecal_client

    def _lookup(self, tzname):
        if tzname.startswith(TZResolver.FREEASSOCIATION_MAGIC_PREFIX):
            tzname = tzname[len(TZResolver.FREEASSOCIATION_MAGIC_PREFIX):]

        if tzname in self.cache:
            return self.cache[tzname]

        try:
            return ZoneInfo(tzname)
        except ValueError:
            return None

    def _custom_vtimezone_part(self, vtimezone_part):
        # FIXME

        # ICal.icalproperty_get_tzoffsetfrom() expects a Property, but we don't have the enum int encoding
        # for TZOFFSETFROM and TZOFFSETTO, otherwise we could probably get those values more easily
        # already.  This can probably be solved by finding something analogous to 'kind_from_string' in
        # _custom_vtimezone and calling vtimezone_part.get_first_proeprty(Mystery.kind_from_String('TZOFFSETFROM'))
        # but I haven't had the time to look more.

        #delta_from = ICal.icalproperty_get_tzoffsetfrom(vtimezone_part)
        #delta_to = ICal.icalproperty_get_tzoffsetto(vtimezone_part)
        #perr(f'  -> deltas : {delta_from} / {delta_to}');
        # FIXME: Event.from_evolution(), package utilise
        pass

    def _custom_vtimezone(self, vtimezone):
        DAYLIGHT = type(vtimezone).kind_from_string('DAYLIGHT')
        STANDARD = type(vtimezone).kind_from_string('STANDARD')
        # These guys are essentially Events, including recurrences:
        standard_time = self._custom_vtimezone_part(vtimezone.get_first_component(STANDARD))
        daylight_time = self._custom_vtimezone_part(vtimezone.get_first_component(DAYLIGHT))
        # FIXME: package utilise

    def __getitem__(self, tzname : str):
        '''Look up time zone bu name'''
        # FIXME: use __call__ for ZoneInfo compatibility?
        if tzname is None:
            return None

        zinfo = self._lookup(tzname)

        if not zinfo:
            perr(f'Struggling with "{tzname}", asking client')
            success, tz = self.ecal_client.get_timezone_sync(tzname)
            if not success:
                perr('-> ECal does not know its own time zone?')
            else:
                zinfo = self._lookup(tz.get_tzid())
                if not zinfo:
                    vtimezone = tz.get_component()
                    # get_first_property
                    self._custom_vtimezone(vtimezone)
                    BAD_TIMEZONES.append(tz)
                    perr(f'-> ECal found it: "{tz.get_display_name()}"')
                    try:
                        perr(f'-> utc offset: {tz.get_utc_offset(None)}')
                    except _:
                        pass

        self.cache[tzname] = zinfo
        return zinfo

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
import zoneinfo
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
        except (ValueError, zoneinfo._common.ZoneInfoNotFoundError, ModuleNotFoundError):
            return None

    def _custom_vtimezone_part(self, vtimezone_part, TZOFFSETFROM):
        # FIXME
        #OFFSETFROM = type(vtimezone_part).kind_from_string('TZOFFSETFROM')
        #OFFSETTO = type(vtimezone_part).kind_from_string('TZOFFSETTO')
        #TZOFFSETFROM = type(vtimezone_part).kind_from_string('TZOFFSETFROM')
        dstz = vtimezone_part

        PREFIX = 'TZOFFSETFROM:'

        matches = [line for line in dstz.as_ical_string().split('\n')
                   if line.startswith(PREFIX)]
        if len(matches) == 1:
            delta = matches[0][len(PREFIX):]
            delta_sign = 1
            if (delta.startswith('+')):
                delta_sign = 1
                delta = delta[1:]
            elif (delta.startswith('-')):
                delta_sign = -1
                delta = delta[1:]
            delta_h = int(delta[0:2])
            delta_min = int(delta[2:4])
            #print(f' tzdelta = sign={delta_sign}, {delta_h}h, {delta_min}min')


        # offset = None
        # prop = dstz.find_property('TZOFFSETFROM')
        # print(prop)
        # exit(1)
        # # print(dir(prop))
        # # properties = prop.get_components()#properties('TZOFFSETFROM')
        # # for p in properties:
        # #     perr('!!--')
        # #     print(p.as_ical_string())
        # #     perr('----')
        # if prop:
        #     perr(prop.as_ical_string())
        #     offset = prop.get_tzoffsetfrom()
        #     perr(dir(dstz.get_inner().get_first_property(TZOFFSETFROM)))
        #     perr(f'off={offset}')
        #     exit(1)
        # return offset

        # # ICal.icalproperty_get_tzoffsetfrom() expects a Property, but we don't have the enum int encoding
        # # for TZOFFSETFROM and TZOFFSETTO, otherwise we could probably get those values more easily
        # # already.  This can probably be solved by finding something analogous to 'kind_from_string' in
        # # _custom_vtimezone and calling vtimezone_part.get_first_proeprty(Mystery.kind_from_String('TZOFFSETFROM'))
        # # but I haven't had the time to look more.

        # #delta_from = ICal.icalproperty_get_tzoffsetfrom(vtimezone_part)
        # #delta_to = ICal.icalproperty_get_tzoffsetto(vtimezone_part)
        # #perr(f'  -> deltas : {delta_from} / {delta_to}');
        # # FIXME: Event.from_evolution(), package utilise
        # pass

    def _custom_vtimezone(self, vtimezone):
        DAYLIGHT = type(vtimezone).kind_from_string('DAYLIGHT')
        STANDARD = type(vtimezone).kind_from_string('STANDARD')
        TZOFFSETFROM = type(vtimezone).kind_from_string('TZOFFSETFROM')
        # These guys are essentially Events, including recurrences:
        standard_time = self._custom_vtimezone_part(vtimezone.get_first_component(STANDARD), TZOFFSETFROM)
        daylight_time = self._custom_vtimezone_part(vtimezone.get_first_component(DAYLIGHT), TZOFFSETFROM)
        # FIXME: package utilise

    def __getitem__(self, tzname : str):
        '''Look up time zone bu name'''
        # FIXME: use __call__ for ZoneInfo compatibility?
        if tzname is None:
            return None

        zinfo = self._lookup(tzname)

        if not zinfo:
            #perr(f'Struggling with "{tzname}", asking client')
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
                    #perr(f'-> ECal found it: "{tz.get_display_name()}"')
                    try:
                        #perr(f'-> utc offset: {tz.get_utc_offset(None)}')
                        pass
                    except _:
                        pass

        self.cache[tzname] = zinfo
        return zinfo

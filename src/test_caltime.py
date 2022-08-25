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

import unittest
import itertools
import caltime
import tzresolve
from caltime import *
from test_mock import mock_class

MockTS = mock_class('MockTS', ['year', 'month', 'day', 'hour', 'minute'],
                    { 'timezone' : None, 'tzid' : None, '*null_time' : False })


dt = CalTime.from_str

class TestCalTime(unittest.TestCase):

    def setUp(self):
        self.converter = CalConverter(tzresolve.TZResolver(None))

    def test_1993(self):
        t = self.converter.time_from_evolution(MockTS(1993, 10, 27, 14, 11))
        self.assertEqual('1993-10-27 Wed', t.date_str())
        self.assertEqual('14:11', t.time_str())
        self.assertEqual('Wed', t.weekday_str())

    def test_2022(self):
        t = self.converter.time_from_evolution(MockTS(2022, 7, 29, 3, 59))
        self.assertEqual('2022-07-29 Fri', t.date_str())
        self.assertEqual('03:59', t.time_str())
        self.assertEqual('Fri', t.weekday_str())

    def test_null(self):
        t = self.converter.time_from_evolution(MockTS(2022, 7, 29, 3, 59, null_time=True))
        self.assertIs(None, t)

    def test_from_str(self):
        t = CalTime.from_str('2022-07-29')
        self.assertEqual('2022-07-29 Fri', t.date_str())
        self.assertEqual('00:00', t.time_str())
        self.assertEqual('Fri', t.weekday_str())

    def test_from_str_time(self):
        t = CalTime.from_str('2022-07-29T03:59')
        self.assertEqual('2022-07-29 Fri', t.date_str())
        self.assertEqual('03:59', t.time_str())
        self.assertEqual('Fri', t.weekday_str())

    def test_add_time(self):
        t = CalTime.from_str('2022-07-21T03:59')
        t = t + timedelta(weeks=1)
        t += timedelta(days=1)
        self.assertEqual('2022-07-29 Fri', t.date_str())
        self.assertEqual('03:59', t.time_str())
        self.assertEqual('Fri', t.weekday_str())

    def test_days_in_month(self):
        for leap_year in [True, False]:
            expected = [-1, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            year = 2003
            if leap_year:
                expected[2] = 29
                year = 2004

            for m in range(1, 13):
                for d in range(1, expected[m] + 1):
                    for t in ((0, 0), (12,0), (23,59)):
                        t = CalTime(year, m, d, t[0], t[1])
                        if expected[m] != t.number_of_days_in_month():
                            print(f'{t} : {t.number_of_days_in_month()}')
                        self.assertEqual(expected[m], t.number_of_days_in_month())

    def test_month_increment(self):
        self.assertEqual(dt('2000-02-01'), MonthIncrement(1) + dt('2000-01-01'))
        self.assertEqual(dt('2000-03-01'), MonthIncrement(2) + dt('2000-01-01'))
        self.assertEqual(dt('2000-08-01'), MonthIncrement(7) + dt('2000-01-01'))

        self.assertEqual(dt('2000-03-31'), MonthIncrement(2) + dt('2000-01-31'))
        self.assertEqual(dt('2000-02-29'), MonthIncrement(1) + dt('2000-01-31'))

    def test_year_increment(self):
        self.assertEqual(dt('2001-01-01'), YearIncrement(1) + dt('2000-01-01'))
        self.assertEqual(dt('2010-01-01'), YearIncrement(10) + dt('2000-01-01'))

        self.assertEqual(dt('2001-01-31'), YearIncrement(1) + dt('2000-01-31'))
        self.assertEqual(dt('2001-02-28'), YearIncrement(1) + dt('2000-02-29'))

def enum_obj(value_name):
    class ETest:
        def __init__(self):
            self.value_name = value_name
    ETest.__qualified_name__ = f'ETest.{value_name}'
    return ETest()


I_NONE   = enum_obj('I_CAL_NO_RECURRENCE')
I_SECOND = enum_obj('I_CAL_SECONDLY_RECURRENCE')
I_MINUTE = enum_obj('I_CAL_MINUTELY_RECURRENCE')
I_HOUR   = enum_obj('I_CAL_HOURLY_RECURRENCE')
I_DAY    = enum_obj('I_CAL_DAILY_RECURRENCE')
I_WEEK   = enum_obj('I_CAL_WEEKLY_RECURRENCE')
I_MONTH  = enum_obj('I_CAL_MONTHLY_RECURRENCE')
I_YEAR   = enum_obj('I_CAL_YEARLY_RECURRENCE')

I_CAL_SUNDAY_WEEKDAY = enum_obj('I_CAL_SUNDAY_WEEKDAY')
I_CAL_MONDAY_WEEKDAY = enum_obj('I_CAL_MONDAY_WEEKDAY')

MockRecurrence = mock_class('MockRecurrence',
                            ['freq', 'interval', 'count'],
                            { 'by_set_pos_array'   : [32639] * 386,
                              'by_year_day_array'  : [32639] * 386,
                              'by_month_day_array' : [32639] * 32,
                              'by_week_no_array'   : [32639] * 56,
                              'by_day_array'       : [32639] * 386,
                              'by_hour_array'      : [32639] * 25,
                              'by_minute_array'    : [32639] * 61,
                              'by_second_array'    : [32639] * 62,
                              'week_start'	   : I_CAL_MONDAY_WEEKDAY,
                              'until' 		   : None,
                              })

def take(iter, n):
    return list(itertools.islice(iter, n))

class TestRecurrence(unittest.TestCase):

    def setUp(self):
        self.converter = CalConverter(tzresolve.TZResolver(None))

    def dt(self, ts):
        return self.converter.time_from_str(ts)

    def test_secondly(self):
        occ = MockRecurrence(I_SECOND, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(str, type(rec)) # "Unsupported" message

    def test_minutely(self):
        occ = MockRecurrence(I_MINUTE, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertEqual('+1m', rec.spec)
        it = rec.range_from(self.dt('2020-01-01T11:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual(self.dt('2020-01-01T11:00'), it.start_date)
        self.assertEqual([self.dt('2020-01-01T11:00/UTC'),
                          self.dt('2020-01-01T11:01/UTC'),
                          self.dt('2020-01-01T11:02/UTC'),
                          self.dt('2020-01-01T11:03/UTC'),
                          self.dt('2020-01-01T11:04/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([self.dt('2020-02-14T13:30/UTC'),
                          self.dt('2020-02-14T13:31/UTC'),
                          self.dt('2020-02-14T13:32/UTC'),
                          ],
                         take(it.starting(self.dt('2020-02-14T13:30')), 3))

    def test_hourly(self):
        occ = MockRecurrence(I_HOUR, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertEqual('+1h', rec.spec)
        it = rec.range_from(self.dt('2020-01-01T11:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual(self.dt('2020-01-01T11:00'), it.start_date)
        self.assertEqual([self.dt('2020-01-01T11:00/UTC'),
                          self.dt('2020-01-01T12:00/UTC'),
                          self.dt('2020-01-01T13:00/UTC'),
                          self.dt('2020-01-01T14:00/UTC'),
                          self.dt('2020-01-01T15:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([self.dt('2020-02-14T13:00/UTC'),
                          self.dt('2020-02-14T14:00/UTC'),
                          self.dt('2020-02-14T15:00/UTC'),
                          ],
                         take(it.starting(self.dt('2020-02-14T13:00')), 3))

    def test_hourly_from_offset(self):
        occ = MockRecurrence(I_HOUR, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        it = rec.range_from(self.dt('2020-01-01T11:30'))
        self.assertEqual([self.dt('2020-02-14T13:30/UTC'),
                          self.dt('2020-02-14T14:30/UTC'),
                          self.dt('2020-02-14T15:30/UTC'),
                          ],
                         take(it.starting(self.dt('2020-02-14T13:28')), 3))

    def test_hourly_from_before(self):
        occ = MockRecurrence(I_HOUR, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        it = rec.range_from(self.dt('2020-02-14T13:30'))
        self.assertEqual([self.dt('2020-02-14T13:30/UTC'),
                          self.dt('2020-02-14T14:30/UTC'),
                          self.dt('2020-02-14T15:30/UTC'),
                          ],
                         take(it.starting(self.dt('2020-02-10T00:00')), 3))

    def test_daily_unbounded(self):
        occ = MockRecurrence(I_DAY, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertEqual('+1d', rec.spec)
        it = rec.range_from(self.dt('2020-01-28T11:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual(self.dt('2020-01-28T11:00'), it.start_date)
        self.assertEqual([self.dt('2020-01-28T11:00/UTC'),
                          self.dt('2020-01-29T11:00/UTC'),
                          self.dt('2020-01-30T11:00/UTC'),
                          self.dt('2020-01-31T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([self.dt('2020-02-14T11:00/UTC'),
                          self.dt('2020-02-15T11:00/UTC'),
                          self.dt('2020-02-16T11:00/UTC'),
                          ],
                         take(it.starting(self.dt('2020-02-13T13:30')), 3))

    def test_daily_five_times(self):
        occ = MockRecurrence(I_DAY, 1, 5)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2020-01-28T11:00'))
        self.assertTrue(it.is_finite())
        self.assertEqual(self.dt('2020-01-28T11:00'), it.start_date)
        self.assertEqual([self.dt('2020-01-28T11:00/UTC'),
                          self.dt('2020-01-29T11:00/UTC'),
                          self.dt('2020-01-30T11:00/UTC'),
                          self.dt('2020-01-31T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2020-01-31T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          ],
                         take(it.starting(self.dt('2020-01-30T13:30')), 10))

    def test_daily_until(self):
        occ = MockRecurrence(I_DAY, 1, 0, until=MockTS(2020, 2, 1, 12, 0))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2020-01-28T11:00'))
        self.assertTrue(it.is_finite())
        self.assertEqual(self.dt('2020-01-28T11:00'), it.start_date)
        self.assertEqual([self.dt('2020-01-28T11:00/UTC'),
                          self.dt('2020-01-29T11:00/UTC'),
                          self.dt('2020-01-30T11:00/UTC'),
                          self.dt('2020-01-31T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2020-01-31T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          ],
                         take(it.starting(self.dt('2020-01-30T13:30')), 10))

    def test_every_second_day(self):
        occ = MockRecurrence(I_DAY, 2, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertEqual('+2d', rec.spec)
        it = rec.range_from(self.dt('2020-01-28T11:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual(self.dt('2020-01-28T11:00'), it.start_date)
        self.assertEqual([self.dt('2020-01-28T11:00/UTC'),
                          self.dt('2020-01-30T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          self.dt('2020-02-03T11:00/UTC'),
                          self.dt('2020-02-05T11:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([self.dt('2020-02-15T11:00/UTC'),
                          self.dt('2020-02-17T11:00/UTC'),
                          self.dt('2020-02-19T11:00/UTC'),
                          ],
                         take(it.starting(self.dt('2020-02-13T13:30')), 3))

    def test_every_wednesday_until(self):
        occ = MockRecurrence(I_WEEK, 1, 0, by_day_array=[4] + ([32639] * 385), until=MockTS(2022, 6, 7, 12, 0))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-05-11T12:00'))
        self.assertTrue(it.is_finite())
        self.assertEqual([self.dt('2022-05-11T12:00/UTC'),
                          self.dt('2022-05-18T12:00/UTC'),
                          self.dt('2022-05-25T12:00/UTC'),
                          self.dt('2022-06-01T12:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2022-06-01T12:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-05-28T13:30')), 10))

    def test_every_wednesday_until_starting_tuesday(self):
        occ = MockRecurrence(I_WEEK, 1, 0, by_day_array=[4] + ([32639] * 385), until=MockTS(2022, 6, 7, 12, 0))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-05-10T12:00'))
        self.assertTrue(it.is_finite())
        self.assertEqual([self.dt('2022-05-10T12:00/UTC'),
                          self.dt('2022-05-11T12:00/UTC'),
                          self.dt('2022-05-18T12:00/UTC'),
                          self.dt('2022-05-25T12:00/UTC'),
                          self.dt('2022-06-01T12:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2022-06-01T12:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-05-28T13:30')), 10))

    def test_every_mon_wed_thu(self):
        occ = MockRecurrence(I_WEEK, 1, 0, by_day_array=[2, 4, 5] + ([32639] * 383))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-05-11T12:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual([self.dt('2022-05-11T12:00/UTC'),
                          self.dt('2022-05-12T12:00/UTC'),
                          self.dt('2022-05-16T12:00/UTC'),
                          self.dt('2022-05-18T12:00/UTC'),
                          self.dt('2022-05-19T12:00/UTC'),
                          self.dt('2022-05-23T12:00/UTC'),
                          self.dt('2022-05-25T12:00/UTC'),
                          self.dt('2022-05-26T12:00/UTC'),
                          self.dt('2022-05-30T12:00/UTC'),
                          self.dt('2022-06-01T12:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2022-05-25T12:00/UTC'),
                          self.dt('2022-05-26T12:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-05-24T13:30')), 2))

    def test_every_mon_wed_thu_with_start_on_tuesday(self):
        occ = MockRecurrence(I_WEEK, 1, 0, by_day_array=[2, 4, 5] + ([32639] * 383))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-05-10T12:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual([self.dt('2022-05-10T12:00/UTC'),
                          self.dt('2022-05-11T12:00/UTC'),
                          self.dt('2022-05-12T12:00/UTC'),
                          self.dt('2022-05-16T12:00/UTC'),
                          self.dt('2022-05-18T12:00/UTC'),
                          self.dt('2022-05-19T12:00/UTC'),
                          self.dt('2022-05-23T12:00/UTC'),
                          self.dt('2022-05-25T12:00/UTC'),
                          self.dt('2022-05-26T12:00/UTC'),
                          self.dt('2022-05-30T12:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2022-05-25T12:00/UTC'),
                          self.dt('2022-05-26T12:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-05-24T13:30')), 2))
        self.assertEqual('{inc=7 days, 0:00:00, subit=Weekdays<sun=6>[from=0+[0, 2, 3]]}', str(rec))

    def test_weekly(self):
        occ = MockRecurrence(I_WEEK, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertEqual('+1w', rec.spec)
        it = rec.range_from(self.dt('2022-02-10T00:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual([self.dt('2022-02-10T00:00/UTC'),
                          self.dt('2022-02-17T00:00/UTC'),
                          self.dt('2022-02-24T00:00/UTC'),
                          self.dt('2022-03-03T00:00/UTC'),
                          self.dt('2022-03-10T00:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([
                          self.dt('2022-05-26T00:00/UTC'),
                          self.dt('2022-06-02T00:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-05-24T13:30')), 2))

    def test_every_third_weekly(self):
        occ = MockRecurrence(I_WEEK, 3, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertEqual('+3w', rec.spec)
        it = rec.range_from(self.dt('2022-02-10T00:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual([self.dt('2022-02-10T00:00/UTC'),
                          self.dt('2022-03-03T00:00/UTC'),
                          self.dt('2022-03-24T00:00/UTC'),
                          self.dt('2022-04-14T00:00/UTC'),
                          self.dt('2022-05-05T00:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([
                          self.dt('2022-05-26T00:00/UTC'),
                          self.dt('2022-06-16T00:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-05-24T13:30')), 2))

    def test_every_fourth_wendesday_per_month(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[36] + ([32639] * 385))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2022-02-10T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2022-02-10T00:00/UTC'),
                              self.dt('2022-02-23T00:00/UTC'),
                              self.dt('2022-03-23T00:00/UTC'),
                              self.dt('2022-04-27T00:00/UTC'),
                              self.dt('2022-05-25T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([
                              self.dt('2022-04-27T00:00/UTC'),
                              self.dt('2022-05-25T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-24T13:30')), 2))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_tuesday_every_two_weeks(self):
        occ = MockRecurrence(I_WEEK, 2, 4, by_day_array=[3] + ([32639] * 385))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-01-04T00:00'))
        self.assertTrue(it.is_finite())
        self.assertEqual([self.dt('2022-01-04T00:00/UTC'),
                          self.dt('2022-01-18T00:00/UTC'),
                          self.dt('2022-02-01T00:00/UTC'),
                          self.dt('2022-02-15T00:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2022-02-01T00:00/UTC'),
                          self.dt('2022-02-15T00:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-01-31T13:30')), 10))
        self.assertEqual('{inc=14 days, 0:00:00, subit=Weekdays<sun=6>[from=1+[0]], count=4}', str(rec))

    def test_every_first_sunday_per_month(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 77, by_day_array=[9] + ([32639] * 385))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2022-02-06T00:00'))
            self.assertTrue(it.is_finite())
            self.assertEqual([self.dt('2022-02-06T00:00/UTC'),
                              self.dt('2022-03-06T00:00/UTC'),
                              self.dt('2022-04-03T00:00/UTC'),
                              self.dt('2022-05-01T00:00/UTC'),
                              self.dt('2022-06-05T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([
                              self.dt('2022-04-03T00:00/UTC'),
                              self.dt('2022-05-01T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE


    def test_every_second_sunday_per_month_outlook(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[17] + ([32639] * 385))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-02-13T00:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual([self.dt('2022-02-13T00:00/UTC'),
                          self.dt('2022-03-13T00:00/UTC'),
                          self.dt('2022-04-10T00:00/UTC'),
                          self.dt('2022-05-08T00:00/UTC'),
                          self.dt('2022-06-12T00:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([
                          self.dt('2022-04-10T00:00/UTC'),
                          self.dt('2022-05-08T00:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-04-01T13:30')), 2))

    def test_every_second_saturday_per_month_outlook(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[23] + ([32639] * 385))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-02-12T00:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual([self.dt('2022-02-12T00:00/UTC'),
                          self.dt('2022-03-12T00:00/UTC'),
                          self.dt('2022-04-09T00:00/UTC'),
                          self.dt('2022-05-14T00:00/UTC'),
                          self.dt('2022-06-11T00:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([
                          self.dt('2022-04-09T00:00/UTC'),
                          self.dt('2022-05-14T00:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-04-01T13:30')), 2))

    def test_every_second_day_per_two_months(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 2, 0, by_month_day_array=[2] + ([32639] * 31))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2022-02-02T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2022-02-02T00:00/UTC'),
                              self.dt('2022-04-02T00:00/UTC'),
                              self.dt('2022-06-02T00:00/UTC'),
                              self.dt('2022-08-02T00:00/UTC'),
                              self.dt('2022-10-02T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([
                              self.dt('2022-04-02T00:00/UTC'),
                              self.dt('2022-06-02T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
            self.assertEqual('{inc={months+=2}, subit=MonthDays<sun=6>[2]}', str(rec))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_last_sunday_per_month_outlook(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[-9] + ([32639] * 385), week_start=I_CAL_MONDAY_WEEKDAY)
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2022-01-30T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2022-01-30T00:00/UTC'),
                              self.dt('2022-02-27T00:00/UTC'),
                              self.dt('2022-03-27T00:00/UTC'),
                              self.dt('2022-04-24T00:00/UTC'),
                              self.dt('2022-05-29T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([self.dt('2022-04-24T00:00/UTC'),
                              self.dt('2022-05-29T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_last_friday_per_month_outlook(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[-14] + ([32639] * 385), week_start=I_CAL_MONDAY_WEEKDAY)
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2022-01-28T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2022-01-28T00:00/UTC'),
                              self.dt('2022-02-25T00:00/UTC'),
                              self.dt('2022-03-25T00:00/UTC'),
                              self.dt('2022-04-29T00:00/UTC'),
                              self.dt('2022-05-27T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([
                              self.dt('2022-04-29T00:00/UTC'),
                              self.dt('2022-05-27T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_last_sunday_per_month_evolution(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[-1] + ([32639] * 385), by_day_array=[1] + ([32639] * 385))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2022-01-30T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2022-01-30T00:00/UTC'),
                              self.dt('2022-02-27T00:00/UTC'),
                              self.dt('2022-03-27T00:00/UTC'),
                              self.dt('2022-04-24T00:00/UTC'),
                              self.dt('2022-05-29T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([self.dt('2022-04-24T00:00/UTC'),
                              self.dt('2022-05-29T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_last_monday_per_month(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[-1] + ([32639] * 385), by_day_array=[2] + ([32639] * 385))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2022-01-31T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2022-01-31T00:00/UTC'),
                              self.dt('2022-02-28T00:00/UTC'),
                              self.dt('2022-03-28T00:00/UTC'),
                              self.dt('2022-04-25T00:00/UTC'),
                              self.dt('2022-05-30T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([self.dt('2022-04-25T00:00/UTC'),
                              self.dt('2022-05-30T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
            self.assertEqual('{inc={months+=1}, subit=MonthWeekDays<sun=6>(+[], -[[], [0]])}', str(rec))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_third_monday_alt(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[3] + ([32639] * 385), by_day_array=[2] + ([32639] * 385))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2021-11-15T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2021-11-15T00:00/UTC'),
                              self.dt('2021-12-20T00:00/UTC'),
                              self.dt('2022-01-17T00:00/UTC'),
                              self.dt('2022-02-21T00:00/UTC'),
                              self.dt('2022-03-21T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([self.dt('2022-04-18T00:00/UTC'),
                              self.dt('2022-05-16T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_third_sunday_alt(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[3] + ([32639] * 385), by_day_array=[1] + ([32639] * 385))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2021-11-21T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2021-11-21T00:00/UTC'),
                              self.dt('2021-12-19T00:00/UTC'),
                              self.dt('2022-01-16T00:00/UTC'),
                              self.dt('2022-02-20T00:00/UTC'),
                              self.dt('2022-03-20T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([self.dt('2022-04-17T00:00/UTC'),
                              self.dt('2022-05-15T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
            self.assertEqual('{inc={months+=1}, subit=MonthWeekDays<sun=6>(+[[], [], [], [6]], -[])}', str(rec))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_25th_of_january(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_YEAR, 1, 0, by_month_day_array=[25] + ([32639] * 31))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2021-01-25T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2021-01-25T00:00/UTC'),
                              self.dt('2022-01-25T00:00/UTC'),
                              self.dt('2023-01-25T00:00/UTC'),
                              self.dt('2024-01-25T00:00/UTC'),
                              self.dt('2025-01-25T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([self.dt('2023-01-25T00:00/UTC'),
                              self.dt('2024-01-25T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_29th_of_february(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_YEAR, 1, 0, by_month_day_array=[29] + ([32639] * 31))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('1996-02-29T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('1996-02-29T00:00/UTC'),
                              self.dt('2000-02-29T00:00/UTC'),
                              self.dt('2004-02-29T00:00/UTC'),
                              self.dt('2008-02-29T00:00/UTC'),
                              self.dt('2012-02-29T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            # If you are still using this in 2100, I shall weep for the human race from beyond the grave.
            self.assertEqual([self.dt('2096-02-29T00:00/UTC'),
                              self.dt('2104-02-29T00:00/UTC'),
                              self.dt('2108-02-29T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2095-04-01T13:30')), 3))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_1st_monday_in_march(self):
        #caltime.DEBUGPRINT = print
        try:
            occ = MockRecurrence(I_YEAR, 1, 0, by_day_array=[10] + ([32639] * 385))
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(self.dt('2021-03-01T00:00'))
            self.assertFalse(it.is_finite())
            self.assertEqual([self.dt('2021-03-01T00:00/UTC'),
                              self.dt('2022-03-07T00:00/UTC'),
                              self.dt('2023-03-06T00:00/UTC'),
                              self.dt('2024-03-04T00:00/UTC'),
                              self.dt('2025-03-03T00:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual([
                              self.dt('2023-03-06T00:00/UTC'),
                              self.dt('2024-03-04T00:00/UTC'),
                              ],
                             take(it.starting(self.dt('2022-04-01T13:30')), 2))
            self.assertEqual('{inc={years+=1}, subit=MonthWeekDays<sun=6>(+[[], [0]], -[])}', str(rec))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_every_20th_of_july(self):
        occ = MockRecurrence(I_YEAR, 1, 0)
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertEqual('+1Y', rec.spec)
        it = rec.range_from(self.dt('1969-07-20T00:00'))
        self.assertFalse(it.is_finite())
        self.assertEqual([self.dt('1969-07-20T00:00/UTC'),
                          self.dt('1970-07-20T00:00/UTC'),
                          self.dt('1971-07-20T00:00/UTC'),
                          self.dt('1972-07-20T00:00/UTC'),
                          self.dt('1973-07-20T00:00/UTC'),
                          ],
                         take(it.all(), 5))
        self.assertEqual([self.dt('2022-07-20T00:00/UTC'),
                          self.dt('2023-07-20T00:00/UTC'),
                          ],
                         take(it.starting(self.dt('2022-04-01T13:30')), 2))
        self.assertEqual('{spec=+1Y, inc={years+=1}}', str(rec))

    def test_weekstart_monday(self):
        # DTSTART:19970805T090000
        # RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=MO
        # ==> 1997 Aug 5,10,19,24

        #caltime.DEBUGPRINT = print
        try:
            start = self.converter.time_from_evolution(MockTS(1997, 8, 5, 10, 00))
            occ = MockRecurrence(I_WEEK, 2, 4, by_day_array=[3, 1] + ([32639] * 384), week_start=I_CAL_MONDAY_WEEKDAY)
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(start)
            self.assertTrue(it.is_finite())
            self.assertEqual([self.dt('1997-08-05T10:00/UTC'),
                              self.dt('1997-08-10T10:00/UTC'),
                              self.dt('1997-08-19T10:00/UTC'),
                              self.dt('1997-08-24T10:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual('{inc=14 days, 0:00:00, subit=Weekdays<sun=6>[from=1+[0, 5]], count=4}', str(rec))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE


    def test_weekstart_sunday(self):
        # DTSTART:19970805T090000
        # RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=SU
        # ==> 1997 August 5,17,19,31

        #caltime.DEBUGPRINT = print
        try:
            start = self.converter.time_from_evolution(MockTS(1997, 8, 5, 10, 00))
            occ = MockRecurrence(I_WEEK, 2, 4, by_day_array=[1, 3] + ([32639] * 384), week_start=I_CAL_SUNDAY_WEEKDAY)
            rec = self.converter.recurrence_from_evolution(occ)
            self.assertIs(None, rec.spec)
            it = rec.range_from(start)
            self.assertTrue(it.is_finite())
            self.assertEqual([self.dt('1997-08-05T10:00/UTC'),
                              self.dt('1997-08-17T10:00/UTC'),
                              self.dt('1997-08-19T10:00/UTC'),
                              self.dt('1997-08-31T10:00/UTC'),
                              ],
                             take(it.all(), 5))
            self.assertEqual('{inc=14 days, 0:00:00, subit=Weekdays<sun=-1>[from=-1+[0, 2]], count=4}', str(rec))
        finally:
            caltime.DEBUGPRINT = DEBUGPRINT_NONE

    def test_until_exact(self):
        '''"until" matches one of the recurrences'''
        occ = MockRecurrence(I_DAY, 1, 0, until=MockTS(2020, 2, 1, 11, 0))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2020-01-28T11:00'))
        self.assertTrue(it.is_finite())
        self.assertEqual(self.dt('2020-01-28T11:00'), it.start_date)
        self.assertEqual([self.dt('2020-01-28T11:00/UTC'),
                          self.dt('2020-01-29T11:00/UTC'),
                          self.dt('2020-01-30T11:00/UTC'),
                          self.dt('2020-01-31T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          ],
                         take(it.all(), 10))
        self.assertEqual([
                          self.dt('2020-01-31T11:00/UTC'),
                          self.dt('2020-02-01T11:00/UTC'),
                          ],
                         take(it.starting(self.dt('2020-01-30T13:30')), 10))

    def test_cross_dst_boundary(self):
        '''DST messing things up again'''
        occ = MockRecurrence(I_DAY, 1, 0, until=MockTS(2022, 3, 28, 8, 0, tzid='Europe/Berlin'))
        rec = self.converter.recurrence_from_evolution(occ)
        self.assertIs(None, rec.spec)
        it = rec.range_from(self.dt('2022-03-26T08:00/Europe/Berlin'))
        self.assertTrue(it.is_finite())
        self.assertEqual(self.dt('2022-03-26T07:00/UTC'), it.start_date.astimezone(None))
        self.assertEqual([self.dt('2022-03-26T07:00/UTC'),
                          self.dt('2022-03-27T06:00/UTC'),
                          self.dt('2022-03-28T06:00/UTC'),
                          ],
                         [tstamp.astimezone(None) for tstamp in  take(it.all(), 10)])

if __name__ == '__main__':
    unittest.main()

import unittest
from caltime import *

def mock_class(name, pos_args, named_args_and_defaults):
    class C:
        pass

    C.__name__ = name
    C.__qualname__ = name

    def attrname(s):
        if s[0] == '*':
            return s[1:]
        return s

    named_args = set(attrname(n) for n in named_args_and_defaults)

    def init(s, *args, **kwargs):
        assert(len(args) == len(pos_args))
        for (i, a) in enumerate(pos_args):
            setattr(s, attrname(a), args[i])

        for k, v in named_args_and_defaults.items():
            setattr(s, attrname(k), v)

        for k, v in kwargs.items():
            assert k in named_args
            setattr(s, attrname(k), v)

    setattr(C, '__init__', init)

    def mkget(name):
        name = attrname(name)
        def get(s):
            return getattr(s, name)
        return get

    for n in list(pos_args) + list(named_args_and_defaults.keys()):
        prefix = 'get_'
        if n[0] == '*':
            prefix = 'is_'

        setattr(C, prefix + attrname(n), mkget(n))
    return C


class TestMockClass(unittest.TestCase):

    def test_positional(self):
        T = mock_class('T', ['a', 'b'], {})
        t = T(1,2)
        self.assertEqual(1, t.get_a())
        self.assertEqual(2, t.get_b())

    def test_positional_bounds(self):
        T = mock_class('T', ['a', 'b'], {})

        self.assertRaises(Exception, lambda: T(1))
        self.assertRaises(Exception, lambda: T(1,2,3))

    def test_keyword(self):
        T2 = mock_class('T', [], {'a': 1, 'b': "foo"})

        t = T2()
        self.assertEqual(1, t.get_a())
        self.assertEqual("foo", t.get_b())

        t = T2(a=2)
        self.assertEqual(2, t.get_a())
        self.assertEqual("foo", t.get_b())

        t = T2(b="bar")
        self.assertEqual(1, t.get_a())
        self.assertEqual("bar", t.get_b())

        t = T2(b="quux", a=3)
        self.assertEqual(3, t.get_a())
        self.assertEqual("quux", t.get_b())

    def test_keyword_bounds(self):
        T3 = mock_class('T', [], {'a': 1, 'b': "foo"})
        self.assertRaises(Exception, lambda: T(c=3))

    def test_keyword_is(self):
        T4 = mock_class('T', ['*a'], {'b': 1, '*c': False})

        t = T4(False)
        self.assertFalse(t.is_a())
        self.assertEqual(1, t.get_b())
        self.assertFalse(t.is_c())

        t = T4(True)
        self.assertTrue(t.is_a())
        self.assertEqual(1, t.get_b())
        self.assertFalse(t.is_c())

        t = T4(True, c=True)
        self.assertTrue(t.is_a())
        self.assertEqual(1, t.get_b())
        self.assertTrue(t.is_c())


MockTS = mock_class('MockTS', ['year', 'month', 'day', 'hour', 'minute'],
                    { 'timezone' : None, '*null_time' : False })


class TestCalTime(unittest.TestCase):

    def test_1993(self):
        t = CalTime.from_evolution(MockTS(1993, 10, 27, 14, 11))
        self.assertEqual('1993-10-27 Wed', t.date_str())
        self.assertEqual('14:11', t.time_str())
        self.assertEqual('Wed', t.weekday_str())

    def test_2022(self):
        t = CalTime.from_evolution(MockTS(2022, 7, 29, 3, 59))
        self.assertEqual('2022-07-29 Fri', t.date_str())
        self.assertEqual('03:59', t.time_str())
        self.assertEqual('Fri', t.weekday_str())

    def test_null(self):
        t = CalTime.from_evolution(MockTS(2022, 7, 29, 3, 59, null_time=True))
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
                              'week_start'	   : 0,
                              'until' 		   : None,
                              })

dt = CalTime.from_str

class TestRecurrence(unittest.TestCase):

    def test_secondly(self):
        occ = MockRecurrence(I_SECOND, 1, 0)
        rec = Recurrence.from_evolution(occ)
        self.assertIs(type(rec), str) # "Unsupported" message

    def test_minutely(self):
        occ = MockRecurrence(I_MINUTE, 1, 0)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_hourly(self):
        occ = MockRecurrence(I_HOUR, 1, 0)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_daily_unbounded(self):
        occ = MockRecurrence(I_DAY, 1, 0)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_daily_five_times(self):
        occ = MockRecurrence(I_DAY, 1, 5)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_daily_until(self):
        occ = MockRecurrence(I_DAY, 1, 0, until=MockTS(2022, 6, 7, 12, 0))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_wednesday_until(self):
        occ = MockRecurrence(I_WEEK, 1, 0, by_day_array=[4] + ([32639] * 385), until=MockTS(2022, 6, 7, 12, 0))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_second_day(self):
        occ = MockRecurrence(I_DAY, 2, 0)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_mon_wed_thu(self):
        occ = MockRecurrence(I_WEEK, 1, 0, by_day_array=[2, 4, 5] + ([32639] * 383))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_mon_wed_thu_with_start_on_tuesday(self):
        occ = MockRecurrence(I_WEEK, 1, 0, by_day_array=[2, 4, 5] + ([32639] * 383))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_weekly(self):
        occ = MockRecurrence(I_WEEK, 1, 0)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_third_weekly(self):
        occ = MockRecurrence(I_WEEK, 1, 3)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_fourth_wendesday_per_month(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[36] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_tuesday_every_two_weeks(self):
        occ = MockRecurrence(I_WEEK, 2, 13, by_day_array=[3] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_first_sunday_per_month(self):
        occ = MockRecurrence(I_MONTH, 1, 77, by_day_array=[9] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_second_sunday_per_month_outlook(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[17] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_second_saturday_per_month_outlook(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_day_array=[23] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_second_day_per_two_months(self):
        occ = MockRecurrence(I_MONTH, 2, 0, by_month_day_array=[2] + ([32639] * 31))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_last_sunday_per_month(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[-1] + ([32639] * 385), by_day_array=[1] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_last_monday_per_month(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[-1] + ([32639] * 385), by_day_array=[2] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_25th_of_january(self):
        occ = MockRecurrence(I_YEAR, 1, 3, by_month_day_array=[25] + ([32639] * 31))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_12th_day_per_month_outlook(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_month_day_array=[12] + ([32639] * 31), until=MockTS(2023, 3, 11, 17, 0))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_28th_of_february(self):
        occ = MockRecurrence(I_YEAR, 1, 0, by_month_day_array=[28] + ([32639] * 31))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_1st_monday_in_march(self):
        MockRecurrence(I_YEAR, 1, 0, by_day_array=[10] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_20th_of_july(self):
        occ = MockRecurrence(I_YEAR, 1, 0)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_third_monday_outlook(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[3] + ([32639] * 385), by_day_array=[2] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_every_third_sunday_outlook(self):
        occ = MockRecurrence(I_MONTH, 1, 0, by_set_pos_array=[3] + ([32639] * 385), by_day_array=[1] + ([32639] * 385))
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_weekstart_monday(self):
        # DTSTART:19970805T090000
        # RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=MO
        # ==> (1997 EDT)Aug 5,10,19,24
        start = CalTime.from_evolution(MockTS(1997, 8, 5, 10, 00))
        occ = MockRecurrence(I_WEEK, 2, 4, by_day_array=[3, 1] + ([32639] * 384), week_start=I_CAL_MONDAY_WEEKDAY)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_weekstart_sunday(self):
        # DTSTART:19970805T090000
        # RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=SU
        # ==> (1997 EDT)August 5,17,19,31
        start = CalTime.from_evolution(MockTS(1997, 8, 5, 10, 00))
        occ = MockRecurrence(I_WEEK, 2, 4, by_day_array=[1, 3] + ([32639] * 384), week_start=I_CAL_SUNDAY_WEEKDAY)
        rec = Recurrence.from_evolution(occ)
        raise Exception('FIXME')

    def test_until_exact(self):
        '''"until" matches one of the recurrences'''
        raise Exception('FIXME')

    def test_cross_dst_boundary(self):
        '''DST messing things up again'''
        raise Exception('FIXME')

if __name__ == '__main__':
    unittest.main()

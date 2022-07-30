from enum import Enum
import datetime

class Recur(Enum):
    SECOND = 'second'
    MINUTE = 'minute'
    HOUR   = 'hour'
    DAY    = 'day'
    WEEK   = 'week'
    MONTH  = 'month'
    YEAR   = 'year'

EVENT_RECURRENCE_MAPPING = {
    'I_CAL_NO_RECURRENCE'        : None,
    'I_CAL_SECONDLY_RECURRENCE'  : Recur.SECOND,
    'I_CAL_MINUTELY_RECURRENCE'  : Recur.MINUTE,
    'I_CAL_HOURLY_RECURRENCE'    : Recur.HOUR,
    'I_CAL_DAILY_RECURRENCE'     : Recur.DAY,
    'I_CAL_WEEKLY_RECURRENCE'    : Recur.WEEK,
    'I_CAL_MONTHLY_RECURRENCE'   : Recur.MONTH,
    'I_CAL_YEARLY_RECURRENCE'    : Recur.YEAR,
}

# Config
RECURRENCE_ENCODING = {
    Recur.SECOND	: None, # unsuported
    Recur.MINUTE	: 'm',  # FIXME: this only works for my personal config
    Recur.HOUR		: 'h',
    Recur.DAY		: 'd',
    Recur.WEEK		: 'w',
    Recur.MONTH		: 'M',  # FIXME: this only works for my personal config
    Recur.YEAR		: 'Y',  # FIXME: this only works for my personal config
}

class CalTime(datetime.datetime):
    WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    def __init__(self, year_or_datetime, month=None, day=None, hour=None, minute=None):
        if type(year_or_datetime) is datetime.datetime:
            dt = year_or_datetime
            assert(month == Null)
            assert(day == Null)
            assert(hour == Null)
            assert(minute == Null)
            datetime.datetime.__init__(self, dt.year, dt.month, dt.day, dt.hour, dt.minute)
        else:
            year = year_or_datetime
            datetime.datetime.__init__(self, year, month, day, hour, minute)

    def weekday_str(self):
        return CalTime.WEEKDAYS[self.weekday()]

    def date_str(self):
        return self.datetime.strftime('%Y-%m-%d') + ' ' + self.weekday_str()

    def time_str(self):
        return self.datetime.strftime('%H:%M')

    def as_mock(self):
        return f'MockTS({self.datetime.year}, {self.datetime.month}, {self.datetime.day}, {self.datetime.hour}, {self.datetime.minute})'

    def timespec(self, repetition=None):
        if repetition is None:
            repstr = ''
        else:
            repstr = f' {repetition.org_agenda_spec}'
        return f'<{self.date_str()} {self.time_str()}{repstr}>'

    def __add__(self, timedelta):
        return CalTime(self.datetime + timedelta)

    @staticmethod
    def from_str(s):
        splits = s.split('T')
        if len(splits) > 0 and len(splits[0]) == 10:
            date = splits[0]

            year = int(date[0:4], 10)
            month = int(date[5:7], 10)
            day = int(date[8:10], 10)
            hour = 0
            second = 0

            ill_formed = False

            if len(splits) == 2 and len(splits[1]) == 5:
                time = splits[1]
                hour = int(time[0:2], 10)
                minute = int(time[3:5], 10)
            elif len(splits) != 1:
                ill_formed = True

            if not ill_formed:
                return CalTime(year, month, day, hour, second)
        raise Exception(f'Ill-formed CalTime({s})')

    @staticmethod
    def from_evolution(t):
        if t is None or t.is_null_time():
            return None
        # This seems to always hold for me; not sure if it is universal?
        assert t.get_timezone() is None or t.get_timezone().get_utc_offset()[0] == 0
        return CalTime(datetime.datetime(year=t.get_year(),
                                         month=t.get_month(),
                                         day=t.get_day(),
                                         hour=t.get_hour(),
                                         minute=t.get_minute()))


class WeekdayShift:
    def __init__(self, to_weekday):
        self.to_weekday = to_weekday - 2
        if self.to_weekday == -1:
            self.to_weekday = 6 # Sunday
        if self.to_weekday < 0 or self.to_weekday > 6:
            raise Exception(f'Bad weekday shift: {to_weekday}')

    def shift(self, caltime : CalTime) -> tuple[CalTime, datetime.timedelta]:
        one_day = datetime.timedelta(days=1)
        delta =  datetime.timedelta(days=0)
        result = caltime
        while result.datetime.weekday() != self.to_weekday:
            delta += one_day
            result = caltime + delta
        return (caltime, delta)


class RecurrenceRange:
    def __init__(self, recurrence, first_date):
        self.first_date = first_date
        self.recurrence = recurrence

    @property
    def start_date(self):
        return self.first_date

    def all(self):
        '''Returns an iterator over all CalTimes'''
        return self.from(self.start_date)

    def from(self, start : CalTime):
        '''Returns an iterator over all CalTimes at or after 'start' '''
        pass

    def is_unlimited(self):
        pass


class Recurrence:
    def __init__(self, spec, adjustment):
        self.spec = spec
        self.adjustment = adjustment

    def adjust_time(self, caltime : CalTime):
        if self.adjustment is None:
            return (caltime, datetime.timedelta(days=0))
        return self.adjustment.shift(caltime)

    def org_agenda_spec(self):
        '''Returns None if there is no matching org agenda spec'''
        return self.spec

    def range_from(self, starttime : CalTime) -> RecurrenceRange:
        '''Constructs a RecurrenceRange that can retrieve all individual instances, given a start time/date'''
        return RecurrenceRange(self, starttime)

    @staticmethod
    def evolution_rec_as_mock(rec):
        # for generating mock objects
        if rec is None:
            return

        GET_METHODS = ['interval', 'count']
        def e(n):
            return f'[32639] * {n}'
        GET_ARRAY_METHODS = [('set_pos', e(386)), ('year_day', e(386)),
                             ('month_day', e(32)), ('week_no', e(56)),
                             ('day', e(386)), ('hour', e(25)),
                             ('minute', e(61)), ('second', e(62))]

        posargs = [repr(getattr(rec, f'get_{method}')()) for method in GET_METHODS]

        kwargs = []
        for (method, dflt) in GET_ARRAY_METHODS:
            v = getattr(rec, f'get_by_{method}_array')()
            if type(v) is list:
                tail_elt = v[-1]
                tail_pos = len(v) - 1
                while tail_pos > -1 and v[tail_pos] == tail_elt:
                    tail_pos -= 1
                vt = f'[{tail_elt}] * {len(v) - tail_pos - 1}'
                if tail_pos >= 0:
                    v = f'{v[:tail_pos + 1]} + ({vt})'
                else:
                    v = vt
            else:
                v = f'{v}'
            if v != dflt:
                kwargs.append((f'by_{method}_array', v))

        until = CalTime.from_evolution(rec.get_until())
        if until is not None:
            kwargs.append(('until', until.as_mock()))
        if rec.get_week_start() != 0:
            kwargs.append(('week_start', str(rec.get_week_start().value_name)))

        posargs += [f'{n}={v}' for n, v in kwargs]
        posargs = ', '.join(posargs)

        freq = rec.get_freq().value_name

        return f'MockRecurrence("{freq}", {posargs})'

    @staticmethod
    def from_evolution(rec):
        rec_unit = None if rec.get_freq() is None else EVENT_RECURRENCE_MAPPING[rec.get_freq().value_name]
        if rec_unit is None:
            return None

        rec_factor = rec.get_interval()
        rec.get_until()

        by_seconds =   [n for n in rec.get_by_second_array() if n < 60]
        by_minutes =   [n for n in rec.get_by_minute_array() if n < 60]
        by_hours =     [n for n in rec.get_by_hour_array() if n < 24]
        by_weekdays =  [n for n in rec.get_by_day_array() if n < 50] # including nth-week encoding
        by_week_no =   [n for n in rec.get_by_week_no_array() if n < 54]
        by_month_day = [n for n in rec.get_by_month_day_array() if n < 32]
        by_year_day =  [n for n in rec.get_by_year_day_array() if n < 366]
        by_set_pos =   [n for n in rec.get_by_set_pos_array() if n < 100] # No idea what this is

        nonempty_periods = [b for b in [('seconds', by_seconds),
                                        ('minutes', by_minutes),
                                        ('hours', by_hours),
                                        ('weekdays', by_weekdays),
                                        ('week_no', by_week_no),
                                        ('month-day', by_month_day),
                                        ('year-day', by_year_day),
                                        ('pos', by_set_pos)] if len(b[1]) > 0]

        processed_periods = []

        adjustments = [None]
        spec = None

        if rec_unit == Recur.SECOND:
            return 'WARNING: Cannot use second-based repetition.'
        elif rec_unit == Recur.MINUTE:
            return 'WARNING: minute-based repetition not implemented yet.'
        elif rec_unit == Recur.HOUR:
            return 'WARNING: hour-based repetition not implemented yet.'
        elif rec_unit == Recur.DAY:
            pass
        elif rec_unit == Recur.WEEK:
            # rec_factor = rec.get_by_week_no(0)
            #return 'WARNING: week-based repetition not implemented yet.'
            if by_weekdays:
                adjustments = [WeekdayShift(n) for n in by_weekdays]
            processed_periods=[by_weekdays]
        elif rec_unit == Recur.MONTH:
            # monthday = rec.get_by_month_day(0)
            # if monthday < 32:
            #     pass
            # rec_factor = rec.get_by_month(0)
            #return 'WARNING: month-based repetition not implemented yet.'
            pass
        elif rec_unit == Recur.YEAR:
            pass
        else:
            raise Exception('Impossible')

        unit_enc = RECURRENCE_ENCODING[rec_unit]
        spec = f'+{rec_factor}{unit_enc}'

        overlooked_periods = []
        for (nep_str, nep) in nonempty_periods:
            found = False
            for p in processed_periods:
                if p is nep:
                    found = True
                    break
            if not found:
                overlooked_periods.append(nep_str + ' (' + ','.join(str(i) for i in nep) + ')')

        if overlooked_periods:
            return f'WARNING: Event repetition in {rec_unit} not completely handled due to ' + '; '.join(overlooked_periods)

        if not spec:
            return 'WARNING: could not figure out recurrence strategy'

        return [Recurrence(spec, a) for a in adjustments]


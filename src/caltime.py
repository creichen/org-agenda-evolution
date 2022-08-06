from __future__ import annotations

from enum import Enum
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from tzresolve import TZResolver
import sys

def perr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

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

# For determining week start
I_CAL_SUNDAY_WEEKDAY = 'I_CAL_SUNDAY_WEEKDAY'
I_CAL_MONDAY_WEEKDAY = 'I_CAL_MONDAY_WEEKDAY'

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

class CalTimeIncrement:
    '''Special date increments'''
    def __add__(self, caltime):
        raise Exception('NIY')


class MonthIncrement(CalTimeIncrement):
    def __init__(self, count=1):
        super().__init__()
        self.months = count
        assert(count >= 0)

    def __str__(self):
        return f'{{months+={self.months}}}'

    def __add__(self, caltime):
        # FIXME: optimise for larger counts
        c = self.months
        if c == 0:
            return caltime

        desired_day = caltime.day
        c -= 1
        caltime += timedelta(days = 1 + caltime.number_of_days_in_month() - caltime.day)

        while c > 0:
            c -= 1
            caltime += timedelta(days = caltime.number_of_days_in_month())

        desired_day = min(desired_day, caltime.number_of_days_in_month())
        return caltime + timedelta(days = desired_day - caltime.day)


class YearIncrement(MonthIncrement):
    def __init__(self, count=1):
        # FIXME: optimise me
        super().__init__(count=0)
        self.months = count*12

    def __str__(self):
        return f'{{years+={self.months//12}}}'


# Since ical supports week starts both for Sundays and Mondays, we have to
# introduce some extra complexity:
WEEKSTART_SUN = I_CAL_SUNDAY_WEEKDAY
WEEKSTART_MON = I_CAL_MONDAY_WEEKDAY

class CalTime(datetime):
    # We default to the standard datetime mapping (WEEKSTART_MON):
    WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    def __new__(cls, year, month=None, day=None, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        if type(year) is datetime:
            dt = year
            assert(month == None)
            assert(day == None)
            assert(hour == None)
            assert(minute == None)
            assert(second == None)
            assert(microsecond == None)
            return super().__new__(cls, dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)
        else:
            return super().__new__(cls, year, month, day, hour, minute, second, microsecond, tzinfo)

    def weekday_str(self):
        return CalTime.WEEKDAYS[self.weekday(WEEKSTART_MON)]

    def date_str(self):
        return self.strftime('%Y-%m-%d') + ' ' + self.weekday_str()

    def astimezone(self, timezone):
        return super().astimezone(timezone)

    @staticmethod
    def today(tzinfo):
        now = datetime.now()
        return CalTime(year = now.year, month = now.month, day = now.day, tzinfo=tzinfo).astimezone(tzinfo)

    @staticmethod
    def sunday(weekstart=WEEKSTART_MON):
        if weekstart is WEEKSTART_SUN:
            return -1
        return 6

    def weekday(str, weekstart):
        wd = super().weekday()
        if weekstart is WEEKSTART_SUN and wd == CalTime.sunday(weekstart=WEEKSTART_MON):
            return CalTime.sunday(weekstart=WEEKSTART_SUN)
        return wd

    def time_str(self):
        return self.strftime('%H:%M')

    def as_mock(self):
        if self.tzinfo is None:
            tzinfo = 'None'
        else:
            tzinfo = '"{self.tzinfo}"'
        return f'MockTS({self.year}, {self.month}, {self.day}, {self.hour}, {self.minute}, tzinfo={tzinfo})'

    def number_of_days_in_month(self):
        year = self.year
        dm = self.month + 1
        if dm == 13:
            dm = 1
            year += 1
        return (CalTime(year, dm, 1) - timedelta(days = 1)).day

    def timespec(self, repetition=None):
        if repetition is None:
            repstr = ''
        else:
            repstr = f' {repetition.org_agenda_spec}'
        return f'<{self.date_str()} {self.time_str()}{repstr}>'

    def __repr__(self):
        return self.date_str().replace(' ', ':') + ':' + self.time_str() + ('' if self.tzinfo is None else f'/{self.tzinfo}')

    @staticmethod
    def from_str(s, tzinfo=None):
        splits = s.split('T')
        if len(splits) > 0 and len(splits[0]) == 10:
            date = splits[0]

            year = int(date[0:4], 10)
            month = int(date[5:7], 10)
            day = int(date[8:10], 10)
            hour = 0
            minute = 0

            ill_formed = False

            if len(splits) == 2 and len(splits[1]) == 5:
                time = splits[1]
                hour = int(time[0:2], 10)
                minute = int(time[3:5], 10)
            elif len(splits) != 1:
                ill_formed = True

            if not ill_formed:
                return CalTime(year, month, day, hour, minute, tzinfo=tzinfo)
        raise Exception(f'Ill-formed CalTime({s})')

    # @staticmethod
    # def from_evolution_cdt(t, tzresolver=None):
    #     if t is None:
    #         return None

    #     timezone = None
    #     if t.get_tzid() is not None:
    #         timezone = tzresolver[t.get_tzid()]

    #     return CalTime.from_evolution(t.get_value(), timezone=timezone, tzresolver=tzresolver)

    # @staticmethod
    # def from_evolution(t, timezone=None, tzresolver=None):
    #     if t is None or t.is_null_time():
    #         return None

    #     # This seems to always hold for me; not sure if it is universal?
    #     assert t.get_timezone() is None or t.get_timezone().get_utc_offset()[0] == 0
    #     return CalTime(year=t.get_year(),
    #                    month=t.get_month(),
    #                    day=t.get_day(),
    #                    hour=t.get_hour(),
    #                    minute=t.get_minute(),
    #                    tzinfo=timezone)


class Subiterator:
    '''
    Iterate within the outer date loop (e.g., for "every Wednesday and Thursday", the outer loop will increment
    by one week, and the inner loop will yield Wednesdays and Thursday (via all_from)
    '''

    def __init__(self, weekstart):
        self.weekstart = weekstart

    def base_date(self, date):
        '''For a given start, compute the date that the outer iterator should increment'''
        raise Exception('NIY')

    def all_from(self, date):
        '''For date as a base_date or increment thereof (via the outer iterator), yield all inner dates'''
        raise Exception('NIY')

    def sunday(self):
        return CalTime.sunday(self.weekstart)

    def weekday(self, d):
        return self.sunday() if d == 1 else d - 2


class WeekdaySubiterator(Subiterator):
    '''Given a week, find the given weekdays'''

    def __init__(self, weekdays, weekstart):
        '''Weekdays expected in ECal format, i.e., 1=Sun, 2=Mon'''
        super().__init__(weekstart)
        weekdays = sorted(self.weekday(d) for d in weekdays)
        self.first = weekdays[0]
        self.day_increments = [(d - self.first) for d in weekdays]
        DEBUGPRINT(f'weekdays = {weekdays}  incrs = {self.day_increments}  first={self.first}  ws={self.weekstart}')

    def base_date(self, date):
        return date - timedelta(days = date.weekday(self.weekstart))

    def all_from(self, date):
        start = date
        start = start + timedelta(days = self.first - start.weekday(self.weekstart))
        DEBUGPRINT(f'start = {start}')
        for days_after_first in self.day_increments:
            yield start + timedelta(days = days_after_first)

    def __str__(self):
        return f'Weekdays<sun={self.sunday()}>[from={self.first}+{self.day_increments}]'


class MonthDaySubiterator(Subiterator):
    '''Specific day per month'''
    def __init__(self, days, weekstart):
        super().__init__(weekstart)
        self.days = sorted(days)

    def base_date(self, date):
        return date - timedelta(days = date.day - 1)

    def all_from(self, date):
        start = date

        DEBUGPRINT(f'start = {start}')
        last_monthday = date.number_of_days_in_month()
        for d in self.days:
            if d >= start.day and d <= last_monthday:
                yield start + timedelta(days = d - start.day)

    def __str__(self):
        return f'MonthDays<sun={self.sunday()}>{self.days}'


class MonthAndWeekdaySubiterator(MonthDaySubiterator):
    '''Given a month, find the nth occurrence of specific weekdays (including the last ones)'''

    def __init__(self, weeks_and_days, weekstart):
        '''
        weeks_and_days = [(week, day), ...]
        week=-1: last week
        week=1 : first week (etc.)
        Weekdays expected in ECal format, i.e., 1=Sun, 2=Mon
        '''
        super().__init__([], weekstart=weekstart)
        self.neg_weekdays = []
        self.pos_weekdays = []

        for w, d in weeks_and_days:
            d = self.weekday(d)
            if w < 0:
                w = -w
                while len(self.neg_weekdays) <= w:
                    self.neg_weekdays.append([])
                self.neg_weekdays[w].append(d)
            else:
                while len(self.pos_weekdays) <= w:
                    self.pos_weekdays.append([])
                self.pos_weekdays[w].append(d)

        for i in range(0, len(self.neg_weekdays)):
            self.neg_weekdays[i] = sorted(self.neg_weekdays[i])

        for i in range(0, len(self.pos_weekdays)):
            self.pos_weekdays[i] = sorted(self.pos_weekdays[i])

        DEBUGPRINT(f'pos: {self.pos_weekdays}')
        DEBUGPRINT(f'neg: {self.neg_weekdays}')

        # neg_weekdays[1] is now the ordered list of weekdays in the last week
        # pos_weekdays[n] is now the ordered list of weekdays in the nth week

    def all_from(self, date):
        start = date

        first_weekday = start.weekday(self.weekstart)
        last_monthday = date.number_of_days_in_month()

        # positive week numbers
        pos_day_offsets = []
        week_offset = 0

        for week in self.pos_weekdays[1:]:
            for day in week:
                day -= first_weekday
                if day < 0:
                    day += 7
                pos_day_offsets.append(day + week_offset)
            week_offset += 7

        # negative week numbers
        neg_day_offsets = []
        week_offset = last_monthday - 6 # first day of the last 7 days
        final_week_first_weekday = (start + timedelta(days = (week_offset - 1))).weekday(self.weekstart)

        for week in self.neg_weekdays[1:]:
            for day in week:
                DEBUGPRINT(f'  woff={week_offset}, day={day} - {final_week_first_weekday}')
                day -= final_week_first_weekday
                if day < 0:
                    day += 7
                neg_day_offsets.append(day + week_offset - start.day)
            week_offset -= 7

        # combine negative and positive
        day_offsets = pos_day_offsets
        if neg_day_offsets:
            day_offsets = neg_day_offsets
            if pos_day_offsets:
                day_offsets = sorted(list(set(pos_day_offsets + neg_day_offset)))

        DEBUGPRINT(f'offsets from {start},wday={first_weekday}/{final_week_first_weekday}: {day_offsets}')

        for offset in day_offsets:
            day = start.day + offset
            if day > 0 and day <= last_monthday:
                yield start + timedelta(days = offset)

    def __str__(self):
        return f'MonthWeekDays<sun={self.sunday()}>(+{self.pos_weekdays}, -{self.neg_weekdays})'

DEBUGPRINT_NONE=lambda _:()
DEBUGPRINT=DEBUGPRINT_NONE

class RecurrenceRange:
    def __init__(self, first_date : CalTime,
                 increment : timedelta, subiterator,
                 count : int, until : CalTime):
        self.first_date = first_date
        self.increment = increment
        self.subiterator = subiterator
        self.count = None if count == 0 else count
        self.until = None if until is None else until.astimezone(self.tzinfo)

    @property
    def tzinfo(self):
        return self.first_date.tzinfo

    @property
    def start_date(self):
        return self.first_date

    def all(self):
        '''Returns an iterator over all CalTimes'''
        return self._starting(self.start_date)

    def before_end(self, caltime):
        '''"until" is inclusive, so it is technically before-or-equal the end'''
        caltime = caltime.astimezone(self.tzinfo)
        return self.until is None or caltime.astimezone(self.tzinfo) <= self.until

    def starting(self, start : CalTime):
        '''Returns an iterator over all CalTimes at or after 'start' '''
        start = start.astimezone(self.tzinfo)

        # must skip to first valid date
        it = self._starting(self.start_date)
        # Performance improvements possible here!

        for v in it:
            if v >= start:
                yield v
                for v in it:
                    yield v
                return
        return


    def _starting(self, start : CalTime):
        '''Returns an iterator over all CalTimes explicitly starting at 'start' '''
        start = start.astimezone(self.tzinfo)

        count = self.count
        pos = start

        pr = DEBUGPRINT

        pr(f"[it, c:{count}, until:{self.until}] -- START -- at {start}")

        # Phase 1: Start date
        if self.before_end(pos) and count != 0:
            if count is not None:
                count -= 1
            pr(f"[it, c:{count}, until:{self.until}] Phase 1 ==> {pos}")
            yield pos


        # Phase 2: subiterator (if any) bounded by start date
        if self.subiterator:
            pos = self.subiterator.base_date(pos)
            pr(f"[it, c:{count}, until:{self.until}] Phase 2 : {pos} <- base_date()")
            for date in self.subiterator.all_from(pos):
                if date > start:
                    if count == 0 or not self.before_end(date):
                        pr(f"[it, c:{count}, until:{self.until}] Phase 2 : done early")
                        return # done
                    if count is not None:
                        count -= 1
                    pr(f"[it, c:{count}, until:{self.until}] Phase 2 ==> {date}")
                    yield date
                else:
                    pr(f"[it, c:{count}, until:{self.until}] Phase 2 skipping {date} (<= {start})")

        pos = self.increment + pos
        pr(f"[it, c:{count}, until:{self.until}] Phase 3: {pos}")

        # Phase 3: free iteration
        while self.before_end(pos) and count != 0:
            if not self.subiterator:
                pr(f"[it, c:{count}, until:{self.until}] Phase 3 ==> {pos}")
                yield pos
                if count is not None:
                    count -= 1
            else:
                for date in self.subiterator.all_from(pos):
                    if date > start:
                        if count == 0 or not self.before_end(date):
                            pr(f"[it, c:{count}, until:{self.until}] Phase 3 : done early")
                            return # done
                        if count is not None:
                            count -= 1
                        pr(f"[it, c:{count}, until:{self.until}] Phase 3 ==> {date}")
                        yield date
                    else:
                        pr(f"[it, c:{count}, until:{self.until}] Phase 3 skipping {date} (<= {start})")

            pos = self.increment + pos

    def is_finite(self):
        return self.count or self.until


class Recurrence:
    '''
    Captures a recurrence rule.  'range_from' can then construct an iterator over events in that range.
    '''

    def __init__(self, spec, increment, subiterator, until, count):
        self.spec = spec
        self.increment = increment
        self.subiterator = subiterator
        self.until = until
        self.count = count

    def adjust_time(self, caltime : CalTime):
        if self.adjustment is None:
            return (caltime, timedelta(days=0))
        return self.adjustment.shift(caltime)

    def org_agenda_spec(self):
        '''Returns None if there is no matching org agenda spec'''
        return self.spec

    def range_from(self, starttime : CalTime) -> RecurrenceRange:
        '''Constructs a RecurrenceRange that can retrieve all individual instances, given a start time/date'''
        return RecurrenceRange(starttime, self.increment, self.subiterator, count=self.count, until=self.until)

    def __str__(self):
        fields = [('spec', self.spec),
                  ('inc', self.increment),
                  ('subit', self.subiterator),
                  ('until', None if self.until is None else repr(self.until)),
                  ('count', None if self.count == 0 else self.count)]
        return '{' + ', '.join(f'{n}={v}' for (n,v) in fields if v is not None) + '}'

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


class CalConverter:
    def __init__(self, tzresolver : TZresolver):
        self._tzresolver = tzresolver

    def timezone(self, tz : string):
        return self._tzresolver[tz]

    def time_from_str(self, spec : str):
        timezone = None

        tzsplit = spec.split('/', 1)
        if len(tzsplit) == 2:
            spec, tzid = tuple(tzsplit)
            timezone = self.timezone(tzid)

        return CalTime.from_str(spec, tzinfo=timezone)

    def time_from_evolution(self, t):
        '''Convert Evolution recurrence objects to caltime.Recurrence'''

        if t is None or t.is_null_time():
            return None

        timezone = self.timezone(t.get_tzid())

        # This seems to always hold for me; not sure if it is universal?
        assert t.get_timezone() is None or t.get_timezone().get_utc_offset()[0] == 0
        return CalTime(year=t.get_year(),
                       month=t.get_month(),
                       day=t.get_day(),
                       hour=t.get_hour(),
                       minute=t.get_minute(),
                       tzinfo=timezone)

    def daily_recurrence(self, count=None):
        return Recurrence(None, timedelta(days = 1), None, until = None, count = 0 if count is None else count)

    def recurrence_from_evolution(self, rec) -> Recurrence:
        '''Convert Evolution recurrence objects to caltime.Recurrence'''

        rec_unit = None if rec.get_freq() is None else EVENT_RECURRENCE_MAPPING[rec.get_freq().value_name]
        if rec_unit is None:
            return None

        rec_factor = rec.get_interval()

        by_seconds =   [n for n in rec.get_by_second_array() if n < 60]
        by_minutes =   [n for n in rec.get_by_minute_array() if n < 60]
        by_hours =     [n for n in rec.get_by_hour_array() if n < 24]
        by_weekdays =  [n for n in rec.get_by_day_array() if n < 50] # including nth-week encoding
        by_week_no =   [n for n in rec.get_by_week_no_array() if n < 54]
        by_month_day = [n for n in rec.get_by_month_day_array() if n < 32]
        by_year_day =  [n for n in rec.get_by_year_day_array() if n < 368]
        by_set_pos =   [n for n in rec.get_by_set_pos_array() if n < 368] # No clear idea what this is

        nonempty_periods = [b for b in [('seconds', by_seconds),
                                        ('minutes', by_minutes),
                                        ('hours', by_hours),
                                        ('weekdays', by_weekdays),
                                        ('week_no', by_week_no),
                                        ('month-day', by_month_day),
                                        ('year-day', by_year_day),
                                        ('pos', by_set_pos)] if len(b[1]) > 0]

        processed_periods = []
        weekstart = rec.get_week_start().value_name
        assert(weekstart in [I_CAL_MONDAY_WEEKDAY, I_CAL_SUNDAY_WEEKDAY])

        spec = None
        increment = None    # delta for 'outer loop' (for simple specs the only loop) in iterating over all dates
        subiterator = None  # 'inner loop' spec (e.g., iterating over certain weekdays)

        if rec_unit == Recur.SECOND:
            return 'WARNING: Cannot use second-based repetition.'
        elif rec_unit == Recur.MINUTE:
            increment = timedelta(minutes = rec_factor)
        elif rec_unit == Recur.HOUR:
            increment = timedelta(hours = rec_factor)
        elif rec_unit == Recur.DAY:
            increment = timedelta(days = rec_factor)
        elif rec_unit == Recur.WEEK:
            if by_weekdays:
                subiterator = WeekdaySubiterator(by_weekdays, weekstart=weekstart)

            increment = timedelta(weeks = rec_factor)
            processed_periods=[by_weekdays]
        elif rec_unit in [Recur.MONTH, Recur.YEAR]: # Very similar recurrence handling
            if by_weekdays and by_set_pos and len(by_weekdays) == len(by_set_pos):
                subiterator = MonthAndWeekdaySubiterator([
                    (by_set_pos[i], d)  for (i, d) in enumerate(by_weekdays)],
                                                         weekstart=weekstart)
                processed_periods=[by_set_pos, by_weekdays]
            elif by_weekdays:
                def decode(encoded_weekday):
                    if encoded_weekday < 0:
                        week = -1 # last week
                        weekday = (-encoded_weekday) - 8
                    else:
                        week = encoded_weekday >> 3
                        weekday = encoded_weekday & 0x7
                    return (week, weekday)

                subiterator = MonthAndWeekdaySubiterator([decode(wd) for wd in by_weekdays],
                                                         weekstart=weekstart)
                processed_periods=[by_weekdays]
            elif by_month_day:
                subiterator = MonthDaySubiterator(by_month_day, weekstart=weekstart)
                processed_periods=[by_month_day]

            if rec_unit == Recur.MONTH:
                increment = MonthIncrement(rec_factor)
            elif rec_unit == Recur.YEAR:
                increment = YearIncrement(rec_factor)
            else:
                raise Exception('Impossible')
        else:
            raise Exception('Impossible')

        if subiterator is None and rec.get_until() is None and rec.get_count() == 0: # Not complicated?
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
            #print(f'WARNING: Event repetition in {rec_unit} not completely handled due to ' + '; '.join(overlooked_periods))
            return f'WARNING: Event repetition in {rec_unit} not completely handled due to ' + '; '.join(overlooked_periods)

        return Recurrence(spec, increment, subiterator, until=self.time_from_evolution(rec.get_until()), count=rec.get_count())

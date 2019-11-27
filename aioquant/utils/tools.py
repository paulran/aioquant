# -*- coding:utf-8 -*-

"""
Tools Bag.

Author: HuangTao
Date:   2018/04/28
Email:  huangtao@ifclover.com
"""

import uuid
import time
import decimal
import datetime


def get_cur_timestamp():
    """Get current timestamp(second)."""
    ts = int(time.time())
    return ts


def get_cur_timestamp_ms():
    """Get current timestamp(millisecond)."""
    ts = int(time.time() * 1000)
    return ts


def get_datetime_str(fmt="%Y-%m-%d %H:%M:%S"):
    """Get date time string, year + month + day + hour + minute + second.

    Args:
        fmt: Date format, default is `%Y-%m-%d %H:%M:%S`.

    Returns:
        str_dt: Date time string.
    """
    today = datetime.datetime.today()
    str_dt = today.strftime(fmt)
    return str_dt


def get_date_str(fmt="%Y%m%d", delta_days=0):
    """Get date string, year + month + day.

    Args:
        fmt: Date format, default is `%Y%m%d`.
        delta_days: Delta days for currently, default is 0.

    Returns:
        str_d: Date string.
    """
    day = datetime.datetime.today()
    if delta_days:
        day += datetime.timedelta(days=delta_days)
    str_d = day.strftime(fmt)
    return str_d


def get_utc_time():
    """Get current UTC time."""
    utc_t = datetime.datetime.utcnow()
    return utc_t


def utctime_str_to_ts(utctime_str, fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
    """Convert UTC time string to timestamp(second).

    Args:
        utctime_str: UTC time string, e.g. `2019-03-04T09:14:27.806Z`.
        fmt: UTC time format, e.g. `%Y-%m-%dT%H:%M:%S.%fZ`.

    Returns:
        timestamp: Timestamp(second).
    """
    dt = datetime.datetime.strptime(utctime_str, fmt)
    timestamp = int(dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).timestamp())
    return timestamp


def utctime_str_to_ms(utctime_str, fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
    """Convert UTC time string to timestamp(millisecond).

    Args:
        utctime_str: UTC time string, e.g. `2019-03-04T09:14:27.806Z`.
        fmt: UTC time format, e.g. `%Y-%m-%dT%H:%M:%S.%fZ`.

    Returns:
        timestamp: Timestamp(millisecond).
    """
    dt = datetime.datetime.strptime(utctime_str, fmt)
    timestamp = int(dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).timestamp() * 1000)
    return timestamp


def get_utctime_str(fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
    """Get current UTC time string.

    Args:
        fmt: UTC time format, e.g. `%Y-%m-%dT%H:%M:%S.%fZ`.

    Returns:
        utctime_str: UTC time string, e.g. `2019-03-04T09:14:27.806Z`.
    """
    utctime = get_utc_time()
    utctime_str = utctime.strftime(fmt)
    return utctime_str


def get_uuid1():
    """Generate a UUID based on the host ID and current time

    Returns:
        s: UUID1 string.
    """
    uid1 = uuid.uuid1()
    s = str(uid1)
    return s


def get_uuid3(str_in):
    """Generate a UUID using an MD5 hash of a namespace UUID and a name

    Args:
        str_in: Input string.

    Returns:
        s: UUID3 string.
    """
    uid3 = uuid.uuid3(uuid.NAMESPACE_DNS, str_in)
    s = str(uid3)
    return s


def get_uuid4():
    """Generate a random UUID.

    Returns:
        s: UUID5 string.
    """
    uid4 = uuid.uuid4()
    s = str(uid4)
    return s


def get_uuid5(str_in):
    """Generate a UUID using a SHA-1 hash of a namespace UUID and a name

    Args:
        str_in: Input string.

    Returns:
        s: UUID5 string.
    """
    uid5 = uuid.uuid5(uuid.NAMESPACE_DNS, str_in)
    s = str(uid5)
    return s


def float_to_str(f, p=20):
    """Convert the given float to a string, without resorting to scientific notation.

    Args:
        f: Float params.
        p: Precision length.

    Returns:
        s: String format data.
    """
    if type(f) == str:
        f = float(f)
    ctx = decimal.Context(p)
    d1 = ctx.create_decimal(repr(f))
    s = format(d1, 'f')
    return s


import re
from lxml import etree
from datetime import date, datetime
from pyramid.renderers import NullRendererHelper
from pytz import UTC
from dateutil import parser as dateparser
from dateutil.tz import tzutc
from dateutil.tz import tzlocal

LOCALZONE = tzlocal()


class FileNullRendererHelper(NullRendererHelper):
    def __repr__(self):
        return "Downloadable file"

file_null_renderer = FileNullRendererHelper()


# def postgres_date_to_utc(value):
#    """convert local time to UTC
#
#    (postgres returns local timezone, solr expects utc)
#    """
#    return value

def datetime_to_string(value):
    """Return a ISO 8601 string

    >>> datetime_to_string(date(1500, 1, 2))
    '1500-01-02'
    >>> datetime_to_string(datetime(1500, 1, 2))
    '1500-01-02T00:00:00'
    >>> datetime_to_string(datetime(1500, 1, 2, 16, 5, 4))
    '1500-01-02T16:05:04'

    """
    if not isinstance(value, date):
        return value

    result = value.isoformat()
    return result


def datetime_to_string_zulu(value):
    """Return a ISO 8601 string that solr will digest

    (i.e. with seconds and milliseconds, but not microseconds, in Zulu time

    >>> datetime_to_string_zulu(date(2000, 3, 5))
    '2000-03-05T00:00:00Z'
    >>> datetime_to_string_zulu(datetime(1400, 3, 5))
    '1400-03-05T00:00:00Z'
    >>> d = datetime(2012, 12, 1, 14, 58, 15, 393353, tzinfo=tzutc())
    >>> datetime_to_string_zulu(d)
    '2012-12-01T14:58:15Z'

    """
    if value is None:
        return value
    if not isinstance(value, date):
        raise Exception('This value %s is not a date or datetime instance' % value)

    if not isinstance(value, datetime):
        value = datetime(value.year, value.month, value.day)

    if not value.tzinfo:
        value = value.replace(tzinfo=tzutc())
    value = value.astimezone(UTC)

    value = value.replace(microsecond=0)

    result = value.isoformat()
    # solr doesn't like offset timezones (`+01:00`)
    # so we convert `offset zero` to `Zulu time` (i.e. capital z)
    result = result.replace('+00:00', 'Z')
    return result


class InvalidDateException(Exception):
    pass


def string_to_datetime(value, default=None):
    """parse a string, try to return a date

    default is a date, as described here:
        http://labix.org/python-dateutil

    default must be a datetime.datetime instance (NOT datetime.date)
    """
    # provide a sane default: the first of januari
    if not default:
        default = datetime(2000, 1, 1)
    try:
        result = dateparser.parse(value, default=default)
    except ValueError as error:
        raise ValueError(unicode(error) + ': ' + value)
    #    if hasattr(result, 'tzinfo'):
    #        # We require UTC
    #        result = result.astimezone(UTC)
    result = result.replace(tzinfo=tzutc())
    return result


def now():
    return datetime.utcnow().replace(tzinfo=tzutc())


def is_NMTOKEN(s):
    # cf http://www.w3.org/TR/2000/REC-xml-20001006#NT-Nmtoken
    # this is just a partial implementation (that is: more strict than
    # it should be)
    regexp = u'(\w|\.|\-|\:)+$'
    return bool(re.match(regexp, s, re.UNICODE))


def flatten(el):
    """given an etree.Element, return, recursively, all text and tail contents"""
    result = el.text or ''
    for sub_el in el:
        result += flatten(sub_el)
    result += el.tail or ''
    result = result.strip()
    return result


def content_tostring(el):
    """return etree.tostring without outer tags"""
    s = etree.tostring(el)
    # remove outer tags
    s = s.strip()
    s = s[s.find('>') + 1:-(len('<%s>' % el.tag) + 1)]
    return s


def cleanup_string(string):
    "Remove double whitespaces and such"
    return re.sub('\s+', ' ', string).strip()


def set_cors(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

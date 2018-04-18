# -*- coding: utf-8 -*-

from collections import Iterable
import numpy
from enum import IntEnum
from datetime import datetime
import time
import bson
from math import log10, floor

class EnumWithName(IntEnum):
    def __new__(cls, value, name):
        member = int.__new__(cls, value)
        member._value_ = value
        member._name = name
        return member

    def __int__(self):
        return self._value_

    def __str__(self):
        return self._name

    def __unicode__(self):
        return unicode(self._name.decode('utf-8'))

def object_to_json(o, level=0, indent=4, space=" ", newline="\n"):
    ret = ""
    if isinstance(o, dict):
        ret += "{" + newline
        comma = ""
        for k,v in o.iteritems():
            ret += comma
            comma = ",\n"
            ret += space * indent * level
            ret += '"' + str(k) + '":' + space
            ret += object_to_json(v, level + 1)

        ret += newline + space * indent * (level - 1) + "}"
    elif isinstance(o, basestring):
        ret += '"' + o + '"'
    elif isinstance(o, list):
        ret += "[" + ", ".join([object_to_json(e, level+1) for e in o]) + "]"
    elif isinstance(o, bool):
        ret += "true" if o else "false"
    elif isinstance(o, (int, long)):
        ret += str(o)
    elif isinstance(o, datetime):
        ret += o.strftime('%Y-%m-%d %H:%M:%S.%f')
    elif isinstance(o, bson.ObjectId):
        ret += 'ObjectId(%s)' % o
    elif isinstance(o, float):
        ret += '%.7g' % o
    elif isinstance(o, numpy.ndarray) and numpy.issubdtype(o.dtype, numpy.integer):
        ret += "[" + ','.join(map(str, o.flatten().tolist())) + "]"
    elif isinstance(o, numpy.ndarray) and numpy.issubdtype(o.dtype, numpy.inexact):
        ret += "[" + ','.join(map(lambda x: '%.7g' % x, o.flatten().tolist())) + "]"
    elif isinstance(o, bson.timestamp.Timestamp):
        ret += o.as_datetime().strftime('%Y-%m-%d %H:%M:%S.%f')
    elif o is None:
        ret += 'null'
    else:
        raise TypeError("Unknown type '%s' for json serialization" % str(type(o)))
    return ret

levels = ' KMGTPEZY'

def simplify_num(value):
    if value < 1000:
        return u'{:.2f}'.format(value)

    lads = int(log10(value) / 3)

    if lads >= len(levels):
        simp_text = levels[-1]
    else:
        simp_text = levels[lads]
    
    simp = value / float(10 ** (lads * 3))
    return u'{:.2f} {}'.format(simp, simp_text)

def simplify_string(s, max_length=8):
    """\
    max_length excludes ...\
    Return unicode.
    """
    if isinstance(s, str):
        s = unicode(s, 'utf-8')

    s = s.replace('\n', '\\n')
    if len(s) > (max_length + 3):
        s = s[:max_length] + '...'
        
    return s

def left_alphabet(s):
    return filter(unicode.isalpha, unicode(s))

def string_to_float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None

def to_int(obj):
    """Return None if items cannot convert to int, else return converted object"""
    try:
        if isinstance(obj, (list, tuple)):
            return [int(i) for i in obj]
        else:
            return int(obj)
    except (ValueError, TypeError):
        return None

def to_list(o):
    if not isinstance(o, list):
        o = [o]

    return o

dir_symbol_dict = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

def dir_symbol(deg):
    CIRCLE_DEG = 360.0

    part_alloc_deg = (CIRCLE_DEG / len(dir_symbol_dict))

    return dir_symbol_dict[int(floor(((float(deg) + (part_alloc_deg / 2)) % CIRCLE_DEG) / part_alloc_deg))]

class action_result(object):
    def __init__(self, result, success):
        self._result = result
        self._success = success

    @property
    def result(self):
        return self._result

    @property
    def success(self):
        return self._success
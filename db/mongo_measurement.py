# -*- coding: utf-8 -*-

from __future__ import division

import os
import urllib

from datetime import datetime

import requests

import ext

class data_range(object):
    IN_1MINUTE = 'PT1M', 'PT20M', -1
    IN_12HR = 'PT1H', 'PT12H', 1
    
class measurement_data_wrapper(object):
    """
    Wrapper of MongoDB Atlas api measurement section

    Reference: 
        Official Documentation: https://docs.atlas.mongodb.com/reference/api/process-measurements/
        ISO 8601: https://en.wikipedia.org/wiki/ISO_8601
    """
    BASE_URL = 'https://cloud.mongodb.com/api/atlas/v1.0'
    
    MAX_LOGICAL_SIZE_BYTES = 536870912 # 512 MB

    def __init__(self):
        self._mongo_group_id = os.getenv('MONGO_GROUP_ID', None)
        if self._mongo_group_id is None:
            print 'Specify MONGO_GROUP_ID: group id/project id in mongo atlas to environment variable.'
            sys.exit(1)
        self._mongo_host = os.getenv('MONGO_HOST', None)
        if self._mongo_host is None:
            print 'Specify MONGO_HOST: mongodb host name to environment variable.'
            sys.exit(1)
        self._mongo_port = os.getenv('MONGO_PORT', None)
        if self._mongo_port is None:
            print 'Specify MONGO_PORT: mongodb host port to environment variable.'
            sys.exit(1)
        self._mongo_email = os.getenv('MONGO_EMAIL', None)
        if self._mongo_port is None:
            print 'Specify MONGO_EMAIL: mongo atlas email account to environment variable.'
            sys.exit(1)
        self._mongo_api_key = os.getenv('MONGO_API_KEY', None)
        if self._mongo_api_key is None:
            print 'Specify MONGO_API_KEY: mongo atlas api key to environment variable.'
            sys.exit(1)

        self._http_digest_auth = requests.auth.HTTPDigestAuth(self._mongo_email, self._mongo_api_key)

        self._url = 'https://cloud.mongodb.com/api/atlas/v1.0/groups/{}/processes/{}:{}/measurements'.format(
            self._mongo_group_id, self._mongo_host, self._mongo_port)

    def get_measurement_data(self, range=data_range.IN_1MINUTE):
        """
        Returns:
            measurement_data instance.
        """
        granularity, period, point_index = range

        payload = {'granularity': granularity, 'period': period}
        request_url = '{}?{}'.format(self._url, urllib.urlencode(payload))

        response = requests.get(request_url, auth=self._http_digest_auth)

        data_pass = response.ok and (request_url == response.url)
        data = response.json() if data_pass else response.status_code
        return measurement_data(granularity, period, data_pass, data, point_index)
        
class measurement_data(object):
    def __init__(self, granularity_ISO8601, period_ISO8601, ok, data_or_status_code, point_index):
        self._granularity = granularity_ISO8601
        self._period = period_ISO8601
        self._point_index = point_index

        self._ok = ok

        self._data = None
        self._status_code = None

        if self._ok:
            self._data = measurements(data_or_status_code["measurements"], data_or_status_code["end"])
        else:
            self._status_code = data_or_status_code

    @property
    def granularity(self):
        """In ISO 8601 string."""
        return self._granularity

    @property
    def period(self):
        """In ISO 8601 string."""
        return self._period

    @property
    def ok(self):
        return self._ok

    def to_string(self, point_index=None):
        if point_index is None:
            point_index = self._point_index
        
        if self._ok:
            ret = []
            time = self._data.last_data_timestamp

            ret.append(self._data.get_data(measurements.CONNECTIONS).get_string_spec_data_point(point_index))
            ret.append(self._data.get_data(measurements.LOGICAL_SIZE).get_string_spec_data_point(point_index))
            ret.append(self._data.get_data(measurements.NETWORK_NUM_REQUESTS).get_string_spec_data_point(point_index))
            ret.append(self._data.get_data(measurements.NETWORK_BYTES_IN).get_string_spec_data_point(point_index))
            ret.append(self._data.get_data(measurements.NETWORK_BYTES_OUT).get_string_spec_data_point(point_index))
            ret.append(u'')
            ret.append(u'資料紀錄時間:\nUTC {} ({:.2f}秒前)'.format(time.strftime('%Y/%m/%d %H:%M:%S'), 
                                                                   (datetime.utcnow() - time).total_seconds()))

            return u'\n'.join(ret)
        else:
            return u'查詢資料時發生錯誤: {}'.format(self._status_code)

class measurements(object):
    CONNECTIONS = 'CONNECTIONS'
    NETWORK_BYTES_IN = 'NETWORK_BYTES_IN'
    NETWORK_BYTES_OUT = 'NETWORK_BYTES_OUT'
    NETWORK_NUM_REQUESTS = 'NETWORK_NUM_REQUESTS'
    OPCOUNTER_CMD = 'OPCOUNTER_CMD'
    OPCOUNTER_QUERY = 'OPCOUNTER_QUERY'
    OPCOUNTER_UPDATE = 'OPCOUNTER_UPDATE'
    OPCOUNTER_DELETE = 'OPCOUNTER_DELETE'
    OPCOUNTER_GETMORE = 'OPCOUNTER_GETMORE'
    OPCOUNTER_INSERT = 'OPCOUNTER_INSERT'
    LOGICAL_SIZE = 'LOGICAL_SIZE'

    def __init__(self, measurements_list, last_data_timestamp):
        self._last_data_timestamp = datetime.strptime(last_data_timestamp, '%Y-%m-%dT%H:%M:%SZ')
        self._data = dict()

        for m_data in measurements_list:
            new_data = measurement_unit_data(m_data)
            self._data[new_data.name] = new_data

    @property
    def last_data_timestamp(self):
        return self._last_data_timestamp

    def get_data(self, data_type):
        """Return None if not exists."""
        return self._data.get(data_type)

class measurement_unit_data(object):
    def __init__(self, collection_dict):
        self._collection_dict = collection_dict

        dp = []
        for point in self.data_points:
            dp.append(data_point(point))
        self.data_points = dp

    @property
    def name(self):
        return self._collection_dict.get('name', u'(Unknown)')

    @property
    def units(self):
        return self._collection_dict.get('units', u'(Unknown)')

    @property
    def data_points(self):
        return self._collection_dict.get('dataPoints', u'(Unknown)')

    @data_points.setter
    def data_points(self, data_points):
        self._collection_dict['dataPoints'] = data_points

    def get_string_spec_data_point(self, point_index):
        name = data_name_converter.convert(self.name)
        unit = data_unit_converter.convert(self.units)
        
        handle_methods = { 
            measurements.LOGICAL_SIZE: self._string_spec_handle_logical_size,
            measurements.CONNECTIONS: self._string_spec_handle_unmodified
        }
        
        try:
            val = self.data_points[point_index].value
            return handle_methods.get(self.name, self._string_spec_handle_default)(name, val, unit)
        except IndexError:
            return u'{}: (查無資料)'.format(name)
        
    def _string_spec_handle_logical_size(self, name, val, unit):
        return u'{}: {:,} {} ({:.3%})'.format(name, val, unit, val / measurement_data_wrapper.MAX_LOGICAL_SIZE_BYTES)
    
    def _string_spec_handle_unmodified(self, name, val, unit):
        return u'{}: {} {}'.format(name, val, unit)
    
    def _string_spec_handle_default(self, name, val, unit):
        DECIMAL_DIGITS = 3
        
        return u'{}: {} {}'.format(name, "{1:0.{0}f}".format(min(len(str(val).split('.')[1]), DECIMAL_DIGITS), val), unit)

class data_point(object):
    def __init__(self, dict):
        self._timestamp = datetime.strptime(dict.get('timestamp'), '%Y-%m-%dT%H:%M:%SZ')
        self._value = dict.get('value')

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def value(self):
        return self._value

    def get_timestamp_string(self):
        return self._timestamp.strftime('%Y/%m/%d %H:%M:%S')

class data_unit_converter(object):
    _trans_dict = {
        'BYTES': u'B',
        'BYTES_PER_SECOND': u'B/s',
        'SCALAR': u'',
        'SCALAR_PER_SECOND': u'/s'
    }

    @staticmethod
    def convert(key):
        return data_unit_converter._trans_dict.get(key, key)

class data_name_converter(object):
    _trans_dict = {
        measurements.CONNECTIONS: u'連線數量',
        measurements.NETWORK_BYTES_IN: u'輸入流量',
        measurements.NETWORK_BYTES_OUT: u'輸出流量',
        measurements.NETWORK_NUM_REQUESTS: u'指令要求',
        measurements.OPCOUNTER_CMD: u'Op COMMAND',
        measurements.OPCOUNTER_QUERY: u'Op QUERY',
        measurements.OPCOUNTER_UPDATE: u'Op UPDATE',
        measurements.OPCOUNTER_DELETE: u'Op DELETE',
        measurements.OPCOUNTER_GETMORE: u'Op GETMORE',
        measurements.OPCOUNTER_INSERT: u'Op INSERT',
        measurements.LOGICAL_SIZE: u'已用空間'
    }

    @staticmethod
    def convert(key):
        return data_name_converter._trans_dict.get(key, key)

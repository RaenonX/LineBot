# -*- coding: utf-8 -*-

############################################################
##### CODE SOURCE: https://github.com/miczal/aqicn-sdk #####
############################################################

import requests
import logging
import urlparse
import datetime

from .main import Coordinate, output_type

class aqicn:
    UNKNOWN = u'(不明)'

    def __init__(self, app_key):
        self._aqicn_api = AqicnApi(app_key)

    def get_location_feed_aqi_data(self, coord):
        """
        Return AqiData.
        """
        try:
            aqi_data = self._aqicn_api.get_location_feed(coord)
            return AqiData(aqi_data)
        except AqicnApiError as e:
            return AqiData(e)

        return result

class AqiData:
    UNKNOWN = u'(不明)'
    UNKNOWN_INT = -1

    @staticmethod
    def aqi_level(aqi_value):
        if aqi_value < 0:
            if aqi_value == AqiData.UNKNOWN_INT:
                return AqiData.UNKNOWN
            else:
                raise ValueError('AQI value must not be minus. {}'.format(aqi_value))
        elif aqi_value < 50:
            return u'好'
        elif aqi_value < 100:
            return u'普通'
        elif aqi_value < 150:
            return u'對敏感族群不健康'
        elif aqi_value < 200:
            return u'對所有族群不健康'
        elif aqi_value < 300:
            return u'非常不健康'
        else:
            return u'有害'

    def __init__(self, data_dict):
        if isinstance(data_dict, AqicnApiError):
            self._ok = False
            self._data = { 'Message': data_dict.message }
        else:
            self._ok = 'status' in data_dict and data_dict['status'] == 'ok'
            self._data = data_dict.get('data', {})

    @property
    def ok(self):
        return self._ok

    @property
    def city_name(self):
        return self._data.get('city', {}).get('name', AqiData.UNKNOWN)

    @property
    def city_loc_coord(self):
        return Coordinate(*self._data.get('city', {}).get('geo', Coordinate(-1, -1)))

    @property
    def reference_time(self):
        """
        Reference time.

        Returns:
            Date time string formatted in %Y-%m-%d %H:%M.
        """
        ref_time = aqi_data.get('time', None)
        if ref_time is None:
            return aqicn.UNKNOWN
        else:
            return (datetime.datetime.fromtimestamp(ref_time['v']) + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

    @property
    def aqi(self):
        """
        AQI.

        Returns:
            AQI in integer.
        """
        return int(self._data.get('aqi', AqiData.UNKNOWN_INT))

    @property
    def primary_pollutant(self):
        """
        The primary pollutant. Aqi will use this index.

        Returns:
            Name of index in string.
        """
        return self._data.get('dominentpol', AqiData.UNKNOWN)

    @property
    def co(self):
        """
        Carbon Monoxide.

        Returns:
            AQI in integer.
        """
        return int(round(self._data.get('iaqi', {}).get('co', {}).get('v', AqiData.UNKNOWN_INT)))
    
    @property
    def no2(self):
        """
        Nitrogen Dioxide.

        Returns:
            AQI in integer.
        """
        return int(round(self._data.get('iaqi', {}).get('no2', {}).get('v', AqiData.UNKNOWN_INT)))
    
    @property
    def o3(self):
        """
        Ozone.

        Returns:
            AQI in integer.
        """
        return int(round(self._data.get('iaqi', {}).get('o3', {}).get('v', AqiData.UNKNOWN_INT)))
    
    @property
    def pm10(self):
        """
        PM10.

        Returns:
            AQI in integer.
        """
        return int(round(self._data.get('iaqi', {}).get('pm10', {}).get('v', AqiData.UNKNOWN_INT)))
    
    @property
    def pm25(self):
        """
        PM2.5.

        Returns:
            AQI in integer.
        """
        return int(round(self._data.get('iaqi', {}).get('pm25', {}).get('v', AqiData.UNKNOWN_INT)))
    
    @property
    def so2(self):
        """
        Sulfur Dioxide.

        Returns:
            AQI in integer.
        """
        return int(round(self._data.get('iaqi', {}).get('so2', {}).get('v', AqiData.UNKNOWN_INT)))

    def to_string(self, o_config=output_type.SIMPLE):
        if self._ok:
            ret = [u'空氣品質指數(AQI) {} ({}) - 主汙染源 {}'.format(self.aqi, AqiData.aqi_level(self.aqi), self.primary_pollutant)]

            if o_config == output_type.DETAIL:
                ret.append(u'【空氣指數細目 (AQI指數)】')
                ret.append(u'PM2.5: {} ({})'.format(self.pm25, AqiData.aqi_level(self.pm25)))
                ret.append(u'PM10: {} ({})'.format(self.pm10, AqiData.aqi_level(self.pm10)))
                ret.append(u'CO: {} ({})'.format(self.co, AqiData.aqi_level(self.co)))
                ret.append(u'NO₂: {} ({})'.format(self.no2, AqiData.aqi_level(self.no2)))
                ret.append(u'SO₂: {} ({})'.format(self.so2, AqiData.aqi_level(self.so2)))
                ret.append(u'O₃: {} ({})'.format(self.o3, AqiData.aqi_level(self.o3)))

            return u'\n'.join(ret)
        else:
            return u'資料有誤，無法顯示。({})'.format(self._data.get('Message', AqiData.UNKNOWN))

class AqicnApiError(Exception):
    _error_trans = {
        'Unknown station': '無可用偵測站。',
        'Unknown city': '未知的城市。',
        'Invalid Key': '無效的API Key。',
        'Over Quota': '已超過使用限額(1000次/分鐘)。'
    }

    def __init__(self, message):
        if message is not None and isinstance(message, (unicode, str)):
            message = AqicnApiError._error_trans.get(message.upper(), message)
        else:
            message = repr(message)

        Exception.__init__(self, message)

class AqicnApi:
    """
    Wrapper for aqicn API. Implementation based on documentation from http://aqicn.org/json-api/doc/
    Implemented API methods always return response in JSON format or throw AqicnApiError when data is invalid
    Available methods:
        - get_feed
        - get_location_feed
        - get_stations_in_area
        - search
    """

    _protocol = "https"
    _domain = "api.waqi.info"
    _header = {'user-agent': 'aqicn-sdk/0.1'}
    _expected_response_status = 200

    def __init__(self, secret, proxy=None):
        """
        Args:
            secret (str): API token
            proxy (dict [str, str]): proxies in form { 'https': 'x.x.x.x', 'http': 'y.y.y.y' }
        """
        self.secret = secret
        self.proxy = proxy if proxy else None
        self.base_url = urlparse.urlunparse((self._protocol, self._domain, "", "", "", ""))

    def request(self, endpoint, params = {}):
        """
        Sends a GET request to the configured API.
        Args:
            endpoint (str):
            params (dict): request parameters
        Returns:
             Response in requests.Response format."""
        params.update({"token": self.secret})
        return requests.get(url=self.base_url + "/" + endpoint,
                            params=params,
                            headers=self._header,
                            proxies=self.proxy)

    def json_request(self, endpoint, params={}):
        """
        Wrapper for GET request to the configured API.
        Response ALWAYS has status_code == 200 according to the documentation.
        If "data" != "ok" then AqicnApiError is thrown.
        Args:
            endpoint (str)
            params (dict): request parameters
        Returns:
             Response in JSON format (dict)
        Every request can throw AqicnApiError with "overQuota" and "invalidKey" messages.
        """
        r = self.request(endpoint=endpoint, params=params)
        
        if r.status_code != self._expected_response_status:
            logging.getLogger(__name__).warning("Default status code changed - see API documentation for more possible changes")

        try:
            json_resp = r.json()
            if json_resp["status"] != "ok": raise AqicnApiError(json_resp["data"])
            return json_resp
        except ValueError:
            raise AqicnApiError("No Data. :{}".format(r))

    # All API methods according to:
    # http://aqicn.org/json-api/doc/

    def get_feed(self, *station_name_or_station_id):
        """
        IP based feed if no arguments, station or station (id) based if 1 argument present.
        Args:
            station_name_or_station_id (str): station name or station id
        Throws:
            ValueError if more than 1 argument given
            AqicnApiError("Unknown station") if wrong id / station name given.
        """
        if len(station_name_or_station_id) > 1: raise ValueError("Only 0 or 1 arguments possible")
        return self.json_request("feed/" + ("".join(station_name_or_station_id) + "/" if station_name_or_station_id else "here/"))

    def get_location_feed(self, coord):
        """
        Geo-localized feed for the nearest station.
        Args:
            coord (Coordinate): lat lng coordinates tuple (either numeric or sting)
        """
        return self.json_request("feed/geo:{0};{1}/".format(coord.lat, coord.lng))

    def get_stations_in_area(self, lower_left, upper_right):
        """
        Feed for stations in rectangular are made from points [lower_left, upper_right].
        Args:
            lower_left (Coordinate): lat lng coordinates tuple (either numeric or sting)
            upper_right (Coordinate): lat lng coordinates tuple (either numeric or sting)
        """
        return self.json_request("map/bounds/",
                                 params={"latlng": "{0},{1},{2},{3}".format(str(lower_left.lat),  str(lower_left.lng),
                                                                            str(upper_right.lat), str(upper_right.lng))})

    def search(self, keyword):
        """
        Search for stations based on keyword.
        Args:
            keyword (str): search phrase
        """
        return self.json_request("search/", params={"keyword": keyword})

class AqicnUtils:
    @staticmethod
    def get_aqi_world_data():
        import re
        stations_data_regex = re.compile(r"mapInitWithData\((\[.*?\])\)")
        return re.search(stations_data_regex, requests.get("http://aqicn.org/map/world/", headers=AqicnApi._header).text).group(1)
    
    @staticmethod
    def scrap_data_from_website(adapter=None):
        def default_world_data_adapter(dct):
            to_replace = {'x': 'id',
                          'g': 'geo'}
            for k, v in list(dct.items()):
                if k in to_replace.keys():
                    del dct[k]
                    dct[to_replace[k]] = v
    
            for k, v in list(dct.items()):
                if k not in ["aqi", "utime", "geo", "city", "id"]: del dct[k]
                if k == "aqi" and v == "-" or v == "placeholder" or v == 999: dct[k] = 0
            return dct
    
        import json
        return json.loads(get_aqi_world_data(), object_hook=adapter if adapter else default_world_data_adapter)
    
    @staticmethod
    def get_stations_data(key="city", fields_to_include=["aqi", "id", "geo", "utime"], adapter=None):
        data = scrap_data_from_website(adapter)
        stations = {}
        for entry in data:
            fields = {}
            for field in fields_to_include: fields[field] = entry[field]
            stations[entry[key]] = fields
        return stations
    
    @staticmethod
    def get_stations_id_data():
        def id_adapter(dct):
            to_keep = ['city']
            to_replace = {'x': 'id',
                          'g': 'geo'}
            for k, v in list(dct.items()):
                if k not in to_keep and k not in to_replace: del dct[k]
                if k in to_replace.keys():
                    dct[to_replace[k]] = v
                    del dct[k]
            return dct
    
        data = scrap_data_from_website(id_adapter)
        res = {}
        for entry in data:
            res[entry["id"]] = {"city": entry["city"], "geo": entry["geo"]}
        return res
# -*- coding: utf-8 -*-

from geopy.distance import vincenty
import math

import ext
import cityids

class Coordinate(object):
    def __init__(self, latitude, longitude):
        self._latitude = latitude
        self._longitude = longitude

    @property
    def lat(self):
        return self._latitude

    @property
    def lng(self):
        return self._longitude

    def to_string(self, digit=3):
        return u'{}, {}'.format(Coordinate.latitude_to_string(self._latitude, digit), Coordinate.longitude_to_string(self._longitude, digit))

    def __str__(self):
        return self.to_string(5)

    @staticmethod
    def latitude_to_string(lat, digit=3):
        fmt = u'.{}f'.format(digit)

        if lat > 0:
            return u'N {:{}}°'.format(lat, fmt)
        elif lat < 0:
            return u'S {:{}}°'.format(lat, fmt)
        else:
            return u'{:{}}°'.format(lat, fmt)

    @staticmethod
    def longitude_to_string(lng, digit=3):
        fmt = u'.{}f'.format(digit)

        if lng > 0:
            return u'E {:{}}°'.format(lng, fmt)
        elif lng < 0:
            return u'W {:{}}°'.format(lng, fmt)
        else:
            return u'{:{}}°'.format(lng, fmt)

class CoordinateRelationship(object):
    def __init__(self, distance_km, direction_deg):
        self._distance_km = distance_km
        self._direction_deg = direction_deg

    @property
    def distance(self):
        """
        Returns:
            Distance between two coordinates. Using WGS-84 ellipsoid ,vincenty formulae and geopy to calculate.
        """
        return self._distance_km

    @property
    def direction(self):
        """
        Returns:
            Direction in degrees.
        """
        return self._direction_deg

    @staticmethod
    def _calculate_deg(source_coord, target_coord):
        d_lat = math.radians(target_coord.lat - source_coord.lat)
        d_lng = math.radians(target_coord.lng - source_coord.lng)

        lat1 = math.radians(source_coord.lat)
        lat2 = math.radians(target_coord.lat)

        y = math.sin(d_lng) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lng)
        brng = math.degrees(math.atan2(y, x)) % 360.0

        return brng

    @staticmethod
    def calculate(source_coord, target_coord):
        """
        Calculate the distance between provided coordinates and the direction from source coordinates to target coordinates.

        Returns:
            CoordinateRelationship object.
        """
        dist = vincenty((source_coord.lat, source_coord.lng), (target_coord.lat, target_coord.lng)).km
        deg = CoordinateRelationship._calculate_deg(source_coord, target_coord)

        return CoordinateRelationship(dist, deg)

    def __str__(self):
        return '位於 {:.2f}°({}) {:.2f} 公里處'.format(self.direction, ext.dir_symbol(self.direction), self.distance)

    def __unicode__(self):
        return unicode(str(self).decode('utf-8'))

class output_type(ext.EnumWithName):
    SIMPLE = 0, '簡潔'
    DETAIL = 1, '詳細'

class weather_reporter(object):
    CITY_ID_REGISTRY = cityids.CityIDRegistry('%03d-%03d.txt.gz')

    def __init__(self, owm_client, aqicn_client):
        self._owm = owm_client
        self._aqicn = aqicn_client

    def get_data_by_owm_id(self, owm_city_id, o_config=output_type.SIMPLE, interval=3, hours_within=120):
        """Return String"""
        weather_data = self._owm.get_weathers_by_id(owm_city_id, o_config, interval, hours_within)
        return self._proc_weather_data(owm_city_id, weather_data, o_config)

    def get_data_by_coord(self, coord, o_config=output_type.SIMPLE, interval=3, hours_within=120):
        """Return String"""
        weather_data = self._owm.get_weathers_by_coord(coord, o_config, interval, hours_within)
        return self._proc_weather_data(coord, weather_data, o_config)

    def _proc_weather_data(self, owm_city_id_or_coord, weather_data, o_config):
        if weather_data is not None:
            ret = []
            coord = weather_data.get_location_coordinate()
            aqi_data = self._aqicn.get_location_feed_aqi_data(coord)

            if isinstance(owm_city_id_or_coord, Coordinate):
                detail_location = u' (氣象站{})'.format(CoordinateRelationship.calculate(owm_city_id_or_coord, coord))
            else:
                detail_location = u''

            ret.append(u'位置: {}{}'.format(weather_data.get_location_string(o_config), detail_location))
            ret.append(u'')
            ret.append(u'【===空氣品質相關===】')
            ret.append(aqi_data.to_string(o_config))
            ret.append(u'')
            ret.append(u'【===紫外線相關===】')
            ret.append(weather_data.get_uv_string())
            ret.append(u'')
            ret.append(u'【===天氣相關===】')
            ret.append(weather_data.get_weather_string(o_config))

            return u'\n'.join(ret)
        else:
            return u'查無資料。({})'.format(owm_city_id_or_coord)
# -*- coding: utf-8 -*-

import os, io, json
import datetime
from collections import namedtuple

import numpy
import pyowm
from math import exp
from pyowm.exceptions.not_found_error import NotFoundError

import ext

from .main import output_type, Coordinate

Weather_ID_Pair = namedtuple('Weather_ID_Pair', ['name', 'id'])

uv_risk_trans = {
     'low': u'低', 
     'moderate': u'中', 
     'high': u'高', 
     'very high': u'極高', 
     'extreme': u'危險' 
}

Beaufort_scale = lambda v: int(round((v/0.836)**(2/3.0)))

class owm(object):
    DEFAULT_TAIPEI = Weather_ID_Pair('Taipei', 1668341)
    DEFAULT_TAICHUNG = Weather_ID_Pair('Taichung', 1668399)
    DEFAULT_KAOHSIUNG = Weather_ID_Pair('Kaohsiung', 1673820)
    DEFAULT_KUALA_LUMPER = Weather_ID_Pair('Kuala Lumper', 1735161)
    DEFAULT_HONG_KONG = Weather_ID_Pair('Hong Kong', 1819729)
    DEFAULT_MACAU = Weather_ID_Pair('Macau', 1821274)

    def __init__(self, app_key):
        self._owm_client = pyowm.OWM(app_key)

    def get_weathers_by_id(self, id, o_config=output_type.SIMPLE, interval=3, hours_within=120):
        """\
        Return None if resource not found. Else return string.
        interval -> floor.
        hours_within -> Max=120 (5 days)\
        """
        try:
            f = self._owm_client.three_hours_forecast_at_id(id).get_forecast()
            f_w = f.get_weathers()

            o = self._owm_client.weather_at_id(id)
            c_w = o.get_weather()

            l = f.get_location()

            forecast_weather_list = [weather(w) for w in f_w[:hours_within / 3:interval / 3]]
            uv = self._owm_client.uvindex_around_coords(l.get_lat(), l.get_lon())

            return OwmResult(l, weather(c_w), forecast_weather_list, uv)
        except NotFoundError:
            return None

    def get_weathers_by_coord(self, coord, o_config=output_type.SIMPLE, interval=3, hours_within=120):
        """\
        Return None if resource no found. Else string.
        interval -> floor.
        hours_within -> Max=120 (5 days)\
        """
        try:
            f = self._owm_client.three_hours_forecast_at_coords(coord.lat, coord.lng).get_forecast()
            f_w = f.get_weathers()

            o = self._owm_client.weather_at_coords(coord.lat, coord.lng)
            c_w = o.get_weather()

            l = f.get_location()

            forecast_weather_list = [weather(w) for w in f_w[:hours_within / 3:interval / 3]]
            uv = self._owm_client.uvindex_around_coords(l.get_lat(), l.get_lon())
            
            return OwmResult(l, weather(c_w), forecast_weather_list, uv)
        except NotFoundError:
            return None

    @staticmethod
    def icon_url(icon_id):
        return u'http://openweathermap.org/img/w/{}.png'.format(icon_id)

class OwmResult:
    def __init__(self, location, current_weather, forecast_weather_list, uv):
        self._location = location
        self._current = current_weather
        self._weather_list = forecast_weather_list
        self._uv = uv_index(uv)

    def get_uv_string(self):
        return self._uv.to_string()

    def get_weather_string(self, o_config):
        ret = []
        
        ret.append(u'【目前天氣】')
        ret.append(self._current.to_string(o_config))
        ret.append(u'')
        ret.append(u'【未來天氣】')
        ret.append(u'\n\n'.join([w.to_string(o_config) for w in self._weather_list]))

        return u'\n'.join(ret)

    def get_location_string(self, o_config):
        ret = u'{}, {} (#{})'.format(self._location.get_name(), self._location.get_country(), self._location.get_ID())

        if o_config == output_type.DETAIL:
            ret += u' @{}'.format(Coordinate(self._location.get_lat(), self._location.get_lon()))

        return ret

    def get_location_coordinate(self):
        return Coordinate(self._location.get_lat(), self._location.get_lon())

class weather(object):
    UNKNOWN = u'(不明)'
    with io.open(os.path.dirname(__file__) + '/owm_code.json', encoding='utf-8') as f:
        r = f.read()
        CODE_DICT = json.loads(r)

    def __init__(self, weather):
        self._weather = weather

    def to_string(self, o_config):
        ret = []
        temp = self._weather.get_temperature('celsius')

        ref_time = self._weather.get_reference_time()
        if ref_time is None:
            ref_time = weather.UNKNOWN
        else:
            ref_time = (datetime.datetime.fromtimestamp(ref_time) + datetime.timedelta(hours=8)).strftime(u'%Y-%m-%d %H:%M')

        status_code = str(self._weather.get_weather_code())
        status = weather.CODE_DICT.get(status_code, u'(Code {})'.format(status_code))

        if temp is None:
            temp_cur = weather.UNKNOWN
        else:
            temp_cur = temp.get('temp', weather.UNKNOWN)

        humid = self._weather.get_humidity()
        if humid is None:
            humid = weather.UNKNOWN

        ret.append(u'{} | 氣溫 {:.2f} ℃ | 濕度 {} %'.format(status, temp_cur, humid, ref_time))
        
        if o_config == output_type.DETAIL:
            if temp is None:
                min_temp = temp.get('temp_min', weather.UNKNOWN)
                max_temp = temp.get('temp_max', weather.UNKNOWN)
            else:
                min_temp = temp.get('temp_min', weather.UNKNOWN)
                max_temp = temp.get('temp_max', weather.UNKNOWN)

            cloud = self._weather.get_clouds()
            if cloud is None:
                cloud = weather.UNKNOWN

            rain = self._weather.get_rain()
            if len(rain) > 0:
                rain = rain.get(u'3h', 0)
            else:
                rain = 0

            snow = self._weather.get_snow()
            if len(snow) > 0:
                snow = snow.get(u'3h', 0)
            else:
                snow = 0

            wind = self._weather.get_wind()
            if wind is None:
                wind_summary = u'風力相關: {}'.format(weather.UNKNOWN)
            else:
                wind_spd = wind.get('speed', weather.UNKNOWN)
                if wind_spd == weather.UNKNOWN:
                    wind_lv = weather.UNKNOWN
                else:
                    wind_lv = Beaufort_scale(wind_spd)
                    wind_spd = u'{:.2f}'.format(wind_spd)
                    
                wind_deg = wind.get('deg', weather.UNKNOWN)
                if wind_deg == weather.UNKNOWN:
                    wind_dir = weather.UNKNOWN
                else:
                    wind_dir = ext.dir_symbol(wind_deg)
                    wind_deg = u'{:.2f}'.format(wind_deg)

                try:
                    wind_summary = u''
                    if all(k != weather.UNKNOWN for k in (wind_spd, wind_lv)):
                        wind_summary += u'風速 {} m/s ({}級)'.format(wind_spd, wind_lv)
                    if all(k != weather.UNKNOWN for k in (wind_deg, wind_dir)):
                        wind_summary += u' {}° ({})'.format(wind_deg, wind_dir)
                except ValueError:
                    wind_summary = u'風力相關: {}'.format(wind)

            if all(item is not None for item in (temp, wind, humid)) and all(item != weather.UNKNOWN for item in (temp_cur, wind_spd, humid)):
                app_temp = weather.apparent_temperature(temp_cur, wind_spd, humid)
            else:
                app_temp = weather.UNKNOWN

            ret.append(u'最低氣溫{:.2f}℃ | 最高氣溫{:.2f}℃ | 體感溫度{:.2f}℃'.format(min_temp, max_temp, app_temp))
            ret.append(u'雲量{}% | 雨量 {:.2f} mm | 雪量 {:.2f} mm'.format(cloud, rain, snow))
            ret.append(wind_summary)

        ret.append(u'@{} (UTC+8)'.format(ref_time))

        return u'\n'.join(ret)

    @staticmethod
    def apparent_temperature(temp_celcius, wind_m_s, humidity):
        wind_m_s = float(wind_m_s)
        humidity = float(humidity)
        temp_celcius = float(temp_celcius)
        return (1.04 * temp_celcius) + (0.2 * ((humidity / 100.0) * 6.105 * exp(17.27 * temp_celcius / (237.7 + temp_celcius)))) - (0.65 * wind_m_s) - 2.7

class uv_index(object):
    def __init__(self, uv):
        self._uv_index = uv

    def to_string(self):
        if self._uv_index is None:
            uv_summary = weather.UNKNOWN
        else:
            uv_lv = self._uv_index.get_value()
            uv_risk_org = self._uv_index.get_exposure_risk()
            uv_risk = uv_risk_trans.get(uv_risk_org, uv_risk_org) 

            uv_summary = u'紫外線(UV)指數 {} ({})'.format(uv_lv, uv_risk)

        return uv_summary
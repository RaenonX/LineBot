# -*- coding: utf-8 -*-

import error, bot, tool, ext

from .base import db_base, dict_like_mapping

DB_NAME = 'sys'

class weather_report_config(db_base):
    COLLECTION_NAME = 'weather_cfg'

    def __init__(self, mongo_client):
        super(weather_report_config, self).__init__(mongo_client, DB_NAME, weather_report_config.COLLECTION_NAME, False, [weather_report_config_data.USER_ID])

    def add_config(self, uid, city_ids, mode=tool.weather.output_type.SIMPLE, interval=3, data_range=120):
        """Return result in string"""
        city_ids = ext.to_int(city_ids)

        if not bot.line_api_wrapper.is_valid_user_id(uid):
            return error.error.line_bot_api.illegal_user_id(uid)
        if data_range < 0 or data_range % 3 != 0 or data_range > 120:
            return error.error.main.invalid_thing_with_correct_format(u'資料範圍(小時內)', u'0~120之間，並且是3的倍數的整數。', data_range)
        if interval < 0 or interval % 3 != 0 or interval > data_range:
            return error.error.main.invalid_thing_with_correct_format(u'資料頻率', u'0~{}(資料範圍)之間，並且是3的倍數的整數。'.format(data_range), interval)
        if city_ids is None:
            return error.error.main.invalid_thing_with_correct_format(u'城市ID', u'整數', city_ids)

        mod_result = self.update_one({ weather_report_config_data.USER_ID: uid }, { '$pushAll': { weather_report_config_data.CONFIG: [weather_report_child_config.init_by_field(city_id, mode, interval, data_range) for city_id in city_ids] } }, True)

        if mod_result.modified_count > 0:
            return u'已新增常用城市。\n{}'.format(u'\n'.join([u'城市ID: {} ({})\n查看{}小時內每{}小時的資料。'.format(city_id, unicode(mode), data_range, interval) for city_id in city_ids]))
        else:
            return u'沒有更動任何常用城市。'

    def del_config(self, uid, city_ids):
        """Return result in string"""
        city_ids = ext.to_int(city_ids)

        if not bot.line_api_wrapper.is_valid_user_id(uid):
            return error.error.line_bot_api.illegal_user_id(uid)
        if city_ids is None:
            return error.error.main.invalid_thing_with_correct_format(u'城市ID', u'整數', city_ids)

        mod_result = self.update_one({ weather_report_config_data.USER_ID: uid }, { '$pullAll': { weather_report_config_data.CONFIG: { weather_report_child_config.CITY_ID: city_ids } } }, True)

        if mod_result.modified_count > 0:
            return u'已刪除常用城市。\n城市ID: {}'.format(u'、'.join([u'#{}'.format(id) for id in city_ids]))
        else:
            return u'沒有更動任何常用城市。'

    def get_config(self, uid):
        """None if no config exists."""
        config = self.find_one({ weather_report_config_data.USER_ID: uid })
        if config is not None:
            return weather_report_config_data(config)
        else:
            return None

class weather_report_config_data(dict_like_mapping):
    """\
    {
        USER_ID: STRING - INDEX,
        CONFIG: [ CONFIG_DATA, CONFIG_DATA... ]
    }\
    """
    USER_ID = 'uid'
    CONFIG = 'cfg'

    @staticmethod
    def init_by_field(uid, config=None):
        init_dict = {
            weather_report_config_data.USER_ID: uid,
            weather_report_config_data.CONFIG: [weather_report_child_config(c) for c in config] if config is not None else []
        }
        
        return weather_report_config_data(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (weather_report_config_data.USER_ID, weather_report_config_data.CONFIG)):
            raise ValueError('Incomplete dictionary. {}'.format(org_dict))

        super(weather_report_config_data, self).__init__(org_dict)

    @property
    def uid(self):
        return self[weather_report_config_data.USER_ID]

    @property
    def config(self):
        return [weather_report_child_config(c) for c in self[weather_report_config_data.CONFIG]]

class weather_report_child_config(dict_like_mapping):
    """\
    {
        CITY_ID: INTEGER, 
        MODE: OUTPUT_CONFIG,
        INTERVAL: INTEGER,
        DATA_RANGE: INTEGER
    }\
    """
    CITY_ID = 'c'
    MODE = 'm'
    INTERVAL = 'i'
    DATA_RANGE = 'r'

    @staticmethod
    def init_by_field(city_id, mode, interval, data_range_hr):
        init_dict = {
            weather_report_child_config.CITY_ID: city_id,
            weather_report_child_config.MODE: mode,
            weather_report_child_config.INTERVAL: interval,
            weather_report_child_config.DATA_RANGE: data_range_hr,
        }
        
        return weather_report_child_config(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (weather_report_child_config.CITY_ID, weather_report_child_config.MODE, weather_report_child_config.INTERVAL, weather_report_child_config.DATA_RANGE)):
            raise ValueError('Incomplete dictionary. {}'.format(org_dict))

        super(weather_report_child_config, self).__init__(org_dict)
        
    @property
    def city_id(self):
        return self[weather_report_child_config.CITY_ID]

    @property
    def mode(self):
        return self[weather_report_child_config.MODE]

    @property
    def interval(self):
        return self[weather_report_child_config.INTERVAL]

    @property
    def data_range(self):
        return self[weather_report_child_config.DATA_RANGE]
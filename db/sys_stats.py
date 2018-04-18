# -*- coding: utf-8 -*-
import pymongo
from datetime import date, datetime, timedelta
from collections import OrderedDict

from .base import db_base, dict_like_mapping, SYSTEM_DATABASE_NAME
from .content_holder import webpage_content_type
import bot, ext

class extend_function_category(ext.EnumWithName):
    IMGUR_UPLOAD = 1, 'IMGUR圖片上傳'
    GET_STICKER_ID = 2, '獲取貼圖ID'
    BASIC_CALCUALTE = 3, '基本計算功能'
    AUTO_REPLY = 4, '自動回覆'
    SPECIAL_TEXT_KEYWORD = 5, '特殊關鍵字'
    REQUEST_WEATHER_REPORT = 6, '查詢氣象'

class system_statistics(db_base):
    COLLECTION_NAME = 'statistics'
    DATA_EXPIRE_SECS = 15 * 24 * 60 * 60

    def __init__(self, mongo_client):
        super(system_statistics, self).__init__(mongo_client, SYSTEM_DATABASE_NAME, system_statistics.COLLECTION_NAME, False)
        self.create_index([(system_data.RECORD_DATE, pymongo.DESCENDING)], expireAfterSeconds=system_statistics.DATA_EXPIRE_SECS)

    def _new_record(self, date):
        self.insert_one(system_data.init_by_field(date))

    def _get_today_date(self):
        return datetime.combine(date.today(), datetime.min.time())

    def command_called(self, command):
        today = self._get_today_date()
        result = self.update_one({ system_data.RECORD_DATE: today },
                                 { '$inc': { system_data.COMMAND_CALLED + '.' + command: 1 } }, True)

    def webpage_viewed(self, webpage_type_enum):
        today = self._get_today_date()
        result = self.update_one({ system_data.RECORD_DATE: today },
                                 { '$inc': { system_data.WEBPAGE_VIEWED + '.' + str(webpage_type_enum): 1 } }, True)

    def extend_function_used(self, extend_cat_enum):
        today = self._get_today_date()
        result = self.update_one({ system_data.RECORD_DATE: today },
                                 { '$inc': { system_data.EXTEND_FUNCTION_USED + '.' + str(extend_cat_enum): 1 } }, True)

    def get_statistics(self):
        SEPARATOR = '_'

        keys = {system_data.COMMAND_CALLED: list(bot.sys_cmd_dict.keys()), 
                system_data.GAME_COMMAND_USED: list(bot.game_cmd_dict.keys()), 
                system_data.WEBPAGE_VIEWED: list([unicode(type_enum) for type_enum in webpage_content_type]),
                system_data.EXTEND_FUNCTION_USED: list([unicode(type_enum) for type_enum in extend_function_category])}

        group_dict = {cat + SEPARATOR + c: { '$sum': '${}.{}'.format(cat, c.encode('utf-8')) } for cat, arr in keys.iteritems() for c in arr}
        group_dict['_id'] = None

        aggr_data = { d_in: None for d_in in StatisticsData.DAYS_IN }

        for day_in in aggr_data.iterkeys():
            aggr_dict = self.aggregate([
                { '$match': { 'rec_date': { '$gt': self._get_today_date() - timedelta(days=day_in) } } },
                { '$group': group_dict }
            ]).next()
            del aggr_dict['_id']
            aggr_data[day_in] = aggr_dict

        proc_data = { cat: { c: StatisticsData({ day_in: data.get(c, 0) for day_in, data in aggr_data.iteritems() }) for c in cat_keys } for cat, cat_keys in keys.iteritems() }

        return u'\n\n'.join([u'-以下統計資料每日AM 8重計-\n-次數格式為[{}]-'.format(u'、'.join([u'{}日內'.format(day_num) for day_num in StatisticsData.DAYS_IN]))] + 
                            [u'【{}】'.format(system_data.translate_category(cat)) + u'\n' + u'\n'.join([c + u': ' + StatisticsData({ day_in: data.get(cat + SEPARATOR + c, 0) for day_in, data in aggr_data.iteritems() }).get_string() for c in cat_keys]) for cat, cat_keys in keys.iteritems()])

    def all_data(self):
        return [system_data(data) for data in list(self.find())]

    def get_data_at_date(self, date):
        return system_data(self.find_one({ system_data.RECORD_DATE: date }))

class system_data(dict_like_mapping):
    """
    {
        date: DATE,
        command_called: {
            command: INTEGER,
            ...
            ...
        },
        webpage_viewed: {
            webpage_type: INTEGER,
            ...
            ...
        },
        extend_func_used: {
            ext_func_cat: INTEGER,
            ...
            ...
        }
    }
    """
    RECORD_DATE = 'rec_date'
    COMMAND_CALLED = 'cmd'
    GAME_COMMAND_USED = 'gm'
    WEBPAGE_VIEWED = 'wp'
    EXTEND_FUNCTION_USED = 'ext'

    _CAT_TRANS_DICT = { COMMAND_CALLED: u'系統指令', WEBPAGE_VIEWED: u'網頁瀏覽', EXTEND_FUNCTION_USED: u'延展功能', GAME_COMMAND_USED: u'遊戲指令' }

    @staticmethod
    def translate_category(cat):
        return system_data._CAT_TRANS_DICT.get(cat, cat)

    @staticmethod
    def init_by_field(date=None):
        init_dict = {
            system_data.COMMAND_CALLED: {},
            system_data.GAME_COMMAND_USED: {},
            system_data.WEBPAGE_VIEWED: {},
            system_data.EXTEND_FUNCTION_USED: {}
        }
        if data is not None:
            init_dict[system_data.RECORD_DATE] = date

        return system_data(init_dict, date is None)

    def __init__(self, org_dict, skip_date_check=False):
        if org_dict is not None:
            if not skip_date_check and not system_data.RECORD_DATE in org_dict:
                raise ValueError('Must have date in data')

            if not system_data.COMMAND_CALLED in org_dict:
                org_dict[system_data.COMMAND_CALLED] = {}

            if not system_data.WEBPAGE_VIEWED in org_dict:
                org_dict[system_data.WEBPAGE_VIEWED] = {}

            if not system_data.EXTEND_FUNCTION_USED in org_dict:
                org_dict[system_data.EXTEND_FUNCTION_USED] = {}

            if not system_data.GAME_COMMAND_USED in org_dict:
                org_dict[system_data.GAME_COMMAND_USED] = {}
        else:
            raise ValueError('Dictionary is none.')

        return super(system_data, self).__init__(org_dict)

    @property
    def command_called(self):
        return self[system_data.COMMAND_CALLED]

    @property
    def webpage_viewed(self):
        return self[system_data.WEBPAGE_VIEWED]

    @property
    def extend_func_used(self):
        return self[system_data.EXTEND_FUNCTION_USED]

    @property
    def game_command_used(self):
        return self[system_data.GAME_COMMAND_USED]

    @property
    def date(self):
        return self.get(system_data.RECORD_DATE, None)

class StatisticsData(object):
    DAYS_IN = [1, 3, 7, 15]

    def __init__(self, dict):
        """
        Dict format:
        { DAYS_IN: count, DAYS_IN: count... }
        """
        self._dict = OrderedDict(sorted(dict.iteritems()))

    def get_string(self):
        return u' | '.join([unicode(self._dict[day_in_num]) for day_in_num in StatisticsData.DAYS_IN])
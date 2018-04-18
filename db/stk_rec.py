# -*- coding: utf-8 -*-

import pymongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta

from .base import db_base, dict_like_mapping
from .misc import PackedResult
import error, bot, ext

DB_NAME = 'rec'

def package_id_to_url(package_id):
    return u'https://line.me/S/sticker/{}'.format(package_id)

class ranking_category(ext.EnumWithName):
    PACKAGE = 1, '圖包'
    STICKER = 2, '貼圖'

class sticker_recorder(db_base):
    COLLECTION_NAME = 'stk'
    DATA_EXPIRE_DAYS = 21
    DATA_EXPIRE_SECS = DATA_EXPIRE_DAYS * 24 * 60 * 60

    def __init__(self, mongo_client):
        super(sticker_recorder, self).__init__(mongo_client, DB_NAME, sticker_recorder.COLLECTION_NAME, False)
        self.create_index([(sticker_record_data.TIMESTAMP, pymongo.DESCENDING)], expireAfterSeconds=sticker_recorder.DATA_EXPIRE_SECS)

    def record(self, package_id, sticker_id):
        self.insert_one(sticker_record_data.init_by_field(package_id, sticker_id))

    def get_ranking(self, category, hours_range_within=None, limit=None):
        if category == ranking_category.PACKAGE:
            return hottest_package_str(hours_range_within, limit)
        elif category == ranking_category.STICKER:
            return hottest_package_str(hours_range_within, limit)
        else:
            raise RuntimeError('Undefined ranking category.')

    def hottest_package_str(self, hours_range_within=None, limit=None):
        """
        Set hours_range_within to None to get full time ranking.
        Set limit to None to get full ranking.
        """
        text_to_join = [u'因資料庫大小限制，故貼圖紀錄最多只可回溯{}天。\n\n熱門貼圖排行(圖包ID分類)'.format(sticker_recorder.DATA_EXPIRE_DAYS)]

        pipeline = []
        COUNT = 'ct'

        if hours_range_within is not None:
            text_to_join[0] += u' - {}小時內'.format(hours_range_within)
            pipeline.append({ '$match': { '_id': { '$gt': ObjectId.from_datetime(datetime.now() - timedelta(hours=hours_range_within)) } } })

        pipeline.append({ '$group': { 
            '_id': '$' + sticker_record_data.PACKAGE_ID,
            COUNT: { '$sum': 1 }
        } })

        pipeline.append({ '$sort': { 
            COUNT: pymongo.DESCENDING
        } })

        if limit is not None:
            pipeline.append({ '$limit': limit })
            text_to_join[0] += u' - 前{}名'.format(limit)

        aggr_cursor = self.aggregate(pipeline)

        for index, data in enumerate(aggr_cursor, start=1):
            text_to_join.append(u'第{}名 - {} ({})'.format(index, package_id_to_url(data['_id']), data[COUNT]))

        return u'\n'.join(text_to_join)

    def hottest_sticker_str(self, hours_range_within=None, limit=None):
        """
        Will return PackedResult. Limited is for LINE message output, Full is for webpage generating.

        Set hours_range_within to None to get full time ranking.
        Set limit to None to get full ranking.
        """
        title = u'因資料庫大小限制，故貼圖紀錄最多只可回溯{}天。\n\n熱門貼圖排行(貼圖ID分類)'.format(sticker_recorder.DATA_EXPIRE_DAYS)

        pipeline = []
        COUNT = 'ct'

        if hours_range_within is not None:
            title += u' - {}小時內'.format(hours_range_within)
            pipeline.append({ '$match': { '_id': { '$gt': ObjectId.from_datetime(datetime.now() - timedelta(hours=hours_range_within)) } } })

        pipeline.append({ '$group': { 
            '_id': { k: '$' + k for k in (sticker_record_data.STICKER_ID, sticker_record_data.PACKAGE_ID) },
            COUNT: { '$sum': 1 }
        } })

        pipeline.append({ '$sort': { 
            COUNT: pymongo.DESCENDING
        } })

        if limit is not None:
            pipeline.append({ '$limit': limit })
            title += u' - 前{}名'.format(limit)

        aggr_cursor = self.aggregate(pipeline)

        limited = [title]
        full = []

        for index, data in enumerate(aggr_cursor, start=1):
            stk_id = data['_id'][sticker_record_data.STICKER_ID]

            limited_text = u'第{}名 - 貼圖ID {} ({})'.format(index, stk_id, data[COUNT])

            limited.append(limited_text)
            full.append((limited_text, package_id_to_url(data['_id'][sticker_record_data.PACKAGE_ID]), bot.line_api_wrapper.sticker_png_url(stk_id)))

        return PackedResult(u'\n'.join(limited), full)

class sticker_record_data(dict_like_mapping):
    """
    {
        timestamp: DATETIME
        package_id: INTEGER,
        sticker_id: INTEGER
    }
    """
    TIMESTAMP = 'ts'
    PACKAGE_ID = 'pkg'
    STICKER_ID = 'stk'

    @staticmethod
    def init_by_field(package_id, sticker_id):
        init_dict = {
            sticker_record_data.STICKER_ID: sticker_id,
            sticker_record_data.PACKAGE_ID: package_id
        }
        return sticker_record_data(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (sticker_record_data.STICKER_ID, sticker_record_data.PACKAGE_ID)):
            raise ValueError(u'Incomplete data. {}'.format(org_dict))

        if sticker_record_data.TIMESTAMP not in org_dict:
            org_dict[sticker_record_data.TIMESTAMP] = datetime.now()

        super(sticker_record_data, self).__init__(org_dict)

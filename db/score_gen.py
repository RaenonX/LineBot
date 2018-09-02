# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

import pymongo
from bson.objectid import ObjectId
from bson import Decimal128

import error

from .base import db_base, dict_like_mapping
from .uid_ref import user_id_ref_manager

DB_NAME = 'rec'

class sc_gen_data_manager(db_base):
    COLLECTION_NAME = 'score_gen'
    DATA_EXPIRE_DAYS = 365
    DATA_EXPIRE_SECS = DATA_EXPIRE_DAYS * 24 * 60 * 60

    def __init__(self, mongo_client):
        super(sc_gen_data_manager, self).__init__(mongo_client, DB_NAME, sc_gen_data_manager.COLLECTION_NAME, False)
        self.create_index([(sc_gen_data.TIMESTAMP, pymongo.DESCENDING)], expireAfterSeconds=sc_gen_data_manager.DATA_EXPIRE_SECS)

        self._max_data = self.get_max_sc_gen_data()
        self._min_data = self.get_min_sc_gen_data()

        self._uid_ref = user_id_ref_manager(mongo_client)

    def record(self, score, uid):
        new_data = sc_gen_data.init_by_field(score, self._uid_ref.get_ref_id_or_record(uid))

        self.insert_one(new_data)

        if score > self._max_data.score:
            self._max_data = new_data

        if score < self._min_data.score:
            self._min_data = new_data

    def get_max_user_data(self, time_sec_limit=None):
        """Return None if no data"""
        self.get_max_sc_gen_data(time_sec_limit)

        return self.get_spec_user_data(uid_ref=self._max_data.user_id_ref, time_sec_limit=time_sec_limit)

    def get_min_user_data(self, time_sec_limit=None):
        """Return None if no data"""
        self.get_min_sc_gen_data(time_sec_limit)
        
        return self.get_spec_user_data(uid_ref=self._min_data.user_id_ref, time_sec_limit=time_sec_limit)

    def get_spec_user_data(self, uid=None, time_sec_limit=None, uid_ref=None):
        """Return None if no data. Need to specify either uid or uid_ref."""
        if uid is None and uid_ref is None:
            raise ValueError(u'Specify either uid or uid_ref.')
        if uid_ref is None:
            uid_ref = self._uid_ref.get_ref_id_or_record(uid)

        match_filter = { sc_gen_data.USER_ID_REF: uid_ref }

        if time_sec_limit is not None:
            match_filter[sc_gen_data.TIMESTAMP] = { '$gt': datetime.now() - timedelta(seconds=time_sec_limit) }

        aggr_cursor = self.aggregate([ 
            {
                "$match": match_filter
            },
            { 
                "$group": { 
                    "_id": None,
                    sc_gen_user_data.MAX: { "$max": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.MIN: { "$min": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.AVG: { "$avg": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.STANDARD_DEVIATION: { "$stdDevSamp": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.ATTEMPT: { "$sum": 1 }
                }
            },
            { 
                "$project": { 
                    sc_gen_user_data.USER_ID_REF: { "$literal": uid_ref },
                    sc_gen_user_data.MAX: True, 
                    sc_gen_user_data.MIN: True, 
                    sc_gen_user_data.AVG: True, 
                    sc_gen_user_data.STANDARD_DEVIATION: True, 
                    sc_gen_user_data.ATTEMPT: True
                }
            }
        ])

        try:
            return sc_gen_user_data(next(aggr_cursor))
        except StopIteration:
            return sc_gen_user_data({}, True)

    def get_max_sc_gen_data(self, time_sec_limit=None):
        max_rec = self.get_sc_gen_data_by_sort([(sc_gen_data.SCORE, pymongo.DESCENDING)], time_sec_limit)

        self._max_data = sc_gen_data(max_rec) if max_rec is not None else sc_gen_data.init_by_field(-1, "")

        return self._max_data

    def get_min_sc_gen_data(self, time_sec_limit=None):
        min_rec = self.get_sc_gen_data_by_sort([(sc_gen_data.SCORE, pymongo.ASCENDING)], time_sec_limit)

        self._min_data = sc_gen_data(min_rec) if min_rec is not None else sc_gen_data.init_by_field(-1, "")

        return self._min_data

    def get_sc_gen_data_by_sort(self, sort, time_sec_limit=None):
        filter_dict = {}

        if time_sec_limit is not None:
            filter_dict[sc_gen_data.TIMESTAMP] = { '$gt': datetime.now() - timedelta(seconds=time_sec_limit) }

        return self.find_one(filter_dict, sort=sort)

    def get_analyzed_data(self, time_sec_limit=None):
        match_filter = {}

        if time_sec_limit is not None:
            match_filter[sc_gen_data.TIMESTAMP] = { '$gt': datetime.now() - timedelta(seconds=time_sec_limit) }

        aggr_cursor = self.aggregate([ 
            {
                "$match": match_filter
            },
            { 
                "$group": { 
                    "_id": None,
                    sc_gen_user_data.MAX: { "$max": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.MIN: { "$min": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.AVG: { "$avg": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.STANDARD_DEVIATION: { "$stdDevSamp": "$" + sc_gen_data.SCORE }, 
                    sc_gen_user_data.ATTEMPT: { "$sum": 1 },
                    sc_gen_user_data.USER_ID_REF: { "$sum": 1 } # Dummy
                }
            }
        ])

        try:
            return sc_gen_user_data(next(aggr_cursor))
        except StopIteration:
            return sc_gen_user_data({}, True)

    def get_analyzed_data_today(self):
        return self.get_analyzed_data(sc_gen_data_manager.get_today_past_seconds())

    @staticmethod
    def get_today_past_seconds():
        now = datetime.now()
        return (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

class sc_gen_user_data(dict_like_mapping):
    """
    {
        max: SC_GEN_DATA,
        min: SC_GEN_DATA,
        avg: DOUBLE,
        sds: DOUBLE,
        attempt: DOUBLE,
        user_id: INT - UID_REF
    }

    if user_id is empty string, then this data is dummy.
    """
    MAX = "M"
    MIN = "m"
    AVG = "a"
    STANDARD_DEVIATION = "s"
    ATTEMPT = "t"
    USER_ID_REF = "u"
    
    def __init__(self, org_dict, is_dummy=False):
        if is_dummy:
            org_dict = { sc_gen_user_data.MAX: -1,
                         sc_gen_user_data.MIN: -1,
                         sc_gen_user_data.AVG: -1,
                         sc_gen_user_data.STANDARD_DEVIATION: -1,
                         sc_gen_user_data.ATTEMPT: -1,
                         sc_gen_user_data.USER_ID_REF: -1 }

        if not is_dummy and not all(k in org_dict for k in (sc_gen_user_data.MAX, sc_gen_user_data.MIN, sc_gen_user_data.AVG,
                                                             sc_gen_user_data.ATTEMPT, sc_gen_user_data.STANDARD_DEVIATION, sc_gen_user_data.USER_ID_REF)):
            raise ValueError(u'Incomplete data. {} - {}'.format(is_dummy, org_dict))

        self._is_dummy = is_dummy

        super(sc_gen_user_data, self).__init__(org_dict)

    def get_status_string(self):
        if not self._is_dummy:
            ret = u"已使用運勢{}次\n最高: {:.5f} | 最低: {:.5f}\n平均: {:.5f} | 標準差: {:.5f}".format(
                self.attempt, float(str(self.max)), float(str(self.min)), float(str(self.avg)), float(str(self.sds) if self.sds is not None else 0.0))
        else:
            ret = u"查無資料。"

        return ret

    @property
    def user_id_ref(self):
        return self[sc_gen_user_data.USER_ID_REF]
    
    @property
    def attempt(self):
        return self[sc_gen_user_data.ATTEMPT]
    
    @property
    def max(self):
        return self[sc_gen_user_data.MAX]
    
    @property
    def min(self):
        return self[sc_gen_user_data.MIN]
    
    @property
    def avg(self):
        return self[sc_gen_user_data.AVG]
    
    @property
    def sds(self):
        return self[sc_gen_user_data.STANDARD_DEVIATION]

    @property
    def is_dummy(self):
        return self._is_dummy

class sc_gen_data(dict_like_mapping):
    """
    {
        score: DOUBLE,
        user_id: INT - UID_REF
    }
    """
    SCORE = 's'
    USER_ID_REF = 'u'
    TIMESTAMP = 't'

    @staticmethod
    def init_by_field(score, user_id, timestamp=None):
        init_dict = {
            sc_gen_data.SCORE: Decimal128(str(score)),
            sc_gen_data.USER_ID_REF: user_id
        }
        
        if timestamp is None:
            init_dict[sc_gen_data.TIMESTAMP] = datetime.now()

        return sc_gen_data(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (sc_gen_data.SCORE, sc_gen_data.USER_ID_REF)):
            raise ValueError(u'Incomplete data. {}'.format(org_dict))

        super(sc_gen_data, self).__init__(org_dict)

    @property
    def score(self):
        return self[sc_gen_data.SCORE]

    @property
    def user_id_ref(self):
        return self[sc_gen_data.USER_ID_REF]

    @property
    def timestamp(self):
        """Type: DateTime"""
        return self[sc_gen_data.TIMESTAMP]

# -*- coding: utf-8 -*-

from datetime import datetime

import pymongo

import error

from .base import db_base, dict_like_mapping
from .gid_ref import group_id_ref_manager

DB_NAME = "rec"

class txt_rec_manager(db_base):
    COLLECTION_NAME = "txt_rec"

    EXPIRE_SECS = 86400

    RANKING_COUNT_KEY = 'ct'

    def __init__(self, mongo_client):
        self._gid_ref = group_id_ref_manager(mongo_client)

        super(txt_rec_manager, self).__init__(mongo_client, DB_NAME, txt_rec_manager.COLLECTION_NAME, False)

        self.create_index([(txt_rec_data.TIMESTAMP, pymongo.DESCENDING)], expireAfterSeconds=txt_rec_manager.EXPIRE_SECS)

    def record(self, text, cid):
        """Insert nothing if the length of text is less than 2"""
        cid_ref = self._gid_ref.get_or_record(cid)
        pairs = txt_rec_manager.get_pairs_from_text(text)

        list_to_insert = [ txt_rec_data.init_by_field(cid_ref, pair) for pair in pairs ]

        if len(list_to_insert) > 0:
            self.insert_many(list_to_insert)

    def get_top_used(self, cid, limit=15):
        """
        Return empty list if no data

        Return format = [{ WORD: COUNT }, { WORD: COUNT }, { WORD: COUNT }.....]
        """
        cid_ref = self._gid_ref.get_or_record(cid)

        pipeline = [
            { '$match': { 
                txt_rec_data.CHANNEL_REF: cid_ref 
            } },
            { '$group': {
                '_id': '$' + txt_rec_data.PAIR, 
                txt_rec_manager.RANKING_COUNT_KEY: { "$sum" : 1 }
            } },
            { '$sort': {
                txt_rec_manager.RANKING_COUNT_KEY: pymongo.DESCENDING
            } },
            { '$limit': limit }
        ]

        return list(self.aggregate(pipeline))

    @staticmethod
    def get_pairs_from_text(s):
        s = unicode(s.lower()) # convert case to lower and convert the string to unicode
        s = u"".join([p for p in s.split(u" ") if not p.startswith(u"@")]) # filter LINE tag

        pairs_list = []

        for i in range(len(s) - 1):
            mix = s[i] + s[i + 1]
            if mix.isalpha():
                pairs_list.append(mix)

        return list(set(pairs_list))

    @staticmethod
    def top_used_to_string(result):
        if len(result) > 0:
            return u'\n'.join([u'{}. {} ({}次)'.format(i, data['_id'].replace('\n', '\\n'), data[txt_rec_manager.RANKING_COUNT_KEY]) for i, data in enumerate(result, start=1)])
        else:
            return error.error.main.no_result()

class txt_rec_data(dict_like_mapping):
    """
    {
        channel_ref: INT (ID_REFERENCE),
        pair: STRING,
        timestamp: DATETIME
    }
    """
    CHANNEL_REF = "h"
    PAIR = "p"
    TIMESTAMP = "t"

    @staticmethod
    def init_by_field(channel_id, pair):
        init_dict = {
            txt_rec_data.PAIR: pair,
            txt_rec_data.CHANNEL_REF: channel_id
        }
        return txt_rec_data(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (txt_rec_data.PAIR, txt_rec_data.CHANNEL_REF)):
            raise ValueError(u'Incomplete data. {}'.format(org_dict))

        if txt_rec_data.TIMESTAMP not in org_dict:
            org_dict[txt_rec_data.TIMESTAMP] = datetime.now()
            
        super(txt_rec_data, self).__init__(org_dict)
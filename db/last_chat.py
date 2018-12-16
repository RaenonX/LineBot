# -*- coding: utf-8 -*-
import operator

from datetime import datetime, timedelta

from .base import db_base, dict_like_mapping

class last_chat_recorder(db_base):
    DB_NAME = "group"
    COL_NAME = "last_chat"

    def __init__(self, mongo_client, line_api_client):
        super(last_chat_recorder, self).__init__(mongo_client, last_chat_recorder.DB_NAME, last_chat_recorder.COL_NAME, False, [last_chat_data.GROUP_ID])
        self._line_api = line_api_client

    def update_last_chat(self, group_id, user_id):
        if user_id is None:
            return

        self.update_one({ last_chat_data.GROUP_ID: group_id }, { "$set": { last_chat_data.TIMESTAMP + "." + user_id: datetime.now() } }, True)

    def last_chat_str(self, group_id):
        d = self.find_one({ last_chat_data.GROUP_ID: group_id })

        if d is None:
            s = u'查無資料。'
        else:
            s = u''
            tsd = sorted(last_chat_data(d).timestamps.items(), key=operator.itemgetter(1), reverse=True)

            for uid, ts in tsd:
                u_name = self._line_api.profile_name_safe(uid, cid=group_id)
                ts += timedelta(hours=8)
                time_str = ts.strftime(u'%Y-%m-%d %H:%M:%S')
                s += u'{}: {}\n'.format(u_name, time_str)

            s += u"\n共{}筆資料".format(len(tsd))

        return s

    def get_last_chat_ts(self, gid):
        """Return None is timestamp is not found."""

        d = self.find_one({ last_chat_data.GROUP_ID: gid })

        s = ""

        if d is not None:
            for uid, ts in d[last_chat_data.TIMESTAMP].items():
                s += "{},{}\n".format(uid, ts.strftime('%Y/%m/%d %H:%M:%S'))

        return s

class last_chat_data(dict_like_mapping):
    GROUP_ID = 'gid'
    TIMESTAMP = 'ts'

    @staticmethod
    def init_by_field(group_id):
        init_dict = {
            last_chat_data.GROUP_ID: group_id,
            last_chat_data.TIMESTAMP: {}
        }
        return last_chat_data(init_dict)
        
    def __init__(self, org_dict):
        if not all(k in org_dict for k in (last_chat_data.GROUP_ID, last_chat_data.TIMESTAMP)):
            raise ValueError('Incomplete last_chat_data.')
        
        super(last_chat_data, self).__init__(org_dict)

    @property
    def group_id(self):
        return self[last_chat_data.GROUP_ID]

    @property
    def timestamps(self):
        return self[last_chat_data.TIMESTAMP]
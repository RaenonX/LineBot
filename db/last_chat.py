# -*- coding: utf-8 -*-
import operator

from datetime import datetime, timedelta

from .base import db_base, dict_like_mapping

class last_chat_recorder(db_base):
    DB_NAME = "group"
    COL_NAME = "chat_count"

    def __init__(self, mongo_client, line_api_client):
        super(last_chat_recorder, self).__init__(mongo_client, last_chat_recorder.DB_NAME, last_chat_recorder.COL_NAME, False, [last_chat_data.GROUP_ID])

        self._line_api = line_api_client

    def update_last_chat(self, group_id, user_id):
        if user_id is None:
            return

        self.update_one({ last_chat_data.GROUP_ID: group_id }, { "$push": { last_chat_data.TIMESTAMP + "." + user_id: datetime.now() } ,
                                                                 "$pull": { "$lt": datetime.now() - timedelta(days=7) }}, True)

    def last_chat_str(self, group_id):
        d = self.find_one({ last_chat_data.GROUP_ID: group_id })

        if d is None:
            s = u'查無資料。'
        else:
            sl = 0

            for uid, tss in d[last_chat_data.TIMESTAMP].iteritems():
                len_ = len(filter(lambda t: t + timedelta(days=7) > datetime.now(), tss))
                d[last_chat_data.TIMESTAMP][uid] = len_
                sl += len_

            s = u'總訊息量: {}\n\n'.format(sl)
            tsd = sorted(last_chat_data(d).timestamps.items(), key=operator.itemgetter(1), reverse=True)

            for idx, tse in enumerate(tsd, start=1):
                uid, ct = tse
                u_name = self._line_api.profile_name_safe(uid, cid=group_id)
                s += u'#{:>4d} {:>30} ({}): {} ({:.02f}%)\n'.format(idx, u_name, uid, ct, ct / sl)

            s += u"\n共{}筆資料".format(len(tsd))

        return s

    def get_last_chat_ts_csv_list(self, gid):
        """Return None if timestamp is not found."""

        d = self.find_one({ last_chat_data.GROUP_ID: gid })

        l = []

        if d is not None:
            for uid, tss in d[last_chat_data.TIMESTAMP].items():
                l.append([uid, len(filter(lambda t: t + timedelta(days=7) > datetime.now(), tss))])

            l.append(["Timestamp", (datetime.now() + timedelta(hours=8)).strftime('%Y/%m/%d %H:%M:%S')])

        return l

    def delete_entry(self, gid, uid):
        d = self.find_one({ last_chat_data.GROUP_ID: gid })

        self.update_one({ last_chat_data.GROUP_ID: gid }, { "$unset": { last_chat_data.TIMESTAMP + "." + uid: None } })

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

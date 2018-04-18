# -*- coding: utf-8 -*-

from error import error

from .base import db_base, dict_like_mapping
from .group_manage import msg_type

DB_NAME = "rec"

class member_activity_manager(db_base):
    COLLECTION_NAME = "mem_actv"

    def __init__(self, mongo_client):
        self._cache = {}

        super(member_activity_manager, self).__init__(mongo_client, DB_NAME, member_activity_manager.COLLECTION_NAME)
    
    def record(self, cid, uid, msg_type):
        """record member activity"""
        key = member_activity_manager.get_key(cid, uid)

        if key not in self._cache:
            find_data = self.find_one({ member_activity_manager.CID: cid, member_activity_manager.UID: uid })
            if find_data is None:
                new_data = member_activity_manager.init_by_field(cid, uid)
                new_seq_id = self.insert_one(new_data).inserted_seq_id
                self._cache[key] = new_seq_id
            else:
                self._cache[key] = member_activity_manager(find_data)
        
        return self._cache[cid]

    @staticmethod
    def get_key(cid, uid):
        return u'{}.{}'.format(cid, uid)

class member_activity_data(dict_like_mapping):
    """
    {
        uid: STRING,
        cid: INT - group_ref,
        msg_count:
            { msg_type: int, ... }
        _seq: INT
    }
    """
    UID = "u"
    CID = "c"

    MSG_COUNT = "m"
    
    @staticmethod
    def init_by_field(uid, cid):
        init_dict = {
            member_activity_data.UID: uid,
            member_activity_data.CID: cid,
            member_activity_data.MSG_COUNT: []
        }
        return member_activity_data(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (member_activity_data.UID, member_activity_data.CID, member_activity_data.MSG_COUNT)):
            raise ValueError(u'Incomplete data. {}'.format(org_dict))

        super(member_activity_data, self).__init__(org_dict)

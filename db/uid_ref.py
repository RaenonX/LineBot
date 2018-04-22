# -*- coding: utf-8 -*-

from error import error

from .base import db_base, dict_like_mapping

DB_NAME = "rec"

class user_id_ref_manager(db_base):
    COLLECTION_NAME = "uid_ref"

    NONE_REF = -1

    def __init__(self, mongo_client):
        self._cache = { None: NONE_REF }

        super(user_id_ref_manager, self).__init__(mongo_client, DB_NAME, user_id_ref_manager.COLLECTION_NAME, True)
    
    def get_ref_id_or_record(self, uid):
        """Get user reference id, get -1 if uid is None"""
        if uid not in self._cache:
            find_data = self.find_one({ user_id_ref_data.UID: uid })
            if find_data is None:
                new_data = user_id_ref_data.init_by_field(uid)
                self._cache[uid] = self.insert_one(new_data).inserted_seq_id
            else:
                find_data = user_id_ref_data(find_data)
                self._cache[uid] = find_data.seq_id
        
        return self._cache[uid]

    def get_uid(self, ref_id):
        """Get user id by ref_id, return None if not found"""
        for uid, item in self._cache.iteritems():
            if item == ref_id:
                return uid

        u_data = self.find_one({ user_id_ref_data.SEQUENCE: ref_id })
        if u_data is not None:
            u_data = user_id_ref_data(u_data)
            self._cache[u_data.uid] = u_data
            return u_data.uid

        return None

class user_id_ref_data(dict_like_mapping):
    """
    {
        id: STRING,
        _seq: INT
    }
    """
    UID = "u"
    SEQUENCE = db_base.SEQUENCE
    
    @staticmethod
    def init_by_field(uid):
        init_dict = {
            user_id_ref_data.UID: uid
        }
        return user_id_ref_data(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (user_id_ref_data.UID)):
            raise ValueError(u'Incomplete data. {}'.format(org_dict))

        super(user_id_ref_data, self).__init__(org_dict)

    @property
    def uid(self):
        return self[user_id_ref_data.UID]

    @property
    def seq_id(self):
        return self.get(user_id_ref_data.SEQUENCE, -1)
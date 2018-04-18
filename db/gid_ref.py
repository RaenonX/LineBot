# -*- coding: utf-8 -*-

from .base import db_base, dict_like_mapping

DB_NAME = "rec"

class group_id_ref_manager(db_base):
    COLLECTION_NAME = "gid_ref"

    def __init__(self, mongo_client):
        self._cache = {}

        super(group_id_ref_manager, self).__init__(mongo_client, DB_NAME, group_id_ref_manager.COLLECTION_NAME, True)
    
    def get_or_record(self, cid):
        """Get group reference id"""
        if cid not in self._cache:
            find_data = self.find_one({ group_id_ref_data.CHANNEL_ID: cid })
            if find_data is None:
                new_data = group_id_ref_data.init_by_field(cid)
                new_seq_id = self.insert_one(new_data).inserted_seq_id
                self._cache[cid] = new_seq_id
            else:
                find_data = group_id_ref_data(find_data)
                self._cache[cid] = find_data.seq_id
        
        return self._cache[cid]

class group_id_ref_data(dict_like_mapping):
    """
    {
        channel: STRING,
        _seq: INT
    }
    """
    CHANNEL_ID = "h"
    SEQUENCE = db_base.SEQUENCE
    
    @staticmethod
    def init_by_field(channel_id):
        init_dict = {
            group_id_ref_data.CHANNEL_ID: channel_id
        }
        return group_id_ref_data(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (group_id_ref_data.CHANNEL_ID)):
            raise ValueError(error.error.main.miscellaneous(u'Incomplete data. {}'.format(org_dict)))

        super(group_id_ref_data, self).__init__(org_dict)

    @property
    def seq_id(self):
        return self.get(group_id_ref_data.SEQUENCE, -1)
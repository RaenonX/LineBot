# -*- coding: utf-8 -*-

import pymongo
from .base import db_base, dict_like_mapping, SYSTEM_DATABASE_NAME

class system_config(db_base):
    COLLECTION_NAME = 'config'

    def __init__(self, mongo_client):
        super(system_config, self).__init__(mongo_client, SYSTEM_DATABASE_NAME, system_config.COLLECTION_NAME, False)
        self._cache = None

    def set(self, field_var, setting_bool):
        """Return changed data."""
        if self._cache is None:
            self._set_cache()

        self._cache.set(field_var, setting_bool)
        return config_data(self.find_one_and_update({}, { '$set': self._cache }, None, None, True, pymongo.ReturnDocument.AFTER))

    def get(self, field_var):
        if self._cache is None:
            self._set_cache()

        return self._cache.get(field_var)

    def _set_cache(self):
        data = self.find_one()
        if data is None:
            data = config_data(data)
            self.insert_one(data)
        self._cache = config_data(data)

class config_data(dict_like_mapping):
    SILENCE = 'mute'
    INTERCEPT = 'itc'
    INTERCEPT_DISPLAY_NAME = 'itc_n'
    CALCULATOR_DEBUG = 'calc_dbg'
    REPLY_ERROR = 'rep_err'
    SEND_ERROR_REPORT = 'err_rep'

    def __init__(self, org_dict):
        if org_dict is None:
            org_dict = {
                config_data.SILENCE: False,
                config_data.INTERCEPT: True,
                config_data.CALCULATOR_DEBUG: False,
                config_data.REPLY_ERROR: False,
                config_data.INTERCEPT_DISPLAY_NAME: False,
                config_data.SEND_ERROR_REPORT: True
            }

        if config_data.SILENCE not in org_dict:
            org_dict[config_data.SILENCE] = False
            
        if config_data.INTERCEPT not in org_dict:
            org_dict[config_data.INTERCEPT] = True
            
        if config_data.CALCULATOR_DEBUG not in org_dict:
            org_dict[config_data.CALCULATOR_DEBUG] = False
            
        if config_data.REPLY_ERROR not in org_dict:
            org_dict[config_data.REPLY_ERROR] = False
            
        if config_data.INTERCEPT_DISPLAY_NAME not in org_dict:
            org_dict[config_data.INTERCEPT_DISPLAY_NAME] = False
            
        if config_data.SEND_ERROR_REPORT not in org_dict:
            org_dict[config_data.SEND_ERROR_REPORT] = True

        return super(config_data, self).__init__(org_dict)

    def get(self, field):
        return self[field]

    def set(self, field, value):
        self[field] = value
# -*- coding: utf-8 -*-

import os, sys
import error

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError
import hashlib
from enum import Enum

from .db_base import db_base_obj

class group_ban(db_base_obj):

    def __init__(self, db_query_mgr):
        super(group_ban, self).__init__(db_query_mgr)
        self.id_length = 33
        self.moderator_count = 3



    @property
    def table_structure(self):
        cmd = u'CREATE TABLE group_ban( \
                groupId VARCHAR(33) PRIMARY KEY, \
                silence BOOLEAN NOT NULL DEFAULT FALSE, \
                admin VARCHAR(33) NOT NULL, \
                admin_sha VARCHAR(56) NOT NULL, \
                moderator1 VARCHAR(33), \
                moderator1_sha VARCHAR(56), \
                moderator2 VARCHAR(33), \
                moderator2_sha VARCHAR(56), \
                moderator3 VARCHAR(33), \
                moderator3_sha VARCHAR(56));'
        return cmd

    def new_data(self, groupId, adminUID, key_for_admin):
        if len(adminUID) != self.id_length or len(groupId) != self.id_length:
            return False
        else:
            try:
                cmd = u'INSERT INTO group_ban(groupId, silence, admin, admin_sha) VALUES(%(id)s, FALSE, %(adm)s, %(key)s)'
                cmd_dict = {'id': groupId, 'adm': adminUID, 'key': key_for_admin}
                self.sql_cmd(cmd, cmd_dict)
                return True
            except IntegrityError as ex:
                return False

    def del_data(self, groupId):
        if len(groupId) != self.id_length:
            return error.error.main.invalid_length(u'群組/房間ID', self.id_length)
        else:
            cmd = u'DELETE FROM group_ban WHERE groupid = %(gid)s'
            cmd_dict = {'gid': groupId}
            self.sql_cmd(cmd, cmd_dict)
            return True

    def get_group_by_id(self, groupId):
        cmd = u'SELECT * FROM group_ban WHERE groupId = %(gid)s'
        cmd_dict = {'gid': groupId}
        result = self.sql_cmd(cmd, cmd_dict)
        return result[0] if result is not None else None

    def set_silence(self, groupId, set, key):
        if len(groupId) != self.id_length:
            return error.error.main.invalid_length(u'群組/房間ID', 33)
        cmd_check = u'SELECT * FROM group_ban WHERE (admin_sha = %(key)s OR \
                                                    moderator1_sha = %(key)s OR \
                                                    moderator2_sha = %(key)s OR \
                                                    moderator3_sha = %(key)s) AND \
                                                    groupId = %(gid)s'
        cmd_check_dict = {'key': hashlib.sha224(key).hexdigest(), 
                          'gid': groupId}
        results = self.sql_cmd(cmd_check, cmd_check_dict)
        if results is not None:
            cmd = u'UPDATE group_ban SET silence = %(set)s WHERE groupId = %(id)s'
            cmd_dict = {'id': groupId, 'set': set}
            self.sql_cmd(cmd, cmd_dict)
            return True
        else:
            return error.error.main.incorrect_password_or_insufficient_permission()

    def change_admin(self, groupId, newAdminUID, key, newkey):
        if len(newAdminUID) != self.id_length or len(groupId) != self.id_length:
            return error.error.main.invalid_length(u'群組/房間ID 或 管理員UID', 33)
        cmd_check = u'SELECT * FROM group_ban WHERE admin_sha = %(key)s AND groupId = %(gid)s'
        cmd_check_dict = {'key': hashlib.sha224(key).hexdigest(),
                          'gid': groupId}
        results = self.sql_cmd(cmd_check, cmd_check_dict)

        if results is not None:
            cmd = u'UPDATE group_ban SET admin = %(adm)s, admin_sha = %(sha)s WHERE groupId = %(id)s'
            cmd_dict = {'id': groupId, 'adm': newAdminUID, 'sha': hashlib.sha224(newkey).hexdigest()}
            self.sql_cmd(cmd, cmd_dict)
            return True
        else:
            return error.error.main.incorrect_password_or_insufficient_permission()

    def set_mod1(self, groupId, newModUID, key, newkey):
        return self._set_moderator(groupId, 1, newModUID, key, newkey)

    def set_mod2(self, groupId, newModUID, key, newkey):
        return self._set_moderator(groupId, 2, newModUID, key, newkey)

    def set_mod3(self, groupId, newModUID, key, newkey):
        return self._set_moderator(groupId, 3, newModUID, key, newkey)

    def _set_moderator(self, groupId, moderator_pos, newModUID, key, newkey):
        """
        newModUID + newkey set to None to delete moderator
        """
        if len(groupId) != self.id_length:
            return error.error.main.invalid_length(u'群組/房間ID', self.id_length)

        if newModUID is None and newkey is None:
            delete_mod = True
        else:
            if len(newModUID) != self.id_length:
                return error.error.main.invalid_length(u'管理員UID', self.id_length)
            elif moderator_pos > 3 or moderator_pos < 0:
                return error.error.main.invalid_thing(u'副管位置序號', moderator_pos)
            delete_mod = False

        mod_col_dict = {1: 'moderator1', 2: 'moderator2', 3: 'moderator3'}
        mod_sha_dict = {1: 'moderator1_sha', 2: 'moderator2_sha', 3: 'moderator3_sha'}

        cmd_check = u'SELECT * FROM group_ban WHERE (admin_sha = %(key)s OR {} = %(key)s) AND groupId = %(gid)s'.format(mod_sha_dict[moderator_pos])
        cmd_check_dict = {'key': hashlib.sha224(key).hexdigest(),
                          'gid': groupId}
        results = self.sql_cmd(cmd_check, cmd_check_dict)
        
        if results is not None:
            cmd = u'UPDATE group_ban SET {} = %(mod)s, {} = %(newkey)s WHERE groupId = %(id)s'.format(mod_col_dict[moderator_pos],
                                                                                                      mod_sha_dict[moderator_pos])
            cmd_dict = {'id': groupId, 
                        'mod': None if delete_mod else newModUID, 
                        'newkey': None if delete_mod else hashlib.sha224(newkey).hexdigest()}
            self.sql_cmd(cmd, cmd_dict)
            return True
        else:
            return error.error.main.incorrect_password_or_insufficient_permission()



    def is_group_set_to_silence(self, groupId):
        group = self.get_group_by_id(groupId)
        if group is not None:
            return group[int(gb_col.silence)]

class gb_col(Enum):
    groupId = 0
    silence = 1
    admin = 2
    admin_sha = 3
    moderator1 = 4
    moderator1_sha = 5
    moderator2 = 6
    moderator2_sha = 7
    moderator3 = 8
    moderator3_sha = 9

    def __int__(self):
        return self.value
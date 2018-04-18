# -*- coding: utf-8 -*-

import os, sys

import urlparse
from datetime import datetime
import hashlib
import pymongo

import error
import ext, tool, bot

from .base import db_base, dict_like_mapping
from .misc import PackedStringResult

GROUP_DB_NAME = 'group'

############
### ENUM ###
############

class group_data_range(ext.EnumWithName):
    SILENCE = 0, '啞巴'
    SYS_ONLY = 1, '機器人'
    GROUP_DATABASE_ONLY = 2, '服務員'
    ALL = 3, '八嘎囧'

class msg_type(ext.EnumWithName):
    UNKNOWN = -1, '不明'
    TEXT = 0, '文字'
    STICKER = 1, '貼圖'
    PICTURE = 2, '圖片'
    VIDEO = 3, '影片'
    AUDIO = 4, '音訊'
    LOCATION = 5, '位置'
    FILE = 6, '檔案'

###############################
### GROUP MANAGING INSTANCE ###
###############################

class group_manager(db_base):
    ID_LENGTH = 33

    def __init__(self, mongo_client):
        super(group_manager, self).__init__(mongo_client, GROUP_DB_NAME, self.__class__.__name__, False, [group_data.GROUP_ID])

        self._activator = group_activator(mongo_client)
        self._permission_manager = user_data_manager(mongo_client)

        self._cache_config = {}
        self._cache_permission = {}

        self._ADMIN_UID = os.getenv('ADMIN_UID', None)
        if self._ADMIN_UID is None:
            print 'Specify bot admin uid as environment variable "ADMIN_UID".'
            sys.exit(1)

    # utilities - misc
    def new_data(self, gid, config=group_data_range.GROUP_DATABASE_ONLY):
        """Return result none if creation failed, else return token to activate accepting public database if config is not set to public."""
        if len(gid) != group_manager.ID_LENGTH:
            return
        else:
            try:
                if bot.line_api_wrapper.is_valid_user_id(gid):
                    config = group_data_range.ALL

                data = group_data.init_by_field(gid, config)
                self.insert_one(data)
                self._permission_manager.new_data(gid, self._ADMIN_UID, self._ADMIN_UID, bot.permission.BOT_ADMIN)
                if bot.line_api_wrapper.is_valid_room_group_id(gid):
                    return self._activator.new_data(gid)
            except pymongo.errors.DuplicateKeyError as ex:
                return

    def activate(self, gid, token):
        """Return boolean to indicate activation result."""
        group_activated = self._activator.del_data(gid, token)
        if group_activated:
            self.find_one_and_update({ group_data.GROUP_ID: gid }, { '$set': { group_data.CONFIG_TYPE: group_data_range.ALL } })

        return group_activated
            
    # utilities - group settings related
    def get_group_by_id(self, gid, including_member_data=False):
        """Return None if nothing found"""
        if len(gid) != group_manager.ID_LENGTH:
            return None
        
        try:
            result = self.find_one({ group_data.GROUP_ID: gid })
            if result is None:
                return None
            else:
                g_data = group_data(result)
                if including_member_data:
                    admins_list = self._permission_manager.get_data_by_permission(gid, bot.permission.ADMIN)
                    mods_list = self._permission_manager.get_data_by_permission(gid, bot.permission.MODERATOR)
                    restricts_list = self._permission_manager.get_data_by_permission(gid, bot.permission.RESTRICTED)
                    g_data.set_members_data(admins_list, mods_list, restricts_list)

                return g_data
        except pymongo.errors.PyMongoError as ex:
            print ex
            raise ex

    def set_config_type(self, gid, config_type):
        """Return true if success, else return error message in string."""

        if len(gid) != group_manager.ID_LENGTH:
            return error.error.line_bot_api.illegal_room_group_id(gid)

        filter_dict = { group_data.GROUP_ID: gid }

        setup_result = self.find_one_and_update(filter_dict, { '$set': { group_data.CONFIG_TYPE: config_type } }, None, None, False, pymongo.ReturnDocument.AFTER)

        if setup_result is not None:
            self._set_cache_config(gid, config_type)
            return True
        else:
            return error.error.main.incorrect_password_or_insufficient_permission()
        
    # utilities - group permission related
    def set_permission(self, gid, setter_uid, target_uid, permission_lv):
        """Raise InsufficientPermissionError if action is not allowed."""
        self._permission_manager.set_permission(gid, setter_uid, target_uid, permission_lv)

    def delete_permission(self, gid, setter_uid, target_uid):
        """Raise InsufficientPermissionError if action is not allowed."""
        self._permission_manager.del_data(gid, setter_uid, target_uid)

    def get_group_config_type(self, gid):
        cfg_type = self._get_cache_config(gid)
        if cfg_type is not None:
            return cfg_type
        else:
            group = self.get_group_by_id(gid)
            if group is not None:
                cfg_type = group.config_type
                self._set_cache_config(gid, group.config_type)
                return cfg_type
            else:
                add = self.new_data(gid)
                if add is not None:
                    return self.get_group_config_type(gid)
                else:
                    return group_data_range.GROUP_DATABASE_ONLY

    def get_user_permission(self, gid, uid):
        if uid == self._ADMIN_UID:
            return bot.permission.BOT_ADMIN

        user_data = self._permission_manager.get_user_data(gid, uid)
        if user_data is not None:
            u_permission = user_data.permission_level
        else:
            u_permission = bot.permission.USER
        return u_permission
        
    def get_user_owned_permissions(self, uid):
        """This will not use cache."""
        return self._permission_manager.get_user_owned_permissions(uid)
        
    # utilities - activity tracking
    def log_message_activity(self, chat_instance_id, rcv_type_enum, rep_type_enum=None, rcv_count=1, rep_count=1):
        if len(chat_instance_id) != group_manager.ID_LENGTH:
            raise ValueError(error.error.main.incorrect_thing_with_correct_format(u'頻道ID', u'33字元長度', chat_instance_id))
        else:
            inc_dict = {}
            if rep_type_enum is not None:
                inc_dict[group_data.MESSAGE_RECORDS + '.' + msg_stats_data.REPLY + '.' + str(rep_type_enum)] = rep_count
                triggered = True
            else:
                triggered = False

            root_field = group_data.MESSAGE_RECORDS + '.' + msg_stats_data.RECEIVE + '.' + str(rcv_type_enum) + '.'

            inc_dict[root_field + (msg_stats_pair.TRIGGERED if triggered else msg_stats_pair.NOT_TRIGGERED)] = rcv_count 
            inc_dict[root_field + (msg_stats_pair.NOT_TRIGGERED if triggered else msg_stats_pair.TRIGGERED)] = 0 

            result = self.update_one({ group_data.GROUP_ID: chat_instance_id },
                                     { '$inc': inc_dict }, False)
            if result.matched_count < 1:
                self.new_data(chat_instance_id)

    # statistics - message track
    def message_sum(self):
        group_dict = { '_id': None }
        for type_enum in list(msg_type):
            for k in (msg_stats_pair.TRIGGERED, msg_stats_pair.NOT_TRIGGERED):
                group_dict[msg_stats_data.RECEIVE + '_' + str(type_enum) + '_' + k] = { '$sum': '$' + group_data.MESSAGE_RECORDS + '.' + msg_stats_data.RECEIVE + '.' + str(type_enum) + '.' + k }
            group_dict[msg_stats_data.REPLY + '_' + str(type_enum)] = { '$sum': '$' + group_data.MESSAGE_RECORDS + '.' + msg_stats_data.REPLY + '.' + str(type_enum) }

        project_dict = {
            msg_stats_data.RECEIVE: { str(type_enum): { k: '$' + msg_stats_data.RECEIVE + '_' + str(type_enum) + '_' + k for k in (msg_stats_pair.TRIGGERED, msg_stats_pair.NOT_TRIGGERED) } for type_enum in list(msg_type) },
            msg_stats_data.REPLY: { str(type_enum): '$' + msg_stats_data.REPLY + '_' + str(type_enum) for type_enum in list(msg_type) }
        }

        aggr_result = list(self.aggregate([
            { '$group': group_dict },
            { '$project': project_dict }
        ]))
        if len(aggr_result) > 0:
            return msg_stats_data(aggr_result[0])
        else:
            return msg_stats_data.empty_init()
        
    def order_by_recorded_msg_count(self, limit=None):
        """Sort by COUNT OF RECEIVED MESSAGES"""

        RECEIVED_MESSAGES = 'rcv_sum'

        aggr_pipeline = [
            { '$addFields': { RECEIVED_MESSAGES: { '$sum': [ '$' + group_data.MESSAGE_RECORDS + '.' + msg_stats_data.RECEIVE + '.' + str(type_enum) + '.' + k for k in (msg_stats_pair.TRIGGERED, msg_stats_pair.NOT_TRIGGERED) for type_enum in list(msg_type) ] } } }, 
            { '$sort': { RECEIVED_MESSAGES: pymongo.DESCENDING } }
        ]

        if limit is not None and isinstance(limit, (int, long)):
            aggr_pipeline.append({ '$limit': limit })

        aggr_result = list(self.aggregate(aggr_pipeline))
        if len(aggr_result) > 0:
            return [group_data(data) for data in aggr_result]
        else:
            return []

    # private
    def _set_cache_config(self, gid, cfg_type):
        self._cache_config[gid] = cfg_type
    
    def _get_cache_config(self, gid):
        """Return none if key not exists"""
        return self._cache_config.get(gid, None)
        
    @staticmethod
    def message_track_string(group_data_or_list, limit=None, append_first_list=None, no_result_text=None, including_channel_id=True, insert_ranking=False, sum_msg_data=None):
        if group_data_or_list is not None and len(group_data_or_list) > 0:
            if not isinstance(group_data_or_list, list):
                group_data_or_list = [group_data_or_list]

            has_msg_sum_stats_int = int(sum_msg_data is not None)

            if has_msg_sum_stats_int == 1:
                group_data_or_list = [sum_msg_data] + group_data_or_list

            def format_string(data):
                text = u''

                if isinstance(data, msg_stats_data):
                    stats_data = data
                else:
                    data = group_data(data)
                    gid = data.group_id

                    if gid.startswith('U'):
                        activation_status = u'私訊頻道'
                    else:
                        activation_status = unicode(data.config_type)

                    if including_channel_id:
                        text += u'頻道ID: {} 【{}】\n'.format(gid, activation_status)

                    stats_data = msg_stats_data(data.message_track_record)

                text += stats_data.get_string()
                return text

            return PackedStringResult.init_by_field(group_data_or_list, format_string, limit, append_first_list, no_result_text, u'\n\n', insert_ranking, has_msg_sum_stats_int)
        else:
            err = error.main.miscellaneous(u'沒有輸入群組資料。')
            return PackedStringResult([err], [err])

class group_data(dict_like_mapping):
    """
    {
        group_id: STRING - INDEX,
        config_type: CONFIG_TYPE
        message_records: {
            receive: {
                (MSG_TYPE): MSG_STATS_PAIR
                ...
                ...
            },
            reply: {
                (MSG_TYPE): INTEGER
                ...
                ...
            }
        },
        ===NO DATA ON INIT===
        mem: {
            admin: [ STRING, STRING, STRING... ],
            moderators: [ STRING, STRING, STRING... ],
            restricts: [ STRING, STRING, STRING... ]
        }
    }
    """
    GROUP_ID = 'group_id'

    SPECIAL_USER = 'mem'
    ADMINS = 'admins'
    MODERATORS = 'mods'
    RESTRICTS = 'rst'

    CONFIG_TYPE = 'config_type'

    MESSAGE_RECORDS = 'msg_rec'

    @staticmethod
    def init_by_field(gid, config_type):
        init_dict = {
            group_data.GROUP_ID: gid,
            group_data.CONFIG_TYPE: config_type,
            group_data.MESSAGE_RECORDS: msg_stats_data.empty_init(),
            group_data.SPECIAL_USER: { 
                group_data.ADMINS: [],
                group_data.MODERATORS: [],
                group_data.RESTRICTS: []
            }
        }

        return group_data(init_dict)

    def __init__(self, org_dict):
        if org_dict is not None:
            if not all(k in org_dict for k in (group_data.GROUP_ID, group_data.SPECIAL_USER, group_data.CONFIG_TYPE)):
                raise ValueError('Invalid group data dictionary.')

            if org_dict[group_data.SPECIAL_USER] is None:
                org_dict[group_data.SPECIAL_USER] = { 
                    group_data.ADMINS: [],
                    group_data.MODERATORS: [],
                    group_data.RESTRICTS: []
                }
            else:
                for k in (group_data.ADMINS, group_data.MODERATORS, group_data.RESTRICTS):
                    if org_dict[group_data.SPECIAL_USER].get(k, None) is None:
                        org_dict[group_data.SPECIAL_USER][k] = []

            org_dict[group_data.MESSAGE_RECORDS] = msg_stats_data(org_dict[group_data.MESSAGE_RECORDS])
        else:
            raise ValueError('Dictionary is None.')
        return super(group_data, self).__init__(org_dict)

    def set_members_data(self, admins_list, mods_list, restricts_list):
        self[group_data.SPECIAL_USER][group_data.ADMINS] = admins_list
        self[group_data.SPECIAL_USER][group_data.MODERATORS] = mods_list
        self[group_data.SPECIAL_USER][group_data.RESTRICTS] = restricts_list

    @property
    def has_member_data(self):
        return self._members_data_set

    def get_status_string(self):
        message_track_string = group_manager.message_track_string(self, None, None, None, False).limited
        admins_string = self.get_group_members_string()

        text = u'房間/群組ID: {}\n'.format(self.group_id)
        text += u'自動回覆設定: {}\n'.format(unicode(self.config_type))
        text += u'【訊息量紀錄】\n{}\n'.format(message_track_string)
        text += u'【管理員列表】\n{}'.format(admins_string)

        return text

    def get_group_members_string(self):
        admin_arr = self[group_data.SPECIAL_USER][group_data.ADMINS]
        mod_arr = self[group_data.SPECIAL_USER][group_data.MODERATORS]
        ban_arr = self[group_data.SPECIAL_USER][group_data.RESTRICTS]
        text = u'管理員({}人):\n{}'.format(len(admin_arr), '\n'.join([data.user_id for data in admin_arr]))
        text += u'\n副管({}人):\n{}'.format(len(mod_arr), '\n'.join([data.user_id for data in mod_arr]))
        text += u'\n限制用戶({}人):\n{}'.format(len(ban_arr), '\n'.join([data.user_id for data in ban_arr]))

        return text

    @property
    def group_id(self):
        return self[group_data.GROUP_ID]

    @property
    def config_type(self):
        return group_data_range(self[group_data.CONFIG_TYPE])
        
    @property
    def message_track_record(self):
        return self[group_data.MESSAGE_RECORDS]

########################
### TOKEN ACTIVATION ###
########################

class group_activator(db_base):
    ID_LENGTH = 33
    ACTIVATE_TOKEN_LENGTH = 40
    DATA_EXPIRE_SECS = 24 * 60 * 60

    def __init__(self, mongo_client):
        super(group_activator, self).__init__(mongo_client, GROUP_DB_NAME, self.__class__.__name__, False, [group_data.GROUP_ID])
        self.create_index([(group_activation_data.TIMESTAMP, pymongo.DESCENDING)], expireAfterSeconds=group_activator.DATA_EXPIRE_SECS)

    def new_data(self, group_id):
        """Return token string."""
        new_token = tool.random_drawer.generate_random_string(group_activator.ACTIVATE_TOKEN_LENGTH)
        self.insert_one(group_activation_data.init_by_field(group_id, new_token))
        return new_token

    def del_data(self, group_id, token):
        """Return data deleted count > 0"""
        return self.delete_many({ group_data.GROUP_ID: group_id, group_activation_data.TOKEN: token }).deleted_count > 0

class group_activation_data(dict_like_mapping):
    """
    {
        group_id: STRING - INDEX,
        token: STRING,
        timestamp: DATETIME
    }
    """
    TOKEN = 'token'
    TIMESTAMP = 'ts'

    @staticmethod
    def init_by_field(group_id, token):
        init_dict = {
            group_data.GROUP_ID: group_id,
            group_activation_data.TOKEN: token,
            group_activation_data.TIMESTAMP: datetime.now()
        }
        return group_activation_data(init_dict)
        
    def __init__(self, org_dict):
        if not all(k in org_dict for k in (group_data.GROUP_ID, group_activation_data.TOKEN)):
            raise ValueError('Incomplete user data.')

        if group_activation_data.TIMESTAMP not in org_dict:
            self[group_activation_data.TIMESTAMP] = datetime.now()
        
        super(group_activation_data, self).__init__(org_dict)

    @property
    def token(self):
        return self[group_activation_data.TOKEN]

    @property
    def group_id(self):
        return self[group_activation_data.GROUP_ID]

##########################
### MESSAGE STATISTICS ###
##########################

class msg_stats_data(dict_like_mapping):
    """
    {
        receive: {
            (MSG_TYPE): MSG_STATS_PAIR
            ...
            ...
        },
        reply: {
            (MSG_TYPE): INTEGER
            ...
            ...
        }
    }
    """
    RECEIVE = 'rcv'
    REPLY = 'rpl'
    CHAT_INSTANCE_ID = 'cid'

    @staticmethod
    def empty_init():
        init_dict = {
            msg_stats_data.RECEIVE: {str(msg_type_iter): msg_stats_pair.empty_init() for msg_type_iter in list(msg_type)},
            msg_stats_data.REPLY: {str(msg_type_iter): 0 for msg_type_iter in list(msg_type)}
        }

        return msg_stats_data(init_dict)

    def __init__(self, org_dict):
        if org_dict is not None:
            key_check_list = [msg_stats_data.RECEIVE, msg_stats_data.REPLY]
            
            if not msg_stats_data.RECEIVE in org_dict:
                org_dict[msg_stats_data.RECEIVE] = {str(msg_type_iter): msg_stats_pair.empty_init() for msg_type_iter in list(msg_type)}

            if not msg_stats_data.REPLY in org_dict:
                org_dict[msg_stats_data.REPLY] = {str(msg_type_iter): 0 for msg_type_iter in list(msg_type)}
        else:
            raise ValueError('Dictionary is none.')

        return super(msg_stats_data, self).__init__(org_dict)

    @property
    def reply(self):
        return self[msg_stats_data.REPLY]
        
    @property
    def received(self):
        return { key: msg_stats_pair(data) for key, data in self[msg_stats_data.RECEIVE].iteritems() } 
        
    @property
    def chat_instance_id(self):
        return self.get(msg_stats_data.CHAT_INSTANCE_ID, None)

    def get_string(self):
        text = u'收到:\n{}'.format('\n'.join(u'{} - 未觸發{} 觸發{}'.format(type_string, pair.not_triggered, pair.triggered) for type_string, pair in self.received.iteritems()))
        text += u'\n回覆:\n{}'.format('\n'.join(u'{} - {}'.format(type_string, count) for type_string, count in self.reply.iteritems()))
        return text

class msg_stats_pair(dict_like_mapping):
    """
    {
        triggered: INTEGER,
        not_triggered: INTEGER
    }
    """
    TRIGGERED = 'trig'
    NOT_TRIGGERED = 'xtrig'

    @staticmethod
    def empty_init():
        init_dict = {
            msg_stats_pair.TRIGGERED: 0, 
            msg_stats_pair.NOT_TRIGGERED: 0
        }
        return msg_stats_pair(init_dict)

    def __init__(self, org_dict):
        if org_dict is not None:
            if all(k in org_dict for k in (msg_stats_pair.TRIGGERED, msg_stats_pair.NOT_TRIGGERED)):
                pass
            else:
                raise ValueError('Incomplete data.')
        else:
            raise ValueError('Dictionary is none.')

        super(msg_stats_pair, self).__init__(org_dict)

    @property
    def triggered(self):
        return self[msg_stats_pair.TRIGGERED]

    @property
    def not_triggered(self):
        return self[msg_stats_pair.NOT_TRIGGERED]

##########################
### PERMISSION RELATED ###
##########################

class user_data_manager(db_base):
    COLLECTION_NAME = 'user_data'

    def __init__(self, mongo_client):
        super(user_data_manager, self).__init__(mongo_client, GROUP_DB_NAME, user_data_manager.COLLECTION_NAME, False)
        self._ADMIN_UID = os.getenv('ADMIN_UID', None)
        if self._ADMIN_UID is None:
            print 'Specify bot admin uid as environment variable "ADMIN_UID".'
            sys.exit(1)
        self._cache = {}

    def new_data(self, group_id, setter_uid, target_uid, target_permission_lv):
        """
        Set setter_uid and target_uid to exact same to bypass permission check.

        Raise InsufficientPermissionError if action is not allowed.
        """
        if not bot.line_api_wrapper.is_valid_room_group_id(group_id) and not bot.line_api_wrapper.is_valid_user_id(group_id):
            raise ValueError(u'Illegal group_id. ({})'.format(group_id))

        if setter_uid == target_uid or self._check_action_is_allowed(setter_uid, group_id, target_permission_lv):
            new_user_data = user_data.init_by_field(target_uid, group_id, target_permission_lv)
            self._set_cache(group_id, new_user_data)
            self.insert_one(new_user_data)
        else:
            raise InsufficientPermissionError()

    def del_data(self, group_id, setter_uid, target_uid):
        """
        Raise InsufficientPermissionError if action is not allowed.
        """
        target_data = self.get_user_data(group_id, target_uid)
        if target_data is not None:
            target_permission_lv = target_data.permission_level
        else:
            target_permission_lv = bot.permission.USER

        if self._check_action_is_allowed(setter_uid, group_id, target_permission_lv):
            self.delete_one({ user_data.USER_ID: target_uid, user_data.GROUP: group_id })
            self._del_cache(group_id, target_uid)
        else:
            raise InsufficientPermissionError()

    def set_permission(self, group_id, setter_uid, target_uid, new_lv):
        """Raise InsufficientPermissionError if action is not allowed."""
        if not bot.line_api_wrapper.is_valid_room_group_id(group_id):
            return

        if self._check_action_is_allowed(setter_uid, group_id, new_lv):
            updated_data = self.find_one_and_update({ user_data.USER_ID: target_uid, user_data.GROUP: group_id },
                                                    { '$set': { user_data.PERMISSION_LEVEL: new_lv } }, None, None, True, pymongo.ReturnDocument.AFTER)
            self._set_cache(group_id, user_data.init_by_field(target_uid, group_id, new_lv))
        else:
            raise InsufficientPermissionError()

    def get_user_data(self, group_id, uid):
        """Return None if nothing found."""
        result = self._get_cache_by_id(group_id, uid)
        if result is None:
            return None
        else:
            return user_data(result)

    def get_user_owned_permissions(self, uid):
        """Return Empty array if nothing found, else array of user_data."""
        user_permission_data = list([user_data(data) for data in self.find({ user_data.USER_ID: uid }).sort([( user_data.GROUP, pymongo.ASCENDING )])])
        for data in user_permission_data:
            self._set_cache(data.group, data)
        return user_permission_data

    def get_data_by_permission(self, group_id, permission_lv):
        return self._get_cache_by_permission(group_id, permission_lv)

    def _check_action_is_allowed(self, uid, group_id, action_permission):
        if uid == self._ADMIN_UID:
            return True

        u_data = self._get_cache_by_id(group_id, uid)
        if u_data is not None:
            u_data = user_data(u_data)

            # Need moderator+ to set restricted
            if action_permission < bot.permission.USER:
                return u_data.permission_level >= bot.permission.MODERATOR
            else:
                return u_data.permission_level >= action_permission
        else:
            return False

    def _set_cache(self, group_id, new_user_data):
        uid = new_user_data[user_data.USER_ID]
        if group_id in self._cache:
            self._cache[group_id][uid] = new_user_data
        else:
            self._cache[group_id] = { uid: new_user_data }

    def _del_cache(self, group_id, uid):
        if group_id in self._cache and uid in self._cache[group_id]:
            del self._cache[group_id][uid]

    def _get_cache_by_id(self, group_id, user_id):
        if group_id in self._cache and user_id in self._cache[group_id]:
            return self._cache[group_id][user_id]
        else:
            u_data = self.find_one({ user_data.GROUP: group_id, user_data.USER_ID: user_id })
            if u_data is not None:
                self._set_cache(group_id, user_data(u_data))
                return self._get_cache_by_id(group_id, user_id)
            else:
                self._set_cache(group_id, user_data.init_by_field(user_id, group_id, bot.permission.USER))
                return self._get_cache_by_id(group_id, user_id)

    def _get_cache_by_permission(self, group_id, permission_lv):
        if group_id in self._cache:
            return list(user_data(item) for item in self._cache[group_id].itervalues() if item[user_data.PERMISSION_LEVEL] == permission_lv and item[user_data.GROUP] == group_id)
        else:
            find_data = list(self.find({ user_data.GROUP: group_id }))
            if len(find_data) > 0:
                for data in find_data:
                    self._set_cache(group_id, data)
                return self._get_cache_by_permission(group_id, permission_lv)
            else:
                return []

class user_data(dict_like_mapping):
    """
    {
        user_id: STRING - INDEX,
        group: STRING,
        permission_level: INTEGER
    }
    """
    USER_ID = 'uid'
    GROUP = 'grp'
    PERMISSION_LEVEL = 'perm'

    @staticmethod
    def init_by_field(uid, group_id, permission_lv):
        init_dict = {
            user_data.USER_ID: uid,
            user_data.GROUP: group_id,
            user_data.PERMISSION_LEVEL: bot.permission(permission_lv)
        }
        return user_data(init_dict)

    def __init__(self, org_dict):
        if org_dict is not None:
            if not all(k in org_dict for k in (user_data.USER_ID, user_data.PERMISSION_LEVEL, user_data.GROUP)):
                raise ValueError(u'Incomplete user data.')
        else:
            raise ValueError(u'Dict is none.')

        return super(user_data, self).__init__(org_dict)

    @property
    def user_id(self):
        return self[user_data.USER_ID]

    @property
    def permission_level(self):
        return bot.permission(self[user_data.PERMISSION_LEVEL])

    @property
    def group(self):
        return self[user_data.GROUP]

class InsufficientPermissionError(Exception):
    def __init__(self, *args):
        return super(InsufficientPermissionError, self).__init__(*args)
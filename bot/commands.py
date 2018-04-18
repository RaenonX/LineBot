# -*- coding: utf-8 -*-

import ext

class permission(ext.EnumWithName):
    RESTRICTED = -1, '限制用戶'
    USER = 0, '一般用戶'
    MODERATOR = 1, '副管理員'
    ADMIN = 2, '管理員'
    BOT_ADMIN = 3, '機器人管理員'

class remote(ext.EnumWithName):
    NOT_AVAILABLE = 0, '不可用'
    GROUP_ID_ONLY = 1, '限群組ID'
    ALLOW_PUBLIC = 2, '可控公群'
    ALLOW_GLOBAL = 3, '可控全域'
    ALLOW_ALL = 4, '可控公群/全域'

    @staticmethod
    def PUBLIC_TOKEN():
        return 'PUBLIC'

    @staticmethod
    def GLOBAL_TOKEN():
        return 'GLOBAL'

class command_object(object):
    def __init__(self, headers, function_code, remotable, lowest_permission_req=permission.USER):
        self._function_code = function_code
        self._headers = [function_code + u'\n'] + ext.to_list(headers)
        self._remotable = remotable
        self._lowest_permission_required = lowest_permission_req

    @property
    def headers(self):
        """Headers of the command. (list)"""
        return self._headers

    @property
    def remotable(self):
        return self._remotable

    @property
    def lowest_permission(self):
        """Required Permission"""
        return self._lowest_permission_required

    @property
    def function_code(self):
        """Code of function"""
        return self._function_code

# Provide lowest permission requirement, if some command requires higher permission, handle inside txt msg handling function.
sys_cmd_dict = { u'記住': command_object([u'記住', u'AA\n'], u'A', remote.ALLOW_ALL), 
                 u'置頂': command_object([u'置頂', u'MM\n'], u'M', remote.GROUP_ID_ONLY, permission.MODERATOR), 
                 u'忘記': command_object(u'忘記', u'D', remote.ALLOW_ALL), 
                 u'忘記置頂': command_object(u'忘記置頂', u'R', remote.ALLOW_ALL), 
                 u'找': command_object(u'找', u'Q', remote.ALLOW_ALL), 
                 u'詳細找': command_object(u'詳細找', u'I', remote.ALLOW_ALL), 
                 u'修改': command_object(u'修改', u'E', remote.ALLOW_ALL), 
                 u'複製': command_object(u'複製', u'X', remote.NOT_AVAILABLE), 
                 u'清除': command_object(u'清除', u'X2', remote.NOT_AVAILABLE, permission.ADMIN), 
                 u'群組': command_object(u'群組', u'G', remote.ALLOW_ALL), 
                 u'當': command_object(u'當', u'GA', remote.GROUP_ID_ONLY), 
                 u'讓': command_object(u'讓', u'GA2', remote.GROUP_ID_ONLY), 
                 u'啟用': command_object(u'啟用', u'GA3', remote.GROUP_ID_ONLY), 
                 u'頻道': command_object(u'頻道', u'H', remote.NOT_AVAILABLE), 
                 u'系統': command_object(u'系統', u'P', remote.ALLOW_ALL), 
                 u'使用者': command_object(u'使用者', u'P2', remote.GROUP_ID_ONLY),
                 u'排名': command_object(u'排名', u'K', remote.ALLOW_ALL), 
                 u'最近的': command_object(u'最近的', u'L', remote.GROUP_ID_ONLY), 
                 u'匯率': command_object(u'匯率', u'C', remote.NOT_AVAILABLE), 
                 u'貼圖': command_object(u'貼圖', u'STK', remote.NOT_AVAILABLE), 
                 u'查': command_object(u'查', u'O', remote.NOT_AVAILABLE), 
                 u'抽': command_object(u'抽', u'RD', remote.NOT_AVAILABLE), 
                 u'轉': command_object(u'轉', u'T', remote.NOT_AVAILABLE), 
                 u'DB': command_object(u'DB', u'S', remote.NOT_AVAILABLE, permission.ADMIN), 
                 u'運勢預估': command_object(u'運勢預估', u'LUK', remote.NOT_AVAILABLE),
                 u'天氣': command_object(u'天氣', u'W', remote.NOT_AVAILABLE), 
                 u'下載': command_object(u'下載', u'DL', remote.NOT_AVAILABLE), 
                 u'公告': command_object(u'公告', u'F', remote.GROUP_ID_ONLY, permission.MODERATOR) }

game_cmd_dict = { u'猜拳': command_object(u'猜拳', u'RPS', remote.NOT_AVAILABLE) } 

class CommandNotExistException(Exception):
    def __init__(self, *args):
        return super(CommandNotExistException, self).__init__(*args)
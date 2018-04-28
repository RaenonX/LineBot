# -*- coding: utf-8 -*-

import ext

from .param_base import param_packer_base, parameter, param_validator, UndefinedCommandCategoryException

class param_packer(object): 
    class func_S(param_packer_base):
        class command_category(ext.EnumWithName):
            DB_COMMAND = 1, '資料庫指令'

        class param_category(ext.EnumWithName):
            DB_NAME = 1, '資料庫名稱'
            MAIN_CMD = 2, '主指令'
            MAIN_PRM = 3, '主參數'
            OTHER_PRM = 4, '其餘參數'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_S, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_S.command_category.DB_COMMAND:
                prm_objs = [parameter(param_packer.func_S.param_category.DB_NAME, param_validator.conv_unicode), 
                            parameter(param_packer.func_S.param_category.MAIN_CMD, param_validator.conv_unicode), 
                            parameter(param_packer.func_S.param_category.MAIN_PRM, param_validator.conv_unicode), 
                            parameter(param_packer.func_S.param_category.OTHER_PRM, param_validator.check_dict)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs
    
    class func_A(param_packer_base):
        class command_category(ext.EnumWithName):
            ADD_PAIR_CH = 1, '新增回覆組(中文)'
            ADD_PAIR_EN = 2, '新增回覆組(英文)'
            ADD_PAIR_AUTO_CH = 3, '新增回覆組(自動偵測，中文)'
            ADD_PAIR_AUTO_EN = 4, '新增回覆組(自動偵測，英文)'

        class param_category(ext.EnumWithName):
            ATTACHMENT = 2, '附加回覆內容'
            RCV_TYPE = 3, '接收(種類)'
            RCV_TXT = 4, '接收(文字)'
            RCV_STK = 5, '接收(貼圖)'
            RCV_PIC = 6, '接收(圖片)'
            REP_TYPE = 7, '回覆(種類)'
            REP_TXT = 8, '回覆(文字)'
            REP_STK = 9, '回覆(貼圖)'
            REP_PIC = 10, '回覆(圖片)'
            RCV_CONTENT = 11, '接收(內容)'
            REP_CONTENT = 12, '回覆(內容)'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_A, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_A.command_category.ADD_PAIR_CH:
                prm_objs = [parameter(param_packer.func_A.param_category.ATTACHMENT, param_validator.conv_unicode_lt2K, True),
                            parameter(param_packer.func_A.param_category.RCV_TYPE, param_validator.keyword_dict.conv_pair_type_from_org),  
                            parameter(param_packer.func_A.param_category.RCV_TXT, param_validator.conv_unicode_lt2K, True),  
                            parameter(param_packer.func_A.param_category.RCV_PIC, param_validator.validate_sha224, True),  
                            parameter(param_packer.func_A.param_category.RCV_STK, param_validator.valid_int, True),  
                            parameter(param_packer.func_A.param_category.REP_TYPE, param_validator.keyword_dict.conv_pair_type_from_org), 
                            parameter(param_packer.func_A.param_category.REP_TXT, param_validator.conv_unicode_lt2K, True), 
                            parameter(param_packer.func_A.param_category.REP_PIC, param_validator.validate_https_image, True), 
                            parameter(param_packer.func_A.param_category.REP_STK, param_validator.valid_int, True)]
            elif command_category == param_packer.func_A.command_category.ADD_PAIR_EN:
                prm_objs = [parameter(param_packer.func_A.param_category.RCV_TYPE, param_validator.keyword_dict.conv_pair_type_from_org),  
                            parameter(param_packer.func_A.param_category.RCV_TXT, param_validator.conv_unicode_lt2K, True),  
                            parameter(param_packer.func_A.param_category.RCV_STK, param_validator.valid_int, True),  
                            parameter(param_packer.func_A.param_category.RCV_PIC, param_validator.validate_sha224, True),  
                            parameter(param_packer.func_A.param_category.REP_TYPE, param_validator.keyword_dict.conv_pair_type_from_org), 
                            parameter(param_packer.func_A.param_category.REP_TXT, param_validator.conv_unicode_lt2K, True), 
                            parameter(param_packer.func_A.param_category.REP_STK, param_validator.valid_int, True), 
                            parameter(param_packer.func_A.param_category.REP_PIC, param_validator.validate_https_image, True), 
                            parameter(param_packer.func_A.param_category.ATTACHMENT, param_validator.conv_unicode_lt2K, True)]
            elif command_category == param_packer.func_A.command_category.ADD_PAIR_AUTO_CH:
                prm_objs = [parameter(param_packer.func_A.param_category.ATTACHMENT, param_validator.conv_unicode_lt2K, True),  
                            parameter(param_packer.func_A.param_category.RCV_CONTENT, param_validator.conv_unicode_lt2K),  
                            parameter(param_packer.func_A.param_category.REP_CONTENT, param_validator.conv_unicode_lt2K)]
            elif command_category == param_packer.func_A.command_category.ADD_PAIR_AUTO_EN:
                prm_objs = [parameter(param_packer.func_A.param_category.RCV_CONTENT, param_validator.conv_unicode_lt2K),  
                            parameter(param_packer.func_A.param_category.REP_CONTENT, param_validator.conv_unicode_lt2K),
                            parameter(param_packer.func_A.param_category.ATTACHMENT, param_validator.conv_unicode_lt2K, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs
    
    class func_D(param_packer_base):
        class command_category(ext.EnumWithName):
            DEL_PAIR = 1, '刪除回覆組'

        class param_category(ext.EnumWithName):
            IS_ID = 1, '根據ID?'
            ID = 2, 'ID'
            WORD = 3, '關鍵字'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_D, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_D.command_category.DEL_PAIR:
                prm_objs = [parameter(param_packer.func_D.param_category.IS_ID, param_validator.is_not_null, True),  
                            parameter(param_packer.func_D.param_category.ID, param_validator.conv_int_arr, True),  
                            parameter(param_packer.func_D.param_category.WORD, param_validator.conv_unicode_arr, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs
    
    class func_Q(param_packer_base):
        class command_category(ext.EnumWithName):
            BY_AVAILABLE = 1, '根據可用範圍'
            BY_ID_RANGE = 2, '根據ID範圍'
            BY_UID = 3, '根據製作者'
            BY_GID = 4, '根據群組'
            BY_KEY = 5, '根據關鍵'

        class param_category(ext.EnumWithName):
            AVAILABLE = 1, '可用的'
            GLOBAL = 2, '全域'
            START_ID = 3, '起始ID'
            END_ID = 4, '終止ID'
            UID = 5, '製作者ID'
            GID = 6, '群組ID'
            IS_ID = 7, '根據ID?'
            KEYWORD = 8, '關鍵字'
            ID = 9, 'ID'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_Q, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_Q.command_category.BY_AVAILABLE:
                prm_objs = [parameter(param_packer.func_Q.param_category.GLOBAL, param_validator.is_not_null, True),
                            parameter(param_packer.func_Q.param_category.AVAILABLE, param_validator.is_not_null, True)]
            elif command_category == param_packer.func_Q.command_category.BY_ID_RANGE:
                prm_objs = [parameter(param_packer.func_Q.param_category.START_ID, param_validator.conv_int_gt_0),  
                            parameter(param_packer.func_Q.param_category.END_ID, param_validator.conv_int_gt_0)]
            elif command_category == param_packer.func_Q.command_category.BY_UID:
                prm_objs = [parameter(param_packer.func_Q.param_category.UID, param_validator.line_bot_api.validate_uid)]
            elif command_category == param_packer.func_Q.command_category.BY_GID:
                prm_objs = [parameter(param_packer.func_Q.param_category.GID, param_validator.line_bot_api.validate_gid_public_global)]
            elif command_category == param_packer.func_Q.command_category.BY_KEY:
                prm_objs = [parameter(param_packer.func_Q.param_category.IS_ID, param_validator.is_not_null, True),  
                            parameter(param_packer.func_Q.param_category.ID, param_validator.conv_int_arr, True),  
                            parameter(param_packer.func_Q.param_category.KEYWORD, param_validator.conv_unicode, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs
    
    class func_X(param_packer_base):
        class command_category(ext.EnumWithName):
            BY_ID_WORD = 1, '根據ID/字'
            BY_GID = 2, '根據群組'

        class param_category(ext.EnumWithName):
            IS_ID = 1, '根據ID?'
            SOURCE_GID = 2, '來源群組ID'
            TARGET_GID = 3, '目標群組ID'
            ID = 4, '回覆組ID'
            KEYWORD = 5, '關鍵字'
            WITH_PINNED = 6, '包含置頂'
            WITH_DELETED = 7, '包含已刪除'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_X, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_X.command_category.BY_ID_WORD:
                prm_objs = [parameter(param_packer.func_X.param_category.IS_ID, param_validator.is_not_null, True),
                            parameter(param_packer.func_X.param_category.ID, param_validator.conv_int_arr, True),
                            parameter(param_packer.func_X.param_category.KEYWORD, param_validator.conv_unicode_arr, True),
                            parameter(param_packer.func_X.param_category.WITH_PINNED, param_validator.special_category.X_pinned, True),
                            parameter(param_packer.func_X.param_category.WITH_DELETED, param_validator.special_category.X_deleted, True)]
            elif command_category == param_packer.func_X.command_category.BY_GID:
                prm_objs = [parameter(param_packer.func_X.param_category.SOURCE_GID, param_validator.line_bot_api.validate_gid),
                            parameter(param_packer.func_X.param_category.WITH_PINNED, param_validator.special_category.X_pinned, True),
                            parameter(param_packer.func_X.param_category.WITH_DELETED, param_validator.special_category.X_deleted, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_X2(param_packer_base):
        class command_category(ext.EnumWithName):
            CLEAR_DATA = 1, '清除關鍵字'

        class param_category(ext.EnumWithName):
            GID = 1, '群組ID'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_X2, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_X2.command_category.CLEAR_DATA:
                prm_objs = []
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_E(param_packer_base):
        class command_category(ext.EnumWithName):
            MOD_LINKED = 1, '修改相關關鍵字'
            MOD_PINNED = 2, '修改置頂'

        class param_category(ext.EnumWithName):
            IS_ID = 1, '根據ID?'
            ID = 2, 'ID陣列'
            KEYWORD = 3, '關鍵字'
            LINKED = 4, '相關關鍵字'
            HAS_LINK = 5, '有/無關'
            NOT_PIN = 6, '不置頂'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_E, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_E.command_category.MOD_LINKED:
                prm_objs = [parameter(param_packer.func_E.param_category.IS_ID, param_validator.is_not_null, True),
                            parameter(param_packer.func_E.param_category.ID, param_validator.conv_int_arr, True),
                            parameter(param_packer.func_E.param_category.KEYWORD, param_validator.conv_unicode_arr, True),
                            parameter(param_packer.func_E.param_category.LINKED, param_validator.conv_unicode_arr),
                            parameter(param_packer.func_E.param_category.HAS_LINK, param_validator.text_to_bool)]
            elif command_category == param_packer.func_E.command_category.MOD_PINNED:
                prm_objs = [parameter(param_packer.func_E.param_category.NOT_PIN, param_validator.is_not_null),
                            parameter(param_packer.func_E.param_category.IS_ID, param_validator.is_not_null, True),
                            parameter(param_packer.func_E.param_category.ID, param_validator.conv_int_arr, True),
                            parameter(param_packer.func_E.param_category.KEYWORD, param_validator.conv_unicode_arr, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_K(param_packer_base):
        class command_category(ext.EnumWithName):
            RANKING = 1, '排名'

        class param_category(ext.EnumWithName):
            CATEGORY = 1, '種類'
            COUNT = 2, '結果數量'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_K, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_K.command_category.RANKING:
                prm_objs = [parameter(param_packer.func_K.param_category.CATEGORY, param_validator.special_category.K_ranking_category),
                            parameter(param_packer.func_K.param_category.COUNT, param_validator.conv_int_gt_0, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_P(param_packer_base):
        class command_category(ext.EnumWithName):
            SYSTEM_RECORD = 1, '系統紀錄'
            MESSAGE_RECORD = 2, '訊息量紀錄'

        class param_category(ext.EnumWithName):
            CATEGORY = 1, '種類'
            COUNT = 2, '結果數量'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_P, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_P.command_category.SYSTEM_RECORD:
                prm_objs = [parameter(param_packer.func_P.param_category.CATEGORY, param_validator.special_category.P_record_category)]
            elif command_category == param_packer.func_P.command_category.MESSAGE_RECORD:
                prm_objs = [parameter(param_packer.func_P.param_category.COUNT, param_validator.conv_int_gt_0, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_P2(param_packer_base):
        class command_category(ext.EnumWithName):
            FIND_PROFILE = 1, '查詢使用者資料'

        class param_category(ext.EnumWithName):
            UID = 1, '使用者ID'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_P2, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_P2.command_category.FIND_PROFILE:
                prm_objs = [parameter(param_packer.func_P2.param_category.UID, param_validator.line_bot_api.validate_uid)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_G(param_packer_base):
        class command_category(ext.EnumWithName):
            GROUP_PROFILE = 1, '查詢群組資料'

        class param_category(ext.EnumWithName):
            GID = 1, '群組ID'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_G, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_G.command_category.GROUP_PROFILE:
                prm_objs = [parameter(param_packer.func_G.param_category.GID, param_validator.line_bot_api.validate_gid, True)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_GA(param_packer_base):
        class command_category(ext.EnumWithName):
            SET_RANGE = 1, '設定群組資料範圍'

        class param_category(ext.EnumWithName):
            RANGE = 1, '範圍'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_GA, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_GA.command_category.SET_RANGE:
                prm_objs = [parameter(param_packer.func_GA.param_category.RANGE, param_validator.special_category.GA_group_range)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_GA2(param_packer_base):
        class command_category(ext.EnumWithName):
            SET_PERMISSION = 1, '設定權限'

        class param_category(ext.EnumWithName):
            UID = 1, '使用者ID'
            PERMISSION = 2, '權限'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_GA2, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_GA2.command_category.SET_PERMISSION:
                prm_objs = [parameter(param_packer.func_GA2.param_category.UID, param_validator.line_bot_api.validate_uid),
                            parameter(param_packer.func_GA2.param_category.PERMISSION, param_validator.special_category.GA2_permission)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_GA3(param_packer_base):
        class command_category(ext.EnumWithName):
            ACTIVATE_PUBLIC_DATA = 1, '啟用公用資料庫'

        class param_category(ext.EnumWithName):
            ACTIVATE_TOKEN = 1, '密鑰'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_GA3, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_GA3.command_category.ACTIVATE_PUBLIC_DATA:
                prm_objs = [parameter(param_packer.func_GA3.param_category.ACTIVATE_TOKEN, param_validator.special_category.GA3_validate_token)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_H(param_packer_base):
        class command_category(ext.EnumWithName):
            CHANNEL_DATA = 1, '查詢頻道資料'

        class param_category(ext.EnumWithName):
            DUMMY = 1, '(Dummy)'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_H, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_H.command_category.CHANNEL_DATA:
                prm_objs = []
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_O(param_packer_base):
        class command_category(ext.EnumWithName):
            OXFORD = 1, '牛津字典'

        class param_category(ext.EnumWithName):
            VOCABULARY = 1, '單字'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_O, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_O.command_category.OXFORD:
                prm_objs = [parameter(param_packer.func_O.param_category.VOCABULARY, param_validator.conv_unicode_lower)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_RD(param_packer_base):
        class command_category(ext.EnumWithName):
            TEXT = 1, '文字'
            PROBABILITY = 2, '機率'
            NUM_RANGE = 3, '數字範圍'
            CASE_SERIAL = 4, '案件編號'

        class param_category(ext.EnumWithName):
            COUNT = 1, '次數'
            PROBABILITY = 2, '機率'
            TEXT = 3, '文字'
            START_NUM = 4, '起始數字'
            END_NUM = 5, '終止數字'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_RD, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_RD.command_category.TEXT:
                prm_objs = [parameter(param_packer.func_RD.param_category.COUNT, param_validator.conv_int_lt_1m, True),
                            parameter(param_packer.func_RD.param_category.TEXT, param_validator.conv_unicode_arr)]
            elif command_category == param_packer.func_RD.command_category.PROBABILITY:
                prm_objs = [parameter(param_packer.func_RD.param_category.PROBABILITY, param_validator.conv_float),
                            parameter(param_packer.func_RD.param_category.COUNT, param_validator.conv_int_lt_1m, True)]
            elif command_category == param_packer.func_RD.command_category.NUM_RANGE:
                prm_objs = [parameter(param_packer.func_RD.param_category.START_NUM, param_validator.conv_int_gt_0),
                            parameter(param_packer.func_RD.param_category.END_NUM, param_validator.conv_int_gt_0),
                            parameter(param_packer.func_RD.param_category.COUNT, param_validator.conv_int_lt_1m, True)]
            elif command_category == param_packer.func_RD.command_category.CASE_SERIAL:
                prm_objs = []
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_L(param_packer_base):
        class command_category(ext.EnumWithName):
            RECENT_DATA = 1, '最近紀錄'

        class param_category(ext.EnumWithName):
            CATEGORY = 1, '種類'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_L, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_L.command_category.RECENT_DATA:
                prm_objs = [parameter(param_packer.func_L.param_category.CATEGORY, param_validator.special_category.L_category)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_T(param_packer_base):
        class command_category(ext.EnumWithName):
            ENCODE_UTF_8 = 1, '編碼(UTF-8)'
            ENCODE_NEWLINE = 2, '編碼(換行)'
            ENCODE_SHA = 3, '編碼(SHA224)'
            ENCODE_FX = 4, '編碼(轉方程)'

        class param_category(ext.EnumWithName):
            TARGET = 1, '編碼對象'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_T, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if any(command_category == ctg for ctg in (param_packer.func_T.command_category.ENCODE_UTF_8,
                                                       param_packer.func_T.command_category.ENCODE_NEWLINE,
                                                       param_packer.func_T.command_category.ENCODE_SHA,
                                                       param_packer.func_T.command_category.ENCODE_FX)):
                prm_objs = [parameter(param_packer.func_T.param_category.TARGET, param_validator.conv_unicode)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_C(param_packer_base):
        class command_category(ext.EnumWithName):
            AVAILABLE = 1, '可用'
            CURRENT = 2, '目前匯率'
            HISTORIC = 3, '歷史匯率'
            CONVERT = 4, '匯率轉換'

        class param_category(ext.EnumWithName):
            CURRENCY_SYMBOLS = 1, '貨幣種類'
            DATE = 2, '日期'
            BASE_CURRENCY = 3, '基底貨幣'
            TARGET_CURRENCY = 4, '目標貨幣'
            AMOUNT = 5, '金額'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_C, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_C.command_category.AVAILABLE:
                prm_objs = []
            elif command_category == param_packer.func_C.command_category.CURRENT:
                prm_objs = [parameter(param_packer.func_C.param_category.CURRENCY_SYMBOLS, param_validator.special_category.C_validate_currency_symbols, True)]
            elif command_category == param_packer.func_C.command_category.HISTORIC:
                prm_objs = [parameter(param_packer.func_C.param_category.DATE, param_validator.special_category.C_validate_date),
                            parameter(param_packer.func_C.param_category.CURRENCY_SYMBOLS, param_validator.special_category.C_validate_currency_symbols, True)]
            elif command_category == param_packer.func_C.command_category.CONVERT:
                prm_objs = [parameter(param_packer.func_C.param_category.BASE_CURRENCY, param_validator.special_category.C_validate_currency_symbol),
                            parameter(param_packer.func_C.param_category.AMOUNT, param_validator.conv_float, True),
                            parameter(param_packer.func_C.param_category.TARGET_CURRENCY, param_validator.special_category.C_validate_currency_symbol)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_W(param_packer_base):
        class command_category(ext.EnumWithName):
            DATA_CONTROL = 1, '資料控制'
            ID_SEARCH = 2, '搜尋ID'

        class param_category(ext.EnumWithName):
            KEYWORD = 1, '城市關鍵字'
            CITY_ID = 2, '城市ID'
            OUTPUT_TYPE = 3, '輸出資料種類'
            HOUR_RANGE = 4, '範圍(小時)'
            FREQUENCY = 5, '頻率(小時)'
            ACTION = 6, '動作'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_W, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_W.command_category.DATA_CONTROL:
                prm_objs = [parameter(param_packer.func_W.param_category.ACTION, param_validator.special_category.W_action),
                            parameter(param_packer.func_W.param_category.CITY_ID, param_validator.conv_int_arr),
                            parameter(param_packer.func_W.param_category.OUTPUT_TYPE, param_validator.special_category.W_output_type, True),
                            parameter(param_packer.func_W.param_category.HOUR_RANGE, param_validator.conv_int_gt_0, True),
                            parameter(param_packer.func_W.param_category.FREQUENCY, param_validator.conv_int_gt_0, True)]
            elif command_category == param_packer.func_W.command_category.ID_SEARCH:
                prm_objs = [parameter(param_packer.func_W.param_category.KEYWORD, param_validator.conv_unicode)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_DL(param_packer_base):
        class command_category(ext.EnumWithName):
            DOWNLOAD_STICKER_PACKAGE = 1, '下載貼圖圖包'

        class param_category(ext.EnumWithName):
            PACKAGE_ID = 1, '圖包ID'
            INCLUDE_SOUND = 2, '含聲音'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_DL, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_DL.command_category.DOWNLOAD_STICKER_PACKAGE:
                prm_objs = [parameter(param_packer.func_DL.param_category.PACKAGE_ID, param_validator.valid_int),
                            parameter(param_packer.func_DL.param_category.INCLUDE_SOUND, param_validator.is_not_null)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_STK(param_packer_base):
        class command_category(ext.EnumWithName):
            RANKING = 1, '排行'
            STICKER_LOOKUP = 2, '貼圖圖片'

        class param_category(ext.EnumWithName):
            CATEGORY = 1, '種類'
            HOUR_RANGE = 2, '範圍(小時)'
            COUNT = 3, '範圍(名次)'
            STICKER_ID = 4, '貼圖ID'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_STK, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_STK.command_category.RANKING:
                prm_objs = [parameter(param_packer.func_STK.param_category.CATEGORY, param_validator.special_category.STK_action_category),
                            parameter(param_packer.func_STK.param_category.HOUR_RANGE, param_validator.conv_int_gt_0, True),
                            parameter(param_packer.func_STK.param_category.COUNT, param_validator.conv_int_gt_0, True)]
            elif command_category == param_packer.func_STK.command_category.STICKER_LOOKUP:
                prm_objs = [parameter(param_packer.func_STK.param_category.STICKER_ID, param_validator.valid_int)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_LUK(param_packer_base):
        class command_category(ext.EnumWithName):
            SC_OPP = 1, '計算分數對應機率'

        class param_category(ext.EnumWithName):
            SCORE = 1, '分數'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_LUK, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_LUK.command_category.SC_OPP:
                prm_objs = [parameter(param_packer.func_LUK.param_category.SCORE, param_validator.conv_float)]
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

    class func_F(param_packer_base):
        class command_category(ext.EnumWithName):
            CREATE = 1, '新增'
            SEARCH = 2, '搜尋'
            UPDATE = 3, '更新'
            DELETE = 4, '刪除'
            GET_LINK = 5, '獲取連結'

        class param_category(ext.EnumWithName):
            RENDER_TEXT = 1, '文字'
            TITLE = 2, '標題'
            URL = 3, '相關連結'
            KEYWORD = 4, '關鍵字'
            ID = 5, 'ID'

        def __init__(self, command_category, CH_regex=None, EN_regex=None):
            prm_objs = self._get_prm_objs(command_category)

            super(param_packer.func_F, self).__init__(command_category, prm_objs, CH_regex, EN_regex)

        def _get_prm_objs(self, command_category):
            if command_category == param_packer.func_F.command_category.CREATE:
                prm_objs = [parameter(param_packer.func_F.param_category.RENDER_TEXT, param_validator.conv_unicode),
                            parameter(param_packer.func_F.param_category.TITLE, param_validator.conv_unicode, True),
                            parameter(param_packer.func_F.param_category.URL, param_validator.validate_https, True)]
            elif command_category == param_packer.func_F.command_category.DELETE:
                prm_objs = [parameter(param_packer.func_F.param_category.ID, param_validator.conv_int_arr)]
            elif command_category == param_packer.func_F.command_category.SEARCH:
                prm_objs = [parameter(param_packer.func_F.param_category.KEYWORD, param_validator.conv_unicode_arr)]
            elif command_category == param_packer.func_F.command_category.UPDATE:
                prm_objs = [parameter(param_packer.func_F.param_category.ID, param_validator.conv_int_gt_0),
                            parameter(param_packer.func_F.param_category.RENDER_TEXT, param_validator.conv_unicode),
                            parameter(param_packer.func_F.param_category.TITLE, param_validator.conv_unicode, True),
                            parameter(param_packer.func_F.param_category.URL, param_validator.validate_https, True)]
            elif command_category == param_packer.func_F.command_category.GET_LINK:
                prm_objs = []
            else:
                raise UndefinedCommandCategoryException()

            return prm_objs

class packer_factory(object):
    _S = [param_packer.func_S(command_category=param_packer.func_S.command_category.DB_COMMAND,
                              CH_regex=ur'小水母 DB ?資料庫((?:.|\n)+)(?<! ) ?主指令((?:.|\n)+)(?<! ) ?主參數((?:.|\n)+)(?<! ) ?參數((?:.|\n)+)(?<! )', 
                              EN_regex=ur'JC\nS\n(.+(?<! ))\n(.+(?<! ))\n(.+(?<! ))\n(.+(?<! ))')]

    _M = [param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_CH,
                              CH_regex=ur'小水母 置頂 ?(?:\s|附加((?:.|\n)+)(?<! ))? ?(收到 ?((?:.|\n)+)(?<! )|看到 ?(\w+)|被貼 ?(\w+)) ?(回答 ?((?:.|\n)+)(?<! )|回圖 ?(https://(?:.|\n)+)|回貼 ?(\w+))'),
          param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_EN,
                              EN_regex=ur'JC\nM\n(T\n(.+)|S\n(\w+)|P\n(\w+))\n(T\n(.+)|S\n(\w+)|P\n(https://.+))(?:\n(.+))?'),
          param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_AUTO_CH,
                              CH_regex=ur'小水母 置頂 ?(?:\s|附加((?:.|\n)+)(?<! ))? ?(?:入 ?((?:.|\n)+)(?<! )) ?(?:出 ?((?:.|\n)+)(?<! ))'),
          param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_AUTO_EN,
                              EN_regex=ur'JC\nMM\n(.+)\n(.+)(?:\n(.+))?')]

    _A = [param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_CH,
                              CH_regex=ur'小水母 記住 ?(?:\s|附加((?:.|\n)+)(?<! ))? ?(收到 ?((?:.|\n)+)(?<! )|看到 ?(\w+)|被貼 ?(\w+)) ?(回答 ?((?:.|\n)+)(?<! )|回圖 ?(https://(?:.|\n)+)|回貼 ?(\w+))'),
          param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_EN,
                              EN_regex=ur'JC\nA\n(T\n(.+)|S\n(\w+)|P\n(\w+))\n(T\n(.+)|S\n(\w+)|P\n(https://.+))(?:\n(.+))?'),
          param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_AUTO_CH,
                              CH_regex=ur'小水母 記住 ?(?:\s|附加((?:.|\n)+)(?<! ))? ?(?:入 ?((?:.|\n)+)(?<! )) ?(?:出 ?((?:.|\n)+)(?<! ))'),
          param_packer.func_A(command_category=param_packer.func_A.command_category.ADD_PAIR_AUTO_EN,
                              EN_regex=ur'JC\nAA\n(.+)\n(.+)(?:\n(.+))?')]

    _R = [param_packer.func_D(command_category=param_packer.func_D.command_category.DEL_PAIR,
                              CH_regex=ur'小水母 忘記置頂的 ?(?:(ID ?)(\w+)|((?:.|\n)+))', 
                              EN_regex=ur'JC\nR\n?(?:(ID\n)(\w+)|(.+))')]

    _D = [param_packer.func_D(command_category=param_packer.func_D.command_category.DEL_PAIR,
                              CH_regex=ur'小水母 忘記 ?(?:(ID ?)(\w+)|((?:.|\n)+))', 
                              EN_regex=ur'JC\nD\n?(?:(ID\n)(\w+)|(.+))')]

    _Q = [param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_AVAILABLE,
                              CH_regex=ur'小水母 找 ?(?:(全部)|(可以用的))',
                              EN_regex=ur'JC\n(?:(Q\nALL)|(Q))'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_ID_RANGE,
                              CH_regex=ur'小水母 找 ?ID範圍 ?(\w+)(?:到|~)(\w+)',
                              EN_regex=ur'JC\nQ\nID\n(\w+)\n(\w+)'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_UID,
                              CH_regex=ur'小水母 找 ?(\w+) ?做的',
                              EN_regex=ur'JC\nQ\nUID\n(\w+)'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_GID,
                              CH_regex=ur'小水母 找 ?(\w+) ?裡面的',
                              EN_regex=ur'JC\nQ\nGID\n(\w+)'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_KEY,
                              CH_regex=ur'小水母 找 ?(?:(ID ?)(\w+)|((?:.|\n)+))',
                              EN_regex=ur'JC\nQ\n(?:(ID\n)([\w ]+)|(.+))')]

    _I = [param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_AVAILABLE,
                              CH_regex=ur'小水母 詳細找 ?(?:(全部)|(可以用的))',
                              EN_regex=ur'JC\n(?:(I\nALL)|(I))'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_ID_RANGE,
                              CH_regex=ur'小水母 詳細找 ?ID範圍 ?(\w+)(?:到|~)(\w+)',
                              EN_regex=ur'JC\nI\nID\n(\w+)\n(\w+)'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_UID,
                              CH_regex=ur'小水母 詳細找 ?(\w+) ?做的',
                              EN_regex=ur'JC\nI\nUID\n(\w+)'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_GID,
                              CH_regex=ur'小水母 詳細找 ?(\w+) ?裡面的',
                              EN_regex=ur'JC\nI\nGID\n(\w+)'),
          param_packer.func_Q(command_category=param_packer.func_Q.command_category.BY_KEY,
                              CH_regex=ur'小水母 詳細找 ?(?:(ID ?)(\w+)|((?:.|\n)+))',
                              EN_regex=ur'JC\nI\n(?:(ID\n)(\w+)|(.+))')]

    _X = [param_packer.func_X(command_category=param_packer.func_X.command_category.BY_ID_WORD,
                              CH_regex=ur'小水母 複製 ?(?:(ID ?)([\w ]+)|((?:.|\n)+)) ?((?:包含置頂)?) ?((?:包含已刪除)?)',
                              EN_regex=ur'JC\nX\n(?:(ID)\n([\w ]+)|(.+))\n?(P?)(D?)'),
          param_packer.func_X(command_category=param_packer.func_X.command_category.BY_GID,
                              CH_regex=ur'小水母 複製群組(\w+)?裡面的 ?((?:包含置頂)?) ?((?:包含置頂)?)',
                              EN_regex=ur'JC\nX\nGID\n(\w+)\n?(P?)(D?)')]

    _X2 = [param_packer.func_X2(command_category=param_packer.func_X2.command_category.CLEAR_DATA,
                                CH_regex=ur'小水母 清除所有回覆組571a95ae875a9ae315fad8cdf814858d9441c5ec671f0fb373b5f340',
                                EN_regex=ur'JC\nX2\n571a95ae875a9ae315fad8cdf814858d9441c5ec671f0fb373b5f340')]

    _E = [param_packer.func_E(command_category=param_packer.func_E.command_category.MOD_LINKED,
                              CH_regex=ur'小水母 修改 ?(?:(ID ?)(\d{1}[\w ]*)|((?:.|\n)+))跟((?:.|\n)+)(\w+)關',
                              EN_regex=ur'JC\nE\n(?:(ID)\n([\w ]+)|((?:.|\n)+))\n((?:.|\n)+)\n(\w+)'),
          param_packer.func_E(command_category=param_packer.func_E.command_category.MOD_PINNED,
                              CH_regex=ur'小水母 修改(不)?置頂 ?(?:(ID ?)(\w+)|((?:.|\n)+))',
                              EN_regex=ur'JC\nE\n(N)?P\n(?:(ID)\n([\w ]+)|((?:.|\n)+))')]

    _K = [param_packer.func_K(command_category=param_packer.func_K.command_category.RANKING,
                              CH_regex=ur'小水母 排名(\w+) ?(?:前(\w+)名)?',
                              EN_regex=ur'JC\nK\n(\w+)(?:\n?(\w+))?')]

    _P = [param_packer.func_P(command_category=param_packer.func_P.command_category.MESSAGE_RECORD,
                              CH_regex=ur'小水母 系統訊息前(\w+)名',
                              EN_regex=ur'JC\nP\nMSG(?:\n(\w+))?'),
          param_packer.func_P(command_category=param_packer.func_P.command_category.SYSTEM_RECORD,
                              CH_regex=ur'小水母 系統(\w+)',
                              EN_regex=ur'JC\nP\n(\w+)')]

    _P2 = [param_packer.func_P2(command_category=param_packer.func_P2.command_category.FIND_PROFILE,
                                CH_regex=ur'小水母 使用者 ?(\w+) ?的資料',
                                EN_regex=ur'JC\nP2\n(\w+)')]

    _G = [param_packer.func_G(command_category=param_packer.func_G.command_category.GROUP_PROFILE,
                                CH_regex=ur'小水母 群組(\w*)?的資料',
                                EN_regex=ur'JC\nG(?:\n(\w*))?')]

    _GA = [param_packer.func_GA(command_category=param_packer.func_G.command_category.GROUP_PROFILE,
                                CH_regex=ur'小水母 當(\w+)',
                                EN_regex=ur'JC\nGA\n(\w+)')]

    _GA2 = [param_packer.func_GA2(command_category=param_packer.func_GA2.command_category.SET_PERMISSION,
                                  CH_regex=ur'小水母 讓 ?(\w+) ?變成(\w+)',
                                  EN_regex=ur'JC\nGA2\n(\w+)\n(\w+)')]

    _GA3 = [param_packer.func_GA2(command_category=param_packer.func_GA2.command_category.SET_PERMISSION,
                                  CH_regex=ur'小水母 啟用公用資料庫(\w+)',
                                  EN_regex=ur'JC\nGA3\n(\w+)')]

    _H = [param_packer.func_H(command_category=param_packer.func_GA2.command_category.SET_PERMISSION,
                                  CH_regex=ur'小水母 頻道資訊',
                                  EN_regex=ur'JC\nH')]

    _O = [param_packer.func_O(command_category=param_packer.func_O.command_category.OXFORD,
                              CH_regex=ur'小水母 查 ?([\w ]+)',
                              EN_regex=ur'JC\nO\n([\w ]+)')]

    _RD = [param_packer.func_RD(command_category=param_packer.func_RD.command_category.CASE_SERIAL,
                                CH_regex=ur'小水母 抽案件編號',
                                EN_regex=ur'JC\nRD'),
           param_packer.func_RD(command_category=param_packer.func_RD.command_category.NUM_RANGE,
                                CH_regex=ur'小水母 抽 ?(\w+)(?:到|~)(\w+) ?(?:(\w+)次)?',
                                EN_regex=ur'JC\nRD\n(\w+) (\w+)\n(\w+)?'),
           param_packer.func_RD(command_category=param_packer.func_RD.command_category.PROBABILITY,
                                CH_regex=ur'小水母 抽 ?(?:([\w\.]{1,})%) ?(?:(\w+)次)?',
                                EN_regex=ur'JC\nRD\n(?:([\w\.]{1,})%)(?:\n(\w+))?'),
           param_packer.func_RD(command_category=param_packer.func_RD.command_category.TEXT,
                                CH_regex=ur'小水母 抽 ?(?:(\w+)次)? ?((?:.|\n)+)',
                                EN_regex=ur'JC\nRD(?:\n(\w+))?\n((?:.|\n)+)')]

    _L = [param_packer.func_L(command_category=param_packer.func_L.command_category.RECENT_DATA,
                              CH_regex=ur'小水母 最近的(\w+)',
                              EN_regex=ur'JC\nL\n(\w+)')]

    _T = [param_packer.func_T(command_category=param_packer.func_T.command_category.ENCODE_UTF_8,
                              CH_regex=ur'小水母 轉U8 ?((?:.|\n)+)',
                              EN_regex=ur'JC\nT\nU8\n((?:.|\n)+)'),
          param_packer.func_T(command_category=param_packer.func_T.command_category.ENCODE_NEWLINE,
                              CH_regex=ur'小水母 轉換行 ?((?:.|\n)+)',
                              EN_regex=ur'JC\nT\nNL\n((?:.|\n)+)'),
          param_packer.func_T(command_category=param_packer.func_T.command_category.ENCODE_SHA,
                              CH_regex=ur'小水母 轉SHA ?((?:.|\n)+)',
                              EN_regex=ur'JC\nT\nSHA\n((?:.|\n)+)'),
          param_packer.func_T(command_category=param_packer.func_T.command_category.ENCODE_FX,
                              CH_regex=ur'小水母 轉方程 ?((?:.|\n)+)',
                              EN_regex=ur'JC\nT\nFX\n((?:.|\n)+)')]

    _C = [param_packer.func_C(command_category=param_packer.func_C.command_category.AVAILABLE,
                              CH_regex=ur'小水母 匯率 ?可用',
                              EN_regex=ur'JC\nC\n\$'),
          param_packer.func_C(command_category=param_packer.func_C.command_category.HISTORIC,
                              CH_regex=ur'小水母 匯率日期(\w+) ?貨幣(\w*)',
                              EN_regex=ur'JC\nC\n(\w+)(?:\n?(\w*))'),
          param_packer.func_C(command_category=param_packer.func_C.command_category.CONVERT,
                              CH_regex=ur'小水母 匯率 ?(\w+) ([\w\.]+) ?轉成 ?(\w+)',
                              EN_regex=ur'JC\nC\n(\w+)\n([\w\.]+)\n(\w+)'),
          param_packer.func_C(command_category=param_packer.func_C.command_category.CURRENT,
                              CH_regex=ur'小水母 匯率 ?(\w*)',
                              EN_regex=ur'JC\nC(?:\n?(\w*))')]

    _W = [param_packer.func_W(command_category=param_packer.func_W.command_category.ID_SEARCH,
                              CH_regex=ur'小水母 天氣ID查詢 ?(\w+)',
                              EN_regex=ur'JC\nW\n(\w+)'),
          param_packer.func_W(command_category=param_packer.func_W.command_category.DATA_CONTROL,
                              CH_regex=ur'小水母 天氣(查詢|新增|刪除) ?([\w ]+) ?(詳細|詳|簡潔|簡)? ?(?:(\w+)小時內)? ?(?:每(\w+)小時)?',
                              EN_regex=ur'JC\nW\n(A|D|ID)(?:\n?([\w ]+))?(?:\n?(S|D))?(?:\n?(\w+))?(?:\n?(\w+))?')]

    _DL = [param_packer.func_DL(command_category=param_packer.func_DL.command_category.DOWNLOAD_STICKER_PACKAGE,
                                CH_regex=ur'小水母 下載貼圖圖包 ?(\w+) ?(含聲音)?',
                                EN_regex=ur'JC\nDL\n(\w+)(S)?')]

    _STK = [param_packer.func_STK(command_category=param_packer.func_STK.command_category.STICKER_LOOKUP,
                                  CH_regex=ur'小水母 貼圖(\w+)',
                                  EN_regex=ur'JC\nSTK\n(\w+)'),
            param_packer.func_STK(command_category=param_packer.func_STK.command_category.RANKING,
                                  CH_regex=ur'小水母 (貼圖|貼圖圖包)排行 ?(?:前(\w+)名)? ?(?:(\w+)小時內)?',
                                  EN_regex=ur'JC\nSTK\n(\w+)(?:\n(\w+))?(?:\n(\w+))?')]

    _LUK = [param_packer.func_LUK(command_category=param_packer.func_LUK.command_category.SC_OPP,
                                  CH_regex=ur'小水母 運勢預估 ?([\w\.E+-]+)',
                                  EN_regex=ur'JC\nLUK\n([\w\.E+-]+)')]

    _F = [param_packer.func_F(command_category=param_packer.func_F.command_category.GET_LINK,
                              CH_regex=ur'小水母 公告連結',
                              EN_regex=ur'JC\nF'),
          param_packer.func_F(command_category=param_packer.func_F.command_category.CREATE,
                              CH_regex=ur'小水母 公告建立 ?(.+) ?(?:標題 ?(\.+)) ?(?:URL ?(.+))',
                              EN_regex=ur'JC\nF\nC\n(.+)(?:\n(.+))?(?:\n(.+))?'),
          param_packer.func_F(command_category=param_packer.func_F.command_category.DELETE,
                              CH_regex=ur'小水母 公告刪除 ?(.+)',
                              EN_regex=ur'JC\nF\nD\n(.+)'),
          param_packer.func_F(command_category=param_packer.func_F.command_category.SEARCH,
                              CH_regex=ur'小水母 公告(?:搜尋|查詢) ?(.+)',
                              EN_regex=ur'JC\nF\nS\n(.+)'),
          param_packer.func_F(command_category=param_packer.func_F.command_category.UPDATE,
                              CH_regex=ur'小水母 公告更新 ?ID ?(.+) (.+) ?(?:標題 ?(.+)) ?(?:URL ?(.+))',
                              EN_regex=ur'JC\nF\nU\n(.+)\n(.+)(?:\n(.+))?(?:\n(.+))?')]
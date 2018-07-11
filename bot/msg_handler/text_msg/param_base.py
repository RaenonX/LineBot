# -*- coding: utf-8 -*-
import requests

import ast

from error import error
import ext
import tool, db, bot

class param_packer_base(object):
    def __init__(self, command_category, param_objs, CH_regex=None, EN_regex=None):
        """
        Parameters:
            CH_regex: chinese regex to check.
            EN_regex: english regex to check.
            command_category: category of the command.
            param_field: enum of parameter object in list.
        """
        self._CH = CH_regex
        self._EN = EN_regex

        if self._CH is None and self._EN is None:
            raise ValueError('Must specify at least one regex.')

        self._cat = command_category
        self._param_objs = param_objs

    @property
    def CH(self):
        return self._CH

    @property
    def EN(self):
        return self._EN

    @property
    def command_category(self):
        return self._cat

    def pack(self, text):
        """
        Parameters:
            text: text to try to match the provided regex.

        Return:
            param_packing_result.
        """
        regex_result = tool.regex_finder.find_match([self._CH, self._EN], text, False)

        if regex_result is not None:
            p_dict = {}
            for i, param in enumerate(self._param_objs, start=1):
                validate_result = param.validate(regex_result.group(i))
                if validate_result.valid:
                    p_dict[param.field_enum] = validate_result.ret
                else:
                    return param_packing_result(error.sys_command.parameter_error(i, validate_result.ret), param_packing_result_status.ERROR_IN_PARAM, self._cat)

            return param_packing_result(p_dict, param_packing_result_status.ALL_PASS, self._cat)
        else:
            return param_packing_result(None, param_packing_result_status.NO_MATCH, self._cat)

class param_packing_result_status(ext.EnumWithName):
    ALL_PASS = 1, '全通過'
    ERROR_IN_PARAM = 2, '參數有誤'
    NO_MATCH = 3, '無符合'

class param_packing_result(object):
    def __init__(self, result, status, command_category):
        self._result = result
        self._status = status
        self._cmd_cat = command_category

    @property
    def command_category(self):
        return self._cmd_cat

    @property
    def result(self):
        """
        Returns:
            Status=ALL_PASS -> Parameter dictionary.
            Status=ERROR_IN_PARAM -> Error message of parameter.
            Status=NO_MATCH -> None.
        """
        return self._result

    @property
    def status(self):
        return self._status

class parameter(object):
    def __init__(self, field_enum, validator_method, allow_null=False):
        """
        Parameter:
            field_enum: Enum that represents this field.
            validator_method: Method to validate the parameter. If the method is not come from param_validator, the action may be unexpected.
            allow_null: Allow this field to be null.
        """
        self._field_enum = field_enum
        self._validator = validator_method
        self._allow_null = allow_null

    @property
    def field_enum(self):
        return self._field_enum

    def validate(self, content):
        """
        Parameter:
            content: Parameter to validate.

        Returns:
            return param_validation_result.
        """
        return self._validator(content, self._allow_null)

class param_validator(object):
    """
    Meta:
        Must be @staticmethod.

    Input:
        obj: parameter object (usually string) to validate.
        allow_null: allow parameter pass the validation if the parameter is null.

    Returns:
        param_check_result. Ret of result may be an error message, or processed parameter.
    """

    ARRAY_SEPARATOR = "  "

    IMAGE_CONTENT_TYPE = ["image/jpeg", "image/png"]

    @staticmethod
    def base_null(obj, allow_null):
        if allow_null and (obj is None or obj == ''):
            return param_validation_result(None, True)

    @staticmethod
    def check_dict(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        try:
            obj = ast.literal_eval(obj)

            if not isinstance(obj, dict):
                return param_validation_result(error.main.miscellaneous(u'輸入參數必須是合法dictionary型別。({})'.format(type(obj))), False)

            return param_validation_result(obj, True)
        except ValueError as ex:
            return param_validation_result(error.main.miscellaneous(u'字串型別分析失敗。\n{}\n\n訊息: {}'.format(obj, ex.message)), False)

    @staticmethod
    def conv_unicode(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        try:
            return param_validation_result(unicode(obj).strip(), True)
        except Exception as ex:
            return param_validation_result(u'{} - {}'.format(type(ex), ex.message), False)

    @staticmethod
    def conv_unicode_lt2K(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        try:
            conv_unc = param_validator.conv_unicode(obj, allow_null)

            if conv_unc.success and len(conv_unc.result) > error.line_bot_api.MAX_CHARACTER_COUNT:
                return param_validation_result(error.line_bot_api.text_too_long(), False)
            else:
                return conv_unc
        except Exception as ex:
            return param_validation_result(u'{} - {}'.format(type(ex), ex.message), False)

    @staticmethod
    def conv_unicode_lower(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        try:
            return param_validation_result(param_validator.conv_unicode(obj, allow_null).result.lower(), True)
        except Exception as ex:
            return param_validation_result(u'{} - {}'.format(type(ex), ex.message), False)

    @staticmethod
    def conv_unicode_arr(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        try:
            return param_validation_result([param_validator.conv_unicode(o, allow_null).result for o in ext.to_list(obj.split(param_validator.ARRAY_SEPARATOR))], True)
        except Exception as ex:
            return param_validation_result(u'{} - {}'.format(type(ex), ex.message), False)

    @staticmethod
    def validate_https(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        validate_unicode = param_validator.conv_unicode(obj, allow_null)

        if validate_unicode.valid:
            obj = obj.split()[0]

            if obj.startswith('https://'):
                return param_validation_result(obj, True)
            else:
                return param_validation_result(error.sys_command.must_https(obj), False)
        else:
            return validate_unicode

    @staticmethod
    def validate_https_image(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base
        
        validate_https = param_validator.validate_https(obj, allow_null)

        if validate_https.valid:
            try:
                response = requests.head(obj)
                content_type = response.headers.get('content-type')

                err_msg = error.sys_command.must_https_image(obj, content_type)
                valid = content_type in param_validator.IMAGE_CONTENT_TYPE

                return param_validation_result(obj if valid else err_msg, valid)
            except Exception:
                return param_validation_result(err_msg, False)
        else:
            return validate_https

    @staticmethod
    def validate_sha224(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        try:
            obj = unicode(obj)
        except UnicodeDecodeError:
            obj = obj.decode('utf-8')
        except UnicodeEncodeError:
            obj = obj.encode('utf-8')

        if tool.regex.regex_finder.find_match([ur'(?:[0-9a-fA-F]{56})'], obj) is not None:
            return param_validator.conv_unicode(obj, allow_null)
        else:
            return param_validation_result(error.sys_command.must_sha(obj), False)

    @staticmethod
    def conv_int_gt_0(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        new_int = ext.to_int(obj)

        if new_int is not None:
            return param_validation_result(new_int, True)
        elif new_int < 0:
            return param_validation_result(error.sys_command.must_gt_0(obj), False)
        else:
            return param_validation_result(error.sys_command.must_int(obj), False)

    @staticmethod
    def valid_int(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        new_int = ext.to_int(obj)

        if new_int is not None:
            return param_validation_result(obj, True)
        else:
            return param_validation_result(error.sys_command.must_int(obj), False)

    @staticmethod
    def conv_int_arr(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        new_int = ext.to_int(ext.to_list(obj.split(param_validator.ARRAY_SEPARATOR)))

        if new_int is not None:
            return param_validation_result(new_int, True)
        else:
            return param_validation_result(error.sys_command.must_int(obj), False)

    @staticmethod
    def valid_int_arr(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        sp = ext.to_list(obj.split(param_validator.ARRAY_SEPARATOR))
        new_int = ext.to_int(sp)

        if new_int is not None:
            return param_validation_result(sp, True)
        else:
            return param_validation_result(error.sys_command.must_int(obj), False)

    @staticmethod
    def conv_int_lt_1m(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        res = param_validator.conv_int_gt_0(obj, allow_null)

        if res.success:
            sp_for_check = res.result

            if not isinstance(obj, (list, tuple)):
                sp_for_check = [sp_for_check]

            return param_validation_result(res.result, all(num < 1000000 for num in sp_for_check))
        else:
            return param_validation_result(error.sys_command.must_int(obj), False)

    @staticmethod
    def is_not_null(obj, allow_null):
        return param_validation_result(obj is not None, True)

    @staticmethod
    def text_to_bool(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        if any(cond == obj for cond in (u'有', '有', 'O', u'O')):
            return param_validation_result(True, True)
        elif any(cond == obj for cond in (u'無', '無', 'X', u'X')):
            return param_validation_result(False, True)
        else:
            raise UndefinedTextException(obj)

    @staticmethod
    def conv_float(obj, allow_null):
        base = param_validator.base_null(obj, allow_null)
        if base is not None:
            return base

        res = ext.string_to_float(obj)

        if res is not None:
            return param_validation_result(res, True)
        else:
            return param_validation_result(obj, False)

    class keyword_dict(object):
        @staticmethod
        def conv_pair_type_from_org(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            if any(obj.startswith(w) for w in (u'收到', u'回答', u'T')):
                ret = db.word_type.TEXT
            elif any(obj.startswith(w) for w in (u'看到', u'回圖', u'P')):
                ret = db.word_type.PICTURE
            elif any(obj.startswith(w) for w in (u'被貼', u'回貼', u'S')):
                ret = db.word_type.STICKER
            else:
                return param_validation_result(u'{} - {}'.format(type(ex), ex.message), False)

            return param_validation_result(ret, True)

        @staticmethod
        def get_type_auto(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            if param_validator.validate_https_image(obj, allow_null).valid or param_validator.validate_sha224(obj, allow_null).valid:
                ret = db.word_type.PICTURE
            elif param_validator.conv_int_gt_0(obj, allow_null).valid:
                ret = db.word_type.STICKER
            elif param_validator.conv_unicode(obj, allow_null).valid:
                ret = db.word_type.TEXT
            else:
                return param_validation_result(u'Object cannot be determined to any type. ({})'.format(obj), False)

            return param_validation_result(ret, True)

    class line_bot_api(object):
        @staticmethod
        def validate_cid(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            return param_validation_result(obj, bot.line_api_wrapper.is_valid_user_id(obj) or bot.line_api_wrapper.is_valid_room_group_id(obj))

        @staticmethod
        def validate_uid(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            return param_validation_result(obj, bot.line_api_wrapper.is_valid_user_id(obj))

        @staticmethod
        def validate_gid(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base
            
            return param_validation_result(obj, bot.line_api_wrapper.is_valid_room_group_id(obj))

        @staticmethod
        def validate_gid_public_global(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base
            
            return param_validation_result(obj, bot.line_api_wrapper.is_valid_room_group_id(obj, True, True))

    class special_category(object):
        @staticmethod
        def K_ranking_category(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_K_ranking_category(obj)
            t = err

            obj = obj.upper()

            if obj == u'使用者' or obj == u'USER':
                t = special_param.func_K.ranking_category.USER
            elif obj == u'使用過的' or obj == u'KWRC':
                t = special_param.func_K.ranking_category.RECENTLY_USED
            elif obj == u'回覆組' or obj == u'KW':
                t = special_param.func_K.ranking_category.KEYWORD

            return param_validation_result(t, t != err)

        @staticmethod
        def P_record_category(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_K_ranking_category(obj)
            t = err
            
            obj = obj.upper()

            if obj == u'自動回覆' or obj == u'KW':
                t = special_param.func_P.record_category.AUTO_REPLY
            elif obj == u'資訊' or obj == u'SYS':
                t = special_param.func_P.record_category.SYS_INFO
            elif obj == u'圖片' or obj == u'IMG':
                t = special_param.func_P.record_category.IMGUR_API
            elif obj == u'匯率' or obj == u'EXC':
                t = special_param.func_P.record_category.EXCHANGE_RATE
            elif obj == u'黑名單' or obj == u'BAN':
                t = special_param.func_P.record_category.BAN_LIST
            elif obj == u'資料庫' or obj == u'DB':
                t = special_param.func_P.record_category.DATABASE

            return param_validation_result(t, t != err)

        @staticmethod
        def GA_group_range(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_GA_group_config(obj)
            t = err

            if obj == u'啞巴' or obj == u'0':
                t = db.group_data_range.SILENCE
            elif obj == u'機器人' or obj == u'1':
                t = db.group_data_range.SYS_ONLY
            elif obj == u'服務員' or obj == u'2':
                t = db.group_data_range.GROUP_DATABASE_ONLY
            elif obj == u'八嘎囧' or obj == u'3':
                t = db.group_data_range.ALL

            return param_validation_result(t, t != err)

        @staticmethod
        def GA2_permission(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_GA2_permission(obj)
            t = err

            if obj == u'可憐兒' or obj == u'-1':
                t = bot.permission.RESTRICTED
            elif obj == u'一般人' or obj == u'0':
                t = bot.permission.USER
            elif obj == u'副管' or obj == u'1':
                t = bot.permission.MODERATOR
            elif obj == u'管理員' or obj == u'2':
                t = bot.permission.ADMIN

            return param_validation_result(t, t != err)
        
        @staticmethod
        def GA3_validate_token(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            return param_validation_result(obj, tool.regex.regex_finder.find_match([ur'.*(?:[A-Z0-9]{40}).*'], obj) is None)

        @staticmethod
        def L_category(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_L_category(obj)
            t = err
            
            obj = obj.upper()

            if obj == u'貼圖' or obj == u'S':
                t = bot.system_data_category.LAST_STICKER
            elif obj == u'圖片' or obj == u'P':
                t = bot.system_data_category.LAST_PIC_SHA
            elif obj == u'回覆組' or obj == u'R':
                t = bot.system_data_category.LAST_PAIR_ID
            elif obj == u'發送者' or obj == u'U':
                t = bot.system_data_category.LAST_UID
            elif obj == u'訊息' or obj == u'M':
                t = bot.system_data_category.LAST_MESSAGE

            return param_validation_result(t, t != err)

        @staticmethod
        def C_validate_currency_symbols(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            l = len(obj)
            regex_valid = tool.regex.regex_finder.find_match([ur'([A-Z ]{3, })'], obj) is not None

            if regex_valid and (l == 3 or (l >= 3 and l % 3 == 2)):
                return param_validator.conv_unicode_arr(obj, allow_null)
            else:
                return param_validation_result(error.sys_command.func_C_currency_symbol_unrecognizable(obj), False)

        @staticmethod
        def C_validate_currency_symbol(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            if tool.regex.regex_finder.find_match([ur'([A-Z]{3})'], obj) is not None:
                return param_validator.conv_unicode(obj, allow_null)
            else:
                return param_validation_result(error.sys_command.func_C_currency_symbol_unrecognizable(obj), False)

        @staticmethod
        def C_validate_date(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            return param_validation_result(obj, tool.regex.regex_finder.find_match([ur'(?:(?:1999|20\d{2})(?:0[1-9]|1[1-2])(?:[0-2][1-9]|3[0-1]))'], obj) is not None)

        @staticmethod
        def W_output_type(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_W_output_type(obj)
            t = err
            
            obj = obj.upper()

            if obj == u'詳細' or obj == u'詳' or obj == u'D':
                t = tool.weather.output_type.DETAIL
            elif obj == u'簡潔' or obj == u'簡' or obj == u'S':
                t = tool.weather.output_type.SIMPLE

            return param_validation_result(t, t != err)

        @staticmethod
        def W_action(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_W_action(obj)
            t = err
            
            obj = obj.upper()

            if obj == u'新增' or obj == u'A':
                t = special_param.func_W.action_category.ADD_TRACK
            elif obj == u'刪除' or obj == u'D':
                t = special_param.func_W.action_category.DEL_TRACK
            elif obj == u'查詢' or obj == u'ID':
                t = special_param.func_W.action_category.GET_DATA

            return param_validation_result(t, t != err)

        @staticmethod
        def X_pinned(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base
            
            obj = obj.upper()

            t = obj == u'P' or obj == u'包含置頂'

            return param_validation_result(t, True)

        @staticmethod
        def X_deleted(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base
            
            obj = obj.upper()

            t = obj == u'D' or obj == u'包含已刪除'

            return param_validation_result(t, True)

        @staticmethod
        def STK_action_category(obj, allow_null):
            base = param_validator.base_null(obj, allow_null)
            if base is not None:
                return base

            err = error.sys_command.unknown_func_STK_ranking_category(obj)
            t = err
            
            obj = obj.upper()

            if obj == u'貼圖圖包' or obj == u'PKG':
                t = db.ranking_category.PACKAGE
            elif obj == u'貼圖' or obj == u'STK':
                t = db.ranking_category.STICKER

            return param_validation_result(t, t != err)

class param_validation_result(ext.action_result):
    def __init__(self, ret, valid):
        super(param_validation_result, self).__init__(ret, valid)

    @property
    def ret(self):
        return self._result

    @property
    def valid(self):
        return self._success

class special_param(object):
    class func_K(object):
        class ranking_category(ext.EnumWithName):
            KEYWORD = 1, '關鍵字排名'
            RECENTLY_USED = 2, '最近使用'
            USER = 3, '使用者'

    class func_P(object):
        class record_category(ext.EnumWithName):
            AUTO_REPLY = 1, '關鍵字排名'
            SYS_INFO = 2, '最近使用'
            IMGUR_API = 3, '使用者'
            EXCHANGE_RATE = 4, '匯率轉換'
            BAN_LIST = 5, '黑名單'
            DATABASE = 6, '資料庫'

    class func_W(object):
        class action_category(ext.EnumWithName):
            ADD_TRACK = 0, '新增追蹤項目'
            DEL_TRACK = 1, '刪除追蹤項目'
            GET_DATA = 2, '獲取資料'

class UndefinedCommandCategoryException(Exception):
    def __init__(self, *args):
        return super(UndefinedCommandCategoryException, self).__init__(*args)

class UndefinedActionException(Exception):
    def __init__(self, *args):
        return super(UndefinedActionException, self).__init__(*args)

class UndefinedParameterException(Exception):
    def __init__(self, *args):
        return super(UndefinedParameterException, self).__init__(*args)

class UndefinedPackedStatusException(Exception):
    def __init__(self, *args):
        return super(UndefinedPackedStatusException, self).__init__(*args)

class UndefinedTextException(Exception):
    def __init__(self, *args):
        return super(UndefinedTextException, self).__init__(*args)
# -*- coding: utf-8 -*-
import os
import requests

import hashlib
from datetime import datetime, timedelta
import re

import bot, db, ext, tool, game
from error import error, warning

from .param import param_packer
from .param_base import (
    special_param, param_validator, 
    UndefinedCommandCategoryException, UndefinedActionException
)

class command_handler_collection(object):
    @staticmethod
    def replace_newline(text):
        if isinstance(text, unicode):
            return text.replace(u'\\n', u'\n')
        elif isinstance(text, str):
            return text.replace('\\n', '\n')
        elif isinstance(text, list):
            return [t.replace(u'\\n', u'\n') for t in text]
        else:
            return text

    class _S(object):
        def __init__(self, mongo_client, packing_result):
            self._mongo_client = mongo_client
            self._packing_result = packing_result

        def generate_output_head(self):
            text = u'目標資料庫:\n{}\n'.format(self._packing_result.result[param_packer.func_S.param_category.DB_NAME])
            text += u'資料庫主指令:\n{}\n'.format(self._packing_result.result[param_packer.func_S.param_category.MAIN_CMD])
            text += u'資料庫主指令參數:\n{}\n'.format(self._packing_result.result[param_packer.func_S.param_category.MAIN_PRM])
            text += u'資料庫副指令:\n{}\n\n'.format(self._packing_result.result[param_packer.func_S.param_category.OTHER_PRM])

            return text

        def generate_output_mongo_result(self):
            return ext.object_to_json(self.execute_mongo_shell())

        def execute_mongo_shell(self):
            return self._mongo_client.get_database(self._packing_result.result[param_packer.func_S.param_category.DB_NAME]) \
                                     .command(self._packing_result.result[param_packer.func_S.param_category.MAIN_CMD], 
                                              self._packing_result.result[param_packer.func_S.param_category.MAIN_PRM], 
                                              **self._packing_result.result[param_packer.func_S.param_category.OTHER_PRM])

    class _A(object):
        def __init__(self, packing_result):
            self._packing_result = packing_result

        def add_kw(self, kwd_instance, pinned, adder_uid):
            param_dict = self._packing_result.result

            rcv_type_result = self._get_rcv_type()
            rcv_content = command_handler_collection.replace_newline(self._get_rcv_content())
            rep_type_result = self._get_rep_type()
            rep_content = command_handler_collection.replace_newline(self._get_rep_content())
            rep_attachment = command_handler_collection.replace_newline(self._get_rep_attachment())

            if not rcv_type_result.success:
                return rcv_type_result.result

            if not rep_type_result.success:
                return rep_type_result.result

            # create and write
            result = kwd_instance.insert_keyword(rcv_content, rep_content, adder_uid, pinned, rcv_type_result.result, rep_type_result.result, None, rep_attachment)

            return ext.action_result(result, isinstance(result, db.pair_data))

        def generate_output(self, kwd_add_result):
            if kwd_add_result.success:
                if isinstance(kwd_add_result.result, (str, unicode)):
                    return result
                elif isinstance(kwd_add_result.result, db.pair_data):
                    return u'回覆組新增成功。\n' + kwd_add_result.result.basic_text(True)
                else:
                    raise ValueError('Unhandled type of return result. ({} - {})'.format(type(kwd_add_result.result), kwd_add_result.result))
            else:
                return u'回覆組新增失敗。\n\n{}'.format(kwd_add_result.result)

        def _is_auto_detect(self):
            return any(self._packing_result.command_category == cat for cat in (param_packer.func_A.command_category.ADD_PAIR_AUTO_CH, param_packer.func_A.command_category.ADD_PAIR_AUTO_EN))

        def _get_rcv_type(self):
            param_dict = self._packing_result.result
            if self._is_auto_detect():
                return param_validator.keyword_dict.get_type_auto(param_dict[param_packer.func_A.param_category.RCV_CONTENT], False)
            else:
                return ext.action_result(param_dict[param_packer.func_A.param_category.RCV_TYPE], True)

        def _get_rep_type(self):
            param_dict = self._packing_result.result
            if self._is_auto_detect():
                return param_validator.keyword_dict.get_type_auto(param_dict[param_packer.func_A.param_category.REP_CONTENT], False)
            else:
                return ext.action_result(param_dict[param_packer.func_A.param_category.REP_TYPE], True)

        def _get_rcv_content(self):
            param_dict = self._packing_result.result
            cmd_cat = self._packing_result.command_category

            if self._is_auto_detect():
                return param_dict[param_packer.func_A.param_category.RCV_CONTENT]
            else:
                if param_dict[param_packer.func_A.param_category.RCV_TYPE] == db.word_type.TEXT:
                    t = param_dict[param_packer.func_A.param_category.RCV_TXT]

                    if cmd_cat == param_packer.func_A.command_category.ADD_PAIR_AUTO_EN:
                        t = command_handler_collection.replace_newline(t)

                    return t
                elif param_dict[param_packer.func_A.param_category.RCV_TYPE] == db.word_type.STICKER:
                    return param_dict[param_packer.func_A.param_category.RCV_STK]
                elif param_dict[param_packer.func_A.param_category.RCV_TYPE] == db.word_type.PICTURE:
                    return param_dict[param_packer.func_A.param_category.RCV_PIC]

        def _get_rep_content(self):
            param_dict = self._packing_result.result
            cmd_cat = self._packing_result.command_category

            if self._is_auto_detect():
                return param_dict[param_packer.func_A.param_category.REP_CONTENT]
            else:
                if param_dict[param_packer.func_A.param_category.REP_TYPE] == db.word_type.TEXT:
                    t = param_dict[param_packer.func_A.param_category.REP_TXT]

                    if cmd_cat == param_packer.func_A.command_category.ADD_PAIR_AUTO_EN:
                        t = command_handler_collection.replace_newline(t)

                    return t
                elif param_dict[param_packer.func_A.param_category.REP_TYPE] == db.word_type.STICKER:
                    return param_dict[param_packer.func_A.param_category.REP_STK]
                elif param_dict[param_packer.func_A.param_category.REP_TYPE] == db.word_type.PICTURE:
                    return param_dict[param_packer.func_A.param_category.REP_PIC]

        def _get_rep_attachment(self):
            param_dict = self._packing_result.result

            return param_dict[param_packer.func_A.param_category.ATTACHMENT]

    class _D(object):
        def __init__(self, packing_result):
            self._packing_result = packing_result

        def del_kw(self, kwd_instance, pinned, executor_uid):
            param_dict = self._packing_result.result
            if param_dict[param_packer.func_D.param_category.IS_ID]:
                disabled_data = kwd_instance.disable_keyword_by_id(param_dict[param_packer.func_D.param_category.ID], executor_uid, pinned)
            else:
                disabled_data = kwd_instance.disable_keyword(command_handler_collection.replace_newline(param_dict[param_packer.func_D.param_category.WORD]), executor_uid, pinned)

            return ext.action_result(disabled_data, len(disabled_data) > 0)

        def generate_output(self, del_result):
            if del_result.success:
                text = u'回覆組刪除成功。\n'
                text += '\n'.join([data.basic_text(True) for data in del_result.result])
                return text
            else:
                return error.main.miscellaneous(error.main.pair_not_exist_or_insuffieicnt_permission() + u'若欲使用ID作為刪除根據，請參閱小水母使用說明。')

    class _Q(object):
        def __init__(self, config_manager, webpage_generator):
            self._config_manager = config_manager
            self._webpage_generator = webpage_generator

        def generate_output(self, query_result):
            if query_result.success:
                max_count = self._config_manager.getint(bot.config.config_category.KEYWORD_DICT, bot.config.config_category_kw_dict.MAX_QUERY_OUTPUT_COUNT)
                str_length = self._config_manager.getint(bot.config.config_category.KEYWORD_DICT, bot.config.config_category_kw_dict.MAX_SIMPLE_STRING_LENGTH)

                title, data = query_result.result

                output = db.keyword_dict.group_dict_manager.list_keyword(data, max_count, title, error.main.no_result(), str_length)

                text = output.limited
                if output.has_result:
                    text += u'\n\n完整結果: {}'.format(self._webpage_generator.rec_webpage(output.full, db.webpage_content_type.QUERY))
                return text
            else:
                return unicode(query_result.result)

    class _I(object):
        def __init__(self, line_wrapper, config_manager, webpage_generator):
            self._line_api_wrapper = line_wrapper
            self._config_manager = config_manager
            self._webpage_generator = webpage_generator

        def generate_output(self, kwd_instance, query_result):
            if query_result.success:
                max_count = self._config_manager.getint(bot.config.config_category.KEYWORD_DICT, bot.config.config_category_kw_dict.MAX_INFO_OUTPUT_COUNT)
                
                title, data = query_result.result

                output = db.keyword_dict.group_dict_manager.list_keyword_info(data, kwd_instance, self._line_api_wrapper, 
                                                                              max_count, title.replace('\n', ''),  error.main.no_result())

                text = output.limited
                if output.has_result:
                    text += u'\n\n完整結果: {}'.format(self._webpage_generator.rec_webpage(output.full, db.webpage_content_type.INFO))
                return text
            else:
                return unicode(query_result.result)

    class _X(object):
        def __init__(self, webpage_generator, kwd_global, packing_result):
            self._webpage_generator = webpage_generator
            self._kwd_global = kwd_global
            self._packing_result = packing_result

        def clone(self, execute_in_gid, executor_uid, executor_permission):
            cmd_cat = self._packing_result.command_category
            param_dict = self._packing_result.result

            copy_pinned = self._copy_pinned(executor_permission, param_dict[param_packer.func_X.param_category.WITH_PINNED])
            copy_deleted = param_dict[param_packer.func_X.param_category.WITH_DELETED]

            if not copy_pinned.success:
                return ext.action_result(copy_pinned.result, False)

            target_gid_result = self._get_target_gid(execute_in_gid)

            if not target_gid_result.success:
                return ext.action_result(target_gid_result.result, False)

            if cmd_cat == param_packer.func_X.command_category.BY_ID_WORD:
                if param_dict[param_packer.func_X.param_category.IS_ID]:
                    return ext.action_result(self._kwd_global.clone_by_id(param_dict[param_packer.func_X.param_category.ID], target_gid_result.result, executor_uid, copy_deleted, copy_pinned.result), True)
                else:
                    return ext.action_result(self._kwd_global.clone_by_word(param_dict[param_packer.func_X.param_category.KEYWORD], target_gid_result.result, executor_uid, copy_deleted, copy_pinned.result), True)
            elif cmd_cat == param_packer.func_X.command_category.BY_GID:
                src_id_result = self._get_source_gid(execute_in_gid)
                if not src_id_result.success:
                    return ext.action_result(src_id_result.result, False)

                return ext.action_result(self._kwd_global.clone_from_group(src_id_result.result, target_gid_result.result, executor_uid, False, copy_pinned.result), True)

        def generate_output(self, clone_result):
            if clone_result.success:
                cloned_ids = clone_result.result

                if len(cloned_ids) > 0:
                    first_id_str = str(cloned_ids[0])
                    last_id_str = str(cloned_ids[-1])
                    return [bot.line_api_wrapper.wrap_text_message(u'回覆組複製完畢。\n新建回覆組ID: {}'.format(u'、'.join([u'#{}'.format(id) for id in cloned_ids])), self._webpage_generator),
                            bot.line_api_wrapper.wrap_template_with_action({
                                u'回覆組資料查詢(簡略)': bot.text_msg_handler.CH_HEAD + u'找ID範圍' + first_id_str + u'到' + last_id_str,
                                u'回覆組資料查詢(詳細)': bot.text_msg_handler.CH_HEAD + u'詳細找ID範圍' + first_id_str + u'到' + last_id_str } ,u'新建回覆組相關指令樣板', u'相關指令')]
                else:
                    return error.sys_command.no_available_target_pair()
            else:
                return unicode(clone_result.result)

        def _get_source_gid(self, execute_in_gid):
            param_dict = self._packing_result.result

            if param_dict[param_packer.func_X.param_category.SOURCE_GID] is not None:
                ret = param_dict[param_packer.func_X.param_category.SOURCE_GID]
                if ret == execute_in_gid:
                    return ext.action_result(error.sys_command.same_source_target(ret), False)
                else:
                    return ext.action_result(ret, True)
            else:
                return ext.action_result(execute_in_gid, True)

        def _get_target_gid(self, execute_in_gid):
            if bot.line_api_wrapper.is_valid_user_id(execute_in_gid):
                return ext.action_result(bot.remote.PUBLIC_TOKEN(), True)
            else:
                return ext.action_result(execute_in_gid, True)

        def _copy_pinned(self, executor_permission, user_wants_copy):
            required_perm = bot.permission.MODERATOR

            if user_wants_copy:
                if executor_permission >= required_perm:
                    return ext.action_result(True, True)
                else:
                    return ext.action_result(error.permission.restricted(required_perm), False)
            else:
                return ext.action_result(False, True)

    class _X2(object):
        def __init__(self, executor_gid, executor_uid, executor_permission, kwd_global):
            self._executor_gid = executor_gid
            self._executor_uid = executor_uid
            self._executor_permission = executor_permission
            self._lowest_permission = bot.permission.ADMIN
            self._kwd_global = kwd_global

        def _allow_deletion(self):
            return self._executor_permission >= self._lowest_permission

        def generate_output(self):
            if self._allow_deletion():
                clear_count = self._kwd_global.clear(self._executor_gid, self._executor_uid)

                if clear_count > 0:
                    return u'已刪除群組所屬回覆組(共{}組)。'.format(clear_count)
                else:
                    return u'沒有刪除任何回覆組。'
            else:
                return error.permission.restricted(self._lowest_permission)

    class _E(object):
        def __init__(self, webpage_generator, packing_result):
            self._webpage_generator = webpage_generator
            self._packing_result = packing_result

        def mod_linked(self, executor_permission, kwd_instance):
            param_dict = self._packing_result.result

            is_add = param_dict[param_packer.func_E.param_category.HAS_LINK]
            mod_pin = self._able_to_mod_pinned(executor_permission)

            if param_dict[param_packer.func_E.param_category.IS_ID]:
                if is_add:
                    result = kwd_instance.add_linked_word_by_id(param_dict[param_packer.func_E.param_category.ID], param_dict[param_packer.func_E.param_category.LINKED], mod_pin)
                else:
                    result = kwd_instance.del_linked_word_by_id(param_dict[param_packer.func_E.param_category.ID], param_dict[param_packer.func_E.param_category.LINKED], mod_pin)
            else:
                if is_add:
                    result = kwd_instance.add_linked_word_by_word(param_dict[param_packer.func_E.param_category.KEYWORD], param_dict[param_packer.func_E.param_category.LINKED], mod_pin)
                else:
                    result = kwd_instance.del_linked_word_by_word(param_dict[param_packer.func_E.param_category.KEYWORD], param_dict[param_packer.func_E.param_category.LINKED], mod_pin)

            return ext.action_result(None, result)

        def generate_output_mod_pinned(self, pin_result):
            expr = self._generate_expr()

            if pin_result.success:
                return (bot.line_api_wrapper.wrap_text_message(u'{} 置頂屬性變更成功。'.format(expr), self._webpage_generator), self._generate_shortcut_template())
            else:
                return u'{} 置頂屬性變更失敗。可能是因為ID不存在、回覆組已經置頂/無置頂 或 權限不足而造成。'.format(expr)

        def generate_output_mod_linked(self, mod_result):
            expr = self._generate_expr()

            if mod_result.success:
                return (bot.line_api_wrapper.wrap_text_message(u'{} 相關回覆組變更成功。'.format(expr), self._webpage_generator), self._generate_shortcut_template())
            else:
                return u'{} 相關回覆組變更失敗。可能是因為ID不存在或權限不足而造成。'.format(expr)

        def _able_to_mod_pinned(self, executor_permission):
            return executor_permission >= bot.permission.MODERATOR

        def mod_pinned(self, executor_permission, kwd_instance):
            param_dict = self._packing_result.result

            mod_pin = self._able_to_mod_pinned(executor_permission)

            if param_dict[param_packer.func_E.param_category.IS_ID]:
                result = kwd_instance.set_pinned_by_index(param_dict[param_packer.func_E.param_category.ID], mod_pin and not param_dict[param_packer.func_E.param_category.NOT_PIN])
            else:
                result = kwd_instance.set_pinned_by_keyword(param_dict[param_packer.func_E.param_category.KEYWORD], mod_pin and not param_dict[param_packer.func_E.param_category.NOT_PIN])

            return ext.action_result(None, result)

        def _generate_shortcut_template(self):
            param_dict = self._packing_result.result

            expr = self._generate_expr()

            if param_dict[param_packer.func_E.param_category.IS_ID]:
                target_array = param_dict[param_packer.func_E.param_category.ID]
                shortcut_template = bot.line_api_wrapper.wrap_template_with_action({ '回覆組詳細資訊(#{})'.format(id): bot.text_msg_handler.CH_HEAD + u'詳細找ID {}'.format(id) for id in target_array },     u'更動回覆組ID: {}'.format(expr), u'相關指令')
            else:
                target_array = param_dict[param_packer.func_E.param_category.KEYWORD]
                shortcut_template = bot.line_api_wrapper.wrap_template_with_action({ '回覆組詳細資訊({})'.format(kw): bot.text_msg_handler.CH_HEAD + u'詳細找{}'.format(kw) for kw in target_array }, u'更動回覆組: {}'.format(expr), u'相關指令')

            return shortcut_template

        def _generate_expr(self):
            param_dict = self._packing_result.result

            if param_dict[param_packer.func_E.param_category.IS_ID]:
                target_array = param_dict[param_packer.func_E.param_category.ID]
                expr = u'、'.join([u'#{}'.format(str(id)) for id in target_array])
            else:
                target_array = param_dict[param_packer.func_E.param_category.KEYWORD]
                expr = u'關鍵字: ' + u'、'.join(target_array)

            return expr

    class _K(object):
        def __init__(self, config_manager, packing_result):
            self._config_manager = config_manager
            self._packing_result = packing_result

        def get_limit(self):
            prm_dict = self._packing_result.result

            default = self._default_limit()
            limit_count = prm_dict[param_packer.func_K.param_category.COUNT] 

            if limit_count is None:
                return default
            else:
                return limit_count

        def _default_limit(self):
            return self._config_manager.getint(bot.config_category.KEYWORD_DICT, bot.config_category_kw_dict.DEFAULT_RANK_RESULT_COUNT)

    class _P(object):
        def __init__(self, webpage_generator, config_manager, system_data, system_stats, group_manager, 
                     loop_preventer, oxr_client, imgur_api, db_measurement, packing_result):
            self._webpage_generator = webpage_generator
            self._config_manager = config_manager
            self._system_data = system_data
            self._system_stats = system_stats
            self._group_manager = group_manager
            self._loop_prev = loop_preventer
            self._oxr_client = oxr_client
            self._imgur_api_wrapper = imgur_api
            self._packing_result = packing_result

            self._db_measurement = db_measurement

        def generate_output_sys_rec(self, kwd_instance):
            rec_cat = self._packing_result.result[param_packer.func_P.param_category.CATEGORY]

            if rec_cat == special_param.func_P.record_category.AUTO_REPLY:
                instance_type = u'{}回覆組資料庫'.format(unicode(kwd_instance.available_range))
                return u'【{}相關統計資料】\n'.format(instance_type) + kwd_instance.get_statistics_string()
            elif rec_cat == special_param.func_P.record_category.BAN_LIST:
                text = u'【暫時封鎖清單】\n以下使用者因洗板疑慮，已暫時封鎖指定使用者對小水母的所有操控。輸入驗證碼以解除鎖定。\n此清單將在小水母重新開啟後自動消除。\n系統開機時間: {}\n\n'.format       (self._system_data.boot_up)
                text += self._loop_prev.get_all_banned_str()

                return text
            elif rec_cat == special_param.func_P.record_category.EXCHANGE_RATE:
                return self._oxr_client.usage_str(self._oxr_client.get_usage_dict())
            elif rec_cat == special_param.func_P.record_category.IMGUR_API:
                import socket
                ip_address = socket.gethostbyname(socket.getfqdn(socket.gethostname()))

                return self._imgur_api_wrapper.get_status_string(ip_address)
            elif rec_cat == special_param.func_P.record_category.SYS_INFO:
                text = u'【系統統計資料】\n'
                text += u'開機時間: {} (UTC+8)\n\n'.format(self._system_data.boot_up)
                text += self._system_stats.get_statistics()

                return text
            elif rec_cat == special_param.func_P.record_category.DATABASE:
                text = u'【資料庫狀態 - Mongo DB Atlas】\n'
                text += self._db_measurement.get_measurement_data().to_string()
                text += u'\n\n'
                text += u'(12小時前)\n'
                text += self._db_measurement.get_measurement_data(db.data_range.IN_12HR).to_string()

                return text
            else:
                return error.sys_command.unknown_func_P_record_category(rec_cat)

        def generate_output_msg_track(self, data):
            limit = self._get_msg_track_data_count()

            tracking_string_obj = db.group_manager.message_track_string(data, limit, [u'【訊息流量統計】(前{}名)'.format(limit)], error.main.miscellaneous(u'沒有訊息量追蹤紀錄。'), True, True,    self._group_manager.message_sum())
            
            return u'為避免訊息過長造成洗板，請點此察看結果:\n{}'.format(self._webpage_generator.rec_webpage(tracking_string_obj.full, db.webpage_content_type.TEXT))

        def get_msg_track_data(self):
            limit = self._get_msg_track_data_count()

            return self._group_manager.order_by_recorded_msg_count(limit)

        def _get_msg_track_data_count(self):
            prm_dict = self._packing_result.result

            default = self._config_manager.getint(bot.config.config_category.KEYWORD_DICT, bot.config.config_category_kw_dict.MAX_MESSAGE_TRACK_OUTPUT_COUNT)
            count = prm_dict[param_packer.func_P.param_category.COUNT]

            if count is None:
                return default
            else:
                return count

    class _P2(object):
        def __init__(self, line_api_wrapper, webpage_generator, kwd_instance, group_manager, packing_result):
            self._line_api_wrapper = line_api_wrapper
            self._webpage_generator = webpage_generator
            self._kwd_instance = kwd_instance
            self._group_manager = group_manager
            self._packing_result = packing_result

        def get_profile_name(self, src, execute_in_gid):
            uid = self._packing_result.result[param_packer.func_P2.param_category.UID]

            try:
                if execute_in_gid != bot.line_api_wrapper.source_channel_id(src):
                    source_type = bot.line_api_wrapper.determine_id_type(execute_in_gid)

                    if source_type == bot.line_event_source_type.GROUP:
                        name = self._line_api_wrapper.profile_group(execute_in_gid, uid).display_name
                    elif source_type == bot.line_event_source_type.ROOM:
                        name = self._line_api_wrapper.profile_room(execute_in_gid, uid).display_name
                    else:
                        name = self._line_api_wrapper.profile_name(uid, src)
                else:
                    name = self._line_api_wrapper.profile_name(uid, src)

                return ext.action_result(name, True)
            except bot.UserProfileNotFoundError:
                return ext.action_result(None, False)

        def generate_output(self, get_name_result):
            if get_name_result.success:
                uid = self._packing_result.result[param_packer.func_P2.param_category.UID]
                name = get_name_result.result

                created_id_arr = u'、'.join([str(id) for id in self._kwd_instance.user_created_id_array(uid)])
                owned_permission = u'\n'.join([u'{}: {}'.format(u_data.group, unicode(u_data.permission_level)) for u_data in self._group_manager.get_user_owned_permissions(uid)])

                text = u'UID:\n{}\n\n名稱:\n{}\n\n擁有權限:\n{}\n\n製作回覆組ID (共{}組):\n{}'.format(uid, name, owned_permission, len(created_id_arr), created_id_arr)

                return [bot.line_api_wrapper.wrap_text_message(text, self._webpage_generator), 
                        bot.line_api_wrapper.wrap_template_with_action({ u'查詢該使用者製作的回覆組': bot.text_msg_handler.CH_HEAD + u'找' + uid + u'做的' }, u'回覆組製作查詢快捷樣板', u'快捷查詢')]
            else:
                return bot.line_api_wrapper.wrap_text_message(error.main.line_account_data_not_found(), self._webpage_generator)

    class _G(object):
        def __init__(self, webpage_generator, last_chat_rec, packing_result, src):
            self._webpage_generator = webpage_generator
            self._packing_result = packing_result
            self._last_chat_rec = last_chat_rec
            self._src = src

        def get_group_id(self, execute_in_gid):
            gid = self._packing_result.result[param_packer.func_G.param_category.GID]

            if gid is None:
                if not bot.line_api_wrapper.is_valid_room_group_id(execute_in_gid):
                    return ext.action_result(error.main.incorrect_channel(False, True, True), False)
                else:
                    gid = execute_in_gid

            return ext.action_result(gid, True)

        def generate_output(self, gid_result, kwd_instance, group_data):
            group_statistics = group_data.get_status_string() + u'\n【回覆組相關】\n' + kwd_instance.get_statistics_string() + u'\n\n【最後訊息時間】\n' + self._last_chat_rec.last_chat_str(gid_result.result, src)
            
            return (bot.line_api_wrapper.wrap_text_message(group_statistics, self._webpage_generator), 
                    bot.line_api_wrapper.wrap_template_with_action({ u'查詢群組資料庫': bot.text_msg_handler.CH_HEAD + u'找' + gid_result.result + u'裡面的'}, u'快速查詢群組資料庫樣板', u'相關指令'))

    class _GA(object):
        def __init__(self, group_manager, packing_result):
            self._group_manager = group_manager
            self._packing_result = packing_result

        def set_config_type(self, group_id, executor_permission):
            """Return true if successfully changed"""
            if executor_permission >= bot.permission.MODERATOR:
                group_config = self._packing_result.result[param_packer.func_GA.param_category.RANGE]
                return self._group_manager.set_config_type(group_id, group_config)
            else:
                return False
            
        def generate_output(self, is_succeed):
            group_config = self._packing_result.result[param_packer.func_GA.param_category.RANGE]
            if is_succeed:
                return u'我變成{}了哦！'.format(unicode(group_config))
            else:
                return u'你又不是管理員，我憑甚麼聽你的話去當{}啊？蛤？裝大咖的廢物，87'.format(unicode(group_config))

    class _GA2(object):
        def __init__(self, line_api_wrapper, group_manager, pack_result):
            self._line_api_wrapper = line_api_wrapper
            self._group_manager = group_manager
            self._pack_result = pack_result

        def generate_output(self, src, execute_in_gid):
            setter_uid = bot.line_api_wrapper.source_user_id(src)
            try:
                setter_name = self._line_api_wrapper.profile_name(setter_uid)
            except bot.UserProfileNotFoundError:
                return error.line_bot_api.unable_to_receive_user_id()

            target_uid = self._pack_result.result[param_packer.func_GA2.param_category.UID]
            try:
                target_name = self._line_api_wrapper.profile_name(target_uid)
            except bot.UserProfileNotFoundError:
                return error.main.miscellaneous(u'無法查詢權限更動目標的使用者資料。請先確保更動目標已加入小水母的好友以後再試一次。')

            permission = self._pack_result.result[param_packer.func_GA2.param_category.PERMISSION]

            if not bot.line_api_wrapper.is_valid_user_id(target_uid):
                return error.line_bot_api.illegal_user_id(target_uid)
            
            try:
                if permission == bot.permission.USER:
                    self._group_manager.delete_permission(execute_in_gid, setter_uid, target_uid)
                    return u'權限刪除成功。\n執行者: {}\n執行者UID: {}\n目標: {}\n目標UID: {}'.format(setter_uid, setter_name, target_name, target_uid)
                else:
                    self._group_manager.set_permission(execute_in_gid, setter_uid, target_uid, permission)
                    return u'權限更改/新增成功。\n執行者: {}\n執行者UID: {}\n目標: {}\n目標UID: {}\n新權限: {}'.format(setter_name, setter_uid, target_name, target_uid, unicode(permission))
            except db.InsufficientPermissionError:
                return error.permission.restricted()

    class _GA3(object):
        def __init__(self, group_manager, packing_result):
            self._group_manager = group_manager
            self._packing_result = packing_result

        def activate(self, execute_in_gid):
            return self._group_manager.activate(execute_in_gid, self._packing_result.result[param_packer.func_GA3.param_category.ACTIVATE_TOKEN])

        def generate_output(self, is_succeed):
            return u'公用資料庫啟用{}。'.format(u'成功' if is_succeed else u'失敗')

    class _H(object):
        def __init__(self, webpage_generator):
            self._webpage_generator = webpage_generator

        def get_channel_info(self, src):
            channel_id = bot.line_api_wrapper.source_channel_id(src)

            return [bot.line_api_wrapper.wrap_text_message(txt, self._webpage_generator) for txt in (str(bot.line_event_source_type.determine(src)), channel_id)]

    class _L(object):
        def __init__(self, system_data, webpage_generator, packing_result):
            self._system_data = system_data
            self._webpage_generator = webpage_generator
            self._packing_result = packing_result

        def get_last_data_array(self, execute_in_gid):
            action_type = self._packing_result.result[param_packer.func_L.param_category.CATEGORY]

            return self._system_data.get(action_type, execute_in_gid)

        def generate_txt_output(self, array):
            action_type = self._packing_result.result[param_packer.func_L.param_category.CATEGORY]

            if array is not None and len(array) > 0:
                return bot.line_api_wrapper.wrap_text_message(
                    u'{} (資料保存{}秒)\n{}'.format(
                        unicode(action_type), 
                        bot.system_data.EXPIRE_SEC, 
                        u'\n'.join(
                            [u'【{}】\n{}'.format((datetime.fromtimestamp(ts) + timedelta(hours=8)).strftime(u'%Y-%m-%d %H:%M:%S'), item) for ts, item in array.iteritems()])),
                    self._webpage_generator)
            else:
                return bot.line_api_wrapper.wrap_text_message(error.main.miscellaneous(u'沒有登記到本頻道的{}，有可能是因為機器人重新啟動，或所有資料紀錄已逾時({}秒)而造成。\n\n本次開機時間: {}'.format(unicode(action_type), bot.system_data.EXPIRE_SEC, self._system_data.boot_up)), self._webpage_generator)

        def generate_template_output(self, array):
            """Return none if array is empty"""
            if array is not None and len(array) > 0:
                action_type = self._packing_result.result[param_packer.func_L.param_category.CATEGORY]

                items_iterator = array.itervalues()

                if action_type == bot.system_data_category.LAST_STICKER:
                    action_dict = {}
                    for item in items_iterator:
                        stk_id = str(item.sticker_id)
                        pkg_id = str(item.package_id)
                        action_dict['簡潔 - {}'.format(stk_id)] = bot.text_msg_handler.CH_HEAD + u'找' + stk_id
                        action_dict['詳細 - {}'.format(stk_id)] = bot.text_msg_handler.CH_HEAD + u'詳細找' + stk_id
                        action_dict['貼圖包下載 - {}'.format(pkg_id)] = bot.text_msg_handler.CH_HEAD + u'下載貼圖圖包' + pkg_id
                elif action_type == bot.system_data_category.LAST_PAIR_ID:
                    action_dict = {}
                    for item in items_iterator:
                        item = str(item)
                        action_dict['簡潔 - {}'.format(item)] = bot.text_msg_handler.CH_HEAD + u'找ID ' + item
                        action_dict['詳細 - {}'.format(item)] = bot.text_msg_handler.CH_HEAD + u'詳細找ID ' + item
                elif action_type == bot.system_data_category.LAST_UID:
                    action_dict = {  '使用者{}製作'.format(uid[0:9]): bot.text_msg_handler.CH_HEAD + u'找' + uid + u'做的' for uid in items_iterator }
                elif action_type == bot.system_data_category.LAST_PIC_SHA:
                    action_dict = {}
                    for sha in items_iterator:
                        sha = str(sha)
                        action_dict['簡潔 - {}'.format(sha)] = bot.text_msg_handler.CH_HEAD + u'找' + sha
                        action_dict['詳細 - {}'.format(sha)] = bot.text_msg_handler.CH_HEAD + u'詳細找' + sha
                elif action_type == bot.system_data_category.LAST_MESSAGE:
                    action_dict = { msg: bot.text_msg_handler.CH_HEAD + u'找' + msg for msg in items_iterator }

                return bot.line_api_wrapper.wrap_template_with_action(action_dict, u'{}快捷查詢樣板'.format(unicode(action_type)), u'快捷指令/快速查詢')
            else:
                return None

    class _T(object):
        def __init__(self, packing_result):
            self._packing_result = packing_result

        def get_trans_result(self):
            cmd_cat = self._packing_result.command_category

            if cmd_cat == param_packer.func_T.command_category.ENCODE_FX:
                return self._trans_fx()
            elif cmd_cat == param_packer.func_T.command_category.ENCODE_NEWLINE:
                return self._trans_newline()
            elif cmd_cat == param_packer.func_T.command_category.ENCODE_SHA:
                return self._trans_sha()
            elif cmd_cat == param_packer.func_T.command_category.ENCODE_UTF_8:
                return self._trans_utf8()
            else:
                raise UndefinedCommandCategoryException()

        def _trans_utf8(self):
            from urllib import quote_plus

            target = self._packing_result.result[param_packer.func_T.param_category.TARGET]
            return quote_plus(target.encode('utf-8'))
        
        def _trans_newline(self):
            target = self._packing_result.result[param_packer.func_T.param_category.TARGET]
            return target.replace(u'\n', u'\\n')
        
        def _trans_sha(self):
            target = self._packing_result.result[param_packer.func_T.param_category.TARGET]
            return hashlib.sha224(target.encode('utf-8')).hexdigest()
        
        def _trans_fx(self):
            target = self._packing_result.result[param_packer.func_T.param_category.TARGET]

            regex = ur"([\d.]*)([a-zA-Z]*)([\d]*)?([+\-*/]?)"
            
            def add_star(match):
                if match.group(1) != '' and match.group(2) != '':
                    if match.group(3) == '':
                        return u'{}*{}{}'.format(match.group(1), match.group(2), match.group(4))
                    else:
                        return u'{}*{}**{}{}'.format(match.group(1), match.group(2), match.group(3), match.group(4))
                else:
                    return match.group()
            
            return re.sub(regex, add_star, target)

    class _RD(object):
        CASE_SERIAL_LENGTH = 12

        def __init__(self, array_sep, packing_result):
            self._array_separator = array_sep
            self._packing_result = packing_result

        def generate_output(self):
            cmd_cat = self._packing_result.command_category

            if cmd_cat == param_packer.func_RD.command_category.NUM_RANGE:
                return self._num_range()
            elif cmd_cat == param_packer.func_RD.command_category.PROBABILITY:
                return self._probability()
            elif cmd_cat == param_packer.func_RD.command_category.TEXT:
                return self._rand_text()
            elif cmd_cat == param_packer.func_RD.command_category.CASE_SERIAL:
                return self._rand_case_serial()
            else:
                raise UndefinedCommandCategoryException()

        def _num_range(self):
            start_index = self._packing_result.result[param_packer.func_RD.param_category.START_NUM]
            end_index = self._packing_result.result[param_packer.func_RD.param_category.END_NUM]
            ct = self._get_count()

            if ct == -1:
                return error.sys_command.func_RD_invalid_count()
            else:
                return tool.random_drawer.draw_number_string(start_index, end_index, ct)

        def _probability(self):
            prob = self._packing_result.result[param_packer.func_RD.param_category.PROBABILITY]
            ct = self._get_count()
            
            if ct == -1:
                return error.sys_command.func_RD_invalid_count()
            else:
                return tool.random_drawer.draw_probability_string(prob, True, ct, 3)

        def _rand_text(self):
            text_arr = self._packing_result.result[param_packer.func_RD.param_category.TEXT]
            ct = self._get_count()
            
            if ct == -1:
                return error.sys_command.func_RD_invalid_count()
            else:
                return tool.random_drawer.draw_text_string(text_arr, ct)

        def _get_count(self):
            ct = self._packing_result.result[param_packer.func_RD.param_category.COUNT]

            if ct is None:
                ct = 1

            if ct > error.sys_command.FUNC_RD_MAX or ct < error.sys_command.FUNC_RD_MIN:
                return -1

            return ct

        def _rand_case_serial(self):
            return tool.random_drawer.generate_random_string(command_handler_collection._RD.CASE_SERIAL_LENGTH)

    class _O(object):
        def __init__(self, oxford_dict, packing_result):
            self._oxford_dict = oxford_dict
            self._packing_result = packing_result
            self._query_result = None

            self._oxford_query()

        def _oxford_query(self):
            voc = self._packing_result.result[param_packer.func_O.param_category.VOCABULARY]

            if not self._oxford_dict.enabled:
                self._query_result = ext.action_result(error.oxford_api.disabled(), False)
            else:
                self._query_result = ext.action_result(self._oxford_dict.get_data_json(voc), True)

        def generate_output(self): 
            if not self._query_result.success:
                return self._query_result.result
            else:
                voc = self._packing_result.result[param_packer.func_O.param_category.VOCABULARY]

                return bot.oxford_api_wrapper.json_to_string(voc, self._query_result.result)

    class _W(object):
        def __init__(self, packing_result, config_manager, weather_id_reg, weather_config, weather_reporter, webpage_generator):
            self._packing_result = packing_result

            self._config_manager = config_manager

            self._weather_id_reg = weather_id_reg
            self._weather_config = weather_config
            self._weather_reporter = weather_reporter

            self._webpage_generator = webpage_generator

        def generate_output(self, src):
            cmd_cat = self._packing_result.command_category

            if cmd_cat == param_packer.func_W.command_category.DATA_CONTROL:
                return self._data_control_output(bot.line_api_wrapper.source_user_id(src))
            elif cmd_cat == param_packer.func_W.command_category.ID_SEARCH:
                return self._id_search_output()
            else:
                raise UndefinedCommandCategoryException()

        def _data_control_output(self, executor_uid):
            action = self._packing_result.result[param_packer.func_W.param_category.ACTION]
            station_ids = self._packing_result.result[param_packer.func_W.param_category.CITY_ID]
            op_type = self._packing_result.result[param_packer.func_W.param_category.OUTPUT_TYPE]
            if op_type is None:
                op_type = tool.weather.output_type.SIMPLE
            hr_freq = self._get_hr_freq()
            hr_range = self._get_hr_range()

            if action == special_param.func_W.action_category.ADD_TRACK:
                return self._weather_config.add_config(executor_uid, station_ids, op_type, hr_freq, hr_range)
            elif action == special_param.func_W.action_category.DEL_TRACK:
                return self._weather_config.del_config(executor_uid, station_ids)
            elif action == special_param.func_W.action_category.GET_DATA:
                return self._get_weather_data(station_ids, op_type, hr_freq, hr_range)
            else:
                raise UndefinedActionException()

        def _get_weather_data(self, station_ids, op_type, hr_freq, hr_range):
            if len(station_ids) > self._config_manager.getint(bot.config_category.WEATHER_REPORT, bot.config_category_weather_report.MAX_BATCH_SEARCH_COUNT):
                return error.main.invalid_thing_with_correct_format(u'批次查詢量', u'最多一次10筆', len(station_ids))

            return u'\n=============\n'.join([self._weather_reporter.get_data_by_owm_id(id, op_type, hr_freq, hr_range) for id in station_ids])

        def _get_hr_freq(self):
            hr_freq = self._packing_result.result[param_packer.func_W.param_category.FREQUENCY]
            if hr_freq is None:
                hr_freq = self._config_manager.getint(bot.config_category.WEATHER_REPORT, bot.config_category_weather_report.DEFAULT_INTERVAL_HR)

            return hr_freq

        def _get_hr_range(self):
            hr_range = self._packing_result.result[param_packer.func_W.param_category.HOUR_RANGE]
            if hr_range is None:
                hr_range = self._config_manager.getint(bot.config_category.WEATHER_REPORT, bot.config_category_weather_report.DEFAULT_DATA_RANGE_HR)

            return hr_range

        def _id_search_output(self):
            keyword = self._packing_result.result[param_packer.func_W.param_category.KEYWORD]

            search_result = self._weather_id_reg.ids_for(keyword, None, 'like')
            search_result_count = len(search_result)
            search_result_simp = search_result[:15]
            search_desc = u'搜尋字詞: {} (共{}筆結果)'.format(keyword, search_result_count)
            if len(search_result) > 0:
                result_arr = [search_desc] + \
                             [u'{} - {} ({})'.format(id, 
                                                     u'{}, {}'.format(city_name, country_code), 
                                                     coordinate.to_string(4)) 
                              for id, city_name, country_code, coordinate in search_result]
                action_dict = { str(id): bot.text_msg_handler.CH_HEAD + u'天氣查詢 ' + str(id) for id, city_name, country_code, coordinate in search_result_simp }
                return [bot.line_api_wrapper.wrap_template_with_action(action_dict, u'搜尋結果快速查詢樣板', u'快速查詢樣板，請參考搜尋結果點選'),
                        bot.line_api_wrapper.wrap_text_message(u'\n'.join(result_arr), self._webpage_generator)]
            else:
                return u'{}\n{}\n若城市名為中文，請用該城市的英文名搜尋。'.format(search_desc, error.main.no_result())

    class _LUK(object):
        def __init__(self, packing_result):
            self._packing_result = packing_result

        def generate_output(self):
            score = self._packing_result.result[param_packer.func_LUK.param_category.SCORE]
            
            result = game.sc_gen_data.calculate_opportunity_greater(score)
            
            try:
                return u'獲得比{}分更高的機率為{:%}'.format(score, result)
            except ValueError:
                return u'Error during calculation:\n{}'.format(result)

    class _DL(object):
        def __init__(self, packing_result, sticker_dl, webpage_gen):
            self._packing_result = packing_result
            self._sticker_dl = sticker_dl

            self._root_url = os.environ["APP_ROOT_URL"] + u"/"

            self._webpage_generator = webpage_gen

        def generate_output(self):
            pkg_id = self._packing_result.result[param_packer.func_DL.param_category.PACKAGE_ID]

            stk_meta = self._get_sticker_meta()
            if stk_meta is not None:
                dl_result = self._dl_stk(stk_meta)
                return self._process_output(dl_result, stk_meta)
            else:
                return error.main.miscellaneous(u'查無貼圖資料。(圖包ID: {})'.format(pkg_id))
            
        def _get_sticker_meta(self):
            pkg_id = self._packing_result.result[param_packer.func_DL.param_category.PACKAGE_ID]
            
            try:
                return self._sticker_dl.get_pack_meta(pkg_id)
            except tool.MetaNotFoundException:
                return None

        def _dl_stk(self, stk_meta):
            with_sound = self._packing_result.result[param_packer.func_DL.param_category.INCLUDE_SOUND]

            return self._sticker_dl.download_stickers(stk_meta, with_sound)

        def _process_output(self, dl_result, stk_meta):
            if dl_result is not None:
                ret = [u'貼圖圖包製作完成，請盡快下載。', 
                       u'檔案將於小水母休眠後刪除。', 
                       u'LINE內建瀏覽器無法下載檔案，請自行複製連結至手機瀏覽器。', 
                       u'若要將動態貼圖轉為gif，請點此 https://ezgif.com/apng-to-gif', 
                       u'']
                ret.append(u'圖包ID: {}'.format(stk_meta.pack_id))
                ret.append(u'{} (由 {} 製作)'.format(stk_meta.title, stk_meta.author))
                ret.append(u'')
                ret.append(u'檔案下載連結: (如下)')
                ret.append(u'下載耗時 {:.3f} 秒'.format(dl_result.downloading_consumed_time))
                ret.append(u'壓縮耗時 {:.3f} 秒'.format(dl_result.compression_consumed_time))
                ret.append(u'內含貼圖 {} 張'.format(dl_result.sticker_count))

                return [bot.line_api_wrapper.wrap_text_message(txt, self._webpage_generator) 
                        for txt in (u'\n'.join(ret), self._root_url + dl_result.compressed_file_path.replace("\\", "\\\\"))]
            else:
                return u'貼圖下載失敗，請重試。'

    class _STK(object):
        def __init__(self, packing_result, stk_rec, config_manager, webpage_generator):
            self._packing_result = packing_result

            self._stk_rec = stk_rec
            self._config_manager = config_manager

            self._webpage_generator = webpage_generator

        def generate_output(self):
            cmd_cat = self._packing_result.command_category

            if cmd_cat == param_packer.func_STK.command_category.RANKING:
                return self.generate_sticker_ranking_output()
            elif cmd_cat == param_packer.func_STK.command_category.STICKER_LOOKUP:
                return self.generate_sticker_lookup_output()
            else:
                raise UndefinedCommandCategoryException()

        def generate_sticker_ranking_output(self):
            ctg = self._packing_result.result[param_packer.func_STK.param_category.CATEGORY]

            if ctg == db.ranking_category.PACKAGE:
                result = self._get_package_ranking_str()
            elif ctg == db.ranking_category.STICKER:
                result = self._get_package_sticker_str()
            else:
                raise UndefinedCommandCategoryException()
            
            if isinstance(result, db.PackedResult):
                full_url = self._webpage_generator.rec_webpage(result.full, db.webpage_content_type.STICKER_RANKING)
                return result.limited + u'\n\n詳細資訊: ' + full_url
            else:
                return result

        def generate_sticker_lookup_output(self):
            stk_id = self._packing_result.result[param_packer.func_STK.param_category.STICKER_ID]

            return bot.line_api_wrapper.wrap_image_message(bot.line_api_wrapper.sticker_png_url(stk_id))

        def _get_package_ranking_str(self):
            hr_range = self._get_range_hr()
            count = self._get_count()

            return self._stk_rec.hottest_package_str(hr_range, count)

        def _get_package_sticker_str(self):
            hr_range = self._get_range_hr()
            count = self._get_count()

            return self._stk_rec.hottest_sticker_str(hr_range, count)

        def _get_count(self):
            limit_count = self._packing_result.result[param_packer.func_STK.param_category.COUNT]
            if limit_count is None:
                limit_count = self._config_manager.getint(bot.config_category.STICKER_RANKING, bot.config_category_sticker_ranking.LIMIT_COUNT)

            return limit_count

        def _get_range_hr(self):
            hour_range = self._packing_result.result[param_packer.func_STK.param_category.HOUR_RANGE]
            if hour_range is None:
                hour_range = self._config_manager.getint(bot.config_category.STICKER_RANKING, bot.config_category_sticker_ranking.HOUR_RANGE)

            return hour_range

    class _C(object):
        def __init__(self, packing_result, ppp, ctyccy, oxr_client):
            self._packing_result = packing_result

            self._ppp = ppp
            self._ctyccy = ctyccy

            self._oxr_client = oxr_client

        def generate_output(self):
            cmd_cat = self._packing_result.command_category

            if cmd_cat == param_packer.func_C.command_category.AVAILABLE:
                return self.generate_output_available_currencies()
            elif cmd_cat == param_packer.func_C.command_category.CONVERT:
                return self.generate_output_convert_currencies()
            elif cmd_cat == param_packer.func_C.command_category.CURRENT:
                return self.generate_output_current_exchange_rate()
            elif cmd_cat == param_packer.func_C.command_category.HISTORIC:
                return self.generate_output_historic_exchange_rate()
            else:
                raise UndefinedCommandCategoryException()

        def generate_output_available_currencies(self):
            return tool.currency.oxr.available_currencies_str(self._oxr_client.get_available_currencies_dict())

        def generate_output_convert_currencies(self):
            source_currency = self._packing_result.result[param_packer.func_C.param_category.BASE_CURRENCY]
            target_currency = self._packing_result.result[param_packer.func_C.param_category.TARGET_CURRENCY]
            amount = self._packing_result.result[param_packer.func_C.param_category.AMOUNT]

            ret = []

            conv_result = self._oxr_client.convert(source_currency, target_currency, amount)
            ret.append(conv_result.formatted_string)
            ret.append(u'')
            ret.append(u'PPP(購買力平價，Purchasing Power Parity)補正匯率: ')

            country_entries_source = self._ctyccy.get_country_entry(currency_codes=source_currency)
            country_entries_target = self._ctyccy.get_country_entry(currency_codes=target_currency)
            ppps_source = self._ppp.get_data(country_names=[ce_s.get_data(tool.currency.country_entry_column.CountryName) for ce_s in country_entries_source])
            ppps_target = self._ppp.get_data(country_names=[ce_t.get_data(tool.currency.country_entry_column.CountryName) for ce_t in country_entries_target])
            
            for ppp_s in ppps_source:
                src_country = ppp_s.country_name
                src_ppp = ppp_s.get_data()

                for ppp_t in ppps_target:
                    tgt_country = ppp_t.country_name
                    tgt_ppp = ppp_t.get_data()

                    if tgt_ppp == tool.currency.data_entry.NA:
                        ppp_txt = warning.currency.data_not_enough(tgt_country)
                    elif src_ppp == tool.currency.data_entry.NA:
                        ppp_txt = warning.currency.data_not_enough(src_country)
                    else:
                        ratio_ppp = conv_result.rate / (tgt_ppp / src_ppp)
                        if ratio_ppp > 1:
                            ppp_txt = u'{}的物價比{}貴{:.4f}倍'.format(src_country, tgt_country, ratio_ppp)
                        elif ratio_ppp == 1:
                            ppp_txt = u'{}的物價跟{}一樣'
                        elif ratio_ppp < 1:
                            ppp_txt = u'{}的物價比{}便宜{:.4f}倍'.format(src_country, tgt_country, 1 / ratio_ppp)

                    ret.append(ppp_txt)

            return u'\n'.join(ret)

        def generate_output_current_exchange_rate(self):
            curr_arr = self._packing_result.result[param_packer.func_C.param_category.CURRENCY_SYMBOLS]

            return tool.currency.oxr.latest_str(self._oxr_client.get_latest_dict(curr_arr))

        def generate_output_historic_exchange_rate(self):
            historical_date = self._packing_result.result[param_packer.func_C.param_category.DATE]
            curr_arr = self._packing_result.result[param_packer.func_C.param_category.CURRENCY_SYMBOLS]

            return tool.currency.oxr.historical_str(self._oxr_client.get_historical_dict(historical_date, curr_arr))

    class _F(object):
        def __init__(self, packing_result, executor_uid, executor_name, executor_permission, rss_data_manager, execute_in_gid):
            self._packing_result = packing_result
            
            self._execute_in_gid = execute_in_gid
            if bot.line_api_wrapper.determine_id_type(self._execute_in_gid) == bot.line_event_source_type.USER:
                self._execute_in_gid = db.PUBLIC_GROUP_ID

            self._executor_uid = executor_uid
            self._executor_name = executor_name
            self._executor_permission = executor_permission
            self._lowest_permission = bot.permission.MODERATOR

            self._rss_data_manager = rss_data_manager

        def generate_output(self):
            cmd_cat = self._packing_result.command_category

            if cmd_cat == param_packer.func_F.command_category.CREATE:
                return self._output_create()
            elif cmd_cat == param_packer.func_F.command_category.DELETE:
                return self._output_delete()
            elif cmd_cat == param_packer.func_F.command_category.SEARCH:
                return self._output_search()
            elif cmd_cat == param_packer.func_F.command_category.UPDATE:
                return self._output_update()
            elif cmd_cat == param_packer.func_F.command_category.GET_LINK:
                return self._output_get_link()
            else:
                raise UndefinedCommandCategoryException()

        def _output_create(self):
            param_dict = self._packing_result.result
            render_text = command_handler_collection.replace_newline(param_dict[param_packer.func_F.param_category.RENDER_TEXT])
            title = param_dict[param_packer.func_F.param_category.TITLE]
            url = param_dict[param_packer.func_F.param_category.URL]

            if not self._has_sufficient_permission():
                return error.permission.restricted(self._lowest_permission)

            new_post_seq_id = self._rss_data_manager.new_post(self._executor_uid, self._executor_name, render_text, title, url, self._execute_in_gid)

            if new_post_seq_id is not None:
                return u'新公告 #{} 建立完成。\n公告內容: {}'.format(new_post_seq_id, db.rss_manager.url_by_id(new_post_seq_id))
            else:
                return error.rss.cannot_create()
        
        def _output_delete(self):
            param_dict = self._packing_result.result
            ids = param_dict[param_packer.func_F.param_category.ID]

            if self._has_sufficient_permission() and self._rss_data_manager.del_post(self._executor_uid, ids):
                return u'公告 #{} 刪除成功。'.format('、'.join([str(id) for id in ids]))
            else:
                return error.rss.cannot_be_deleted(ids)
        
        def _output_search(self):
            param_dict = self._packing_result.result
            keywords = param_dict[param_packer.func_F.param_category.KEYWORD]
            
            result = self._rss_data_manager.search_post(self._execute_in_gid, keywords)
            if len(result) > 0:
                return u'\n'.join([u'公告搜尋 關鍵字: {}'.format(u'、'.join(keywords)), u''] + 
                                  [rss_data.to_simp_string() + u'\n' + rss_data.url_for_id() for rss_data in result])
            else:
                return error.main.no_result()
        
        def _output_update(self):
            param_dict = self._packing_result.result
            id = param_dict[param_packer.func_F.param_category.ID]
            render_text = command_handler_collection.replace_newline(param_dict[param_packer.func_F.param_category.RENDER_TEXT])
            title = param_dict[param_packer.func_F.param_category.TITLE]
            url = param_dict[param_packer.func_F.param_category.URL]

            if not self._has_sufficient_permission() and self._rss_data_manager.update_post(self._executor_uid, self._executor_name, id, render_text, title, url):
                return error.rss.cannot_be_updated(id)
            else:
                return u'公告 #{} 更新成功。\n公告內容: {}'.format(id, db.rss_manager.url_by_id(id))

        def _output_get_link(self):
            if self._execute_in_gid == db.PUBLIC_GROUP_ID:
                return u'小水母RSS連結:\n' + db.RSS_ID_URL_BASE
            else:
                return u'群組專屬RSS連結:\n' + db.RSS_ID_URL_BASE + self._execute_in_gid
            
        def _has_sufficient_permission(self):
            if self._execute_in_gid == db.PUBLIC_GROUP_ID:
                return self._executor_permission >= bot.permission.BOT_ADMIN
            else:
                return self._executor_permission >= self._lowest_permission

# -*- coding: utf-8 -*-
import os, sys
from db import misc
import json
from datetime import datetime
import hashlib
import re

from flask import request, url_for
import pymongo

import tool
from error import error
import bot, db, ext

from .param import param_packer, packer_factory
from .param_base import (
    param_validator, param_packing_result_status, special_param,
    UndefinedCommandCategoryException, UndefinedPackedStatusException
)
from .cmd_handler import command_handler_collection

class text_msg_handler(object):
    ########################################################################
    # Validating Algorhithm Generation Explanation:
    #   ---1--- 1st generation text parsing alogorhithm:
    #               .Direct regex.find_match usage in parsing function.
    #
    #   ---2--- 2nd generation text parsing alogorhithm:
    #               .For loop with packer_list
    #               .Same, unnecessary duplicated code on handling the case of not match.
    #
    #   ---3--- 3rd generation text parsing alogorhithm:
    #               .Use self._validate to validate the give information
    ########################################################################

    CH_HEAD = u'小水母 '
    EN_HEAD = u'JC\n'

    REMOTE_SPLITTER = u'\n'

    def __init__(self, flask_app, config_manager, line_api_wrapper, mongo_client, oxford_api, system_data, webpage_generator, imgur_api_wrapper, 
                 oxr_client, string_calculator, weather_reporter, file_tmp_path, rss_data_mgr, last_chat_rec):
        self._flask_app = flask_app
        self._config_manager = config_manager
        self._last_chat_rec = last_chat_rec

        self._array_separator = param_validator.ARRAY_SEPARATOR

        self._system_data = system_data
        self._system_config = db.system_config(mongo_client)
        self._system_stats = db.system_statistics(mongo_client)
        self._stk_rec = db.sticker_recorder(mongo_client)
        self._loop_prev = bot.infinite_loop_preventer(self._config_manager.getint(bot.config_category.SYSTEM, bot.config_category_system.DUPLICATE_CONTENT_BAN_COUNT), self._config_manager.getint(bot.config_category.SYSTEM, bot.config_category_system.UNLOCK_PASSWORD_LENGTH))
        self._db_measurement = db.measurement_data_wrapper()

        self._kwd_public = db.group_dict_manager(mongo_client, config_manager.getint(bot.config_category.KEYWORD_DICT, bot.config_category_kw_dict.CREATE_DUPLICATE), config_manager.getint(bot.config_category.KEYWORD_DICT, bot.config_category_kw_dict.REPEAT_CALL))
        self._kwd_global = db.word_dict_global(mongo_client)
        self._group_manager = db.group_manager(mongo_client)
        self._oxford_dict = oxford_api
        self._line_api_wrapper = line_api_wrapper
        self._webpage_generator = webpage_generator
        self._imgur_api_wrapper = imgur_api_wrapper
        self._oxr_client = oxr_client
        self._string_calculator = string_calculator
        self._weather_reporter = weather_reporter
        self._weather_config = db.weather_report_config(mongo_client)
        self._weather_id_reg = tool.weather.weather_reporter.CITY_ID_REGISTRY
        self._sticker_dl = tool.line_sticker_downloader(file_tmp_path)
        self._pli = tool.currency.pypli()
        self._ctyccy = tool.currency.countries_and_currencies()
        self._ppp = tool.currency.ppp_manager()

        self._rss_data_manager = rss_data_mgr
        
        self._pymongo_client = mongo_client
        
    def handle_text(self, event, user_permission, group_config_type):
        """Return whether message has been replied"""
        token = event.reply_token
        text = unicode(event.message.text)
        src = event.source

        src_gid = bot.line_api_wrapper.source_channel_id(src)
        src_uid = bot.line_api_wrapper.source_user_id(src)

        texts = bot.msg_handler.misc.split(text, text_msg_handler.REMOTE_SPLITTER, 2)
        if bot.line_api_wrapper.is_valid_room_group_id(texts[0], True, True) and texts[1] is not None:
            attempt_to_remote = True
            execute_remote_gid = texts[0]
            text = texts[1]
        else:
            attempt_to_remote = False
            execute_remote_gid = src_gid
            text = text

        cmd_iter = self._get_cmd_data(text)
        if cmd_iter is not None:
            cmd_key, cmd_data = cmd_iter
        else:
            print 'Called an not existed command.'
            return False

        # terminate if set to silence
        if group_config_type <= db.group_data_range.SILENCE and cmd_data.function_code != 'GA':
            print 'Terminate because the group is set to silence and function code is not GA.'
            return False

        # log statistics
        self._system_stats.command_called(cmd_key)

        # get function
        cmd_function = getattr(self, '_{}'.format(cmd_data.function_code))

        # override user_permission(command executor) and group_config_type if the command is attempt to control remotely
        if attempt_to_remote and cmd_data.remotable >= bot.remote.GROUP_ID_ONLY:
            user_permission = self._group_manager.get_user_permission(execute_remote_gid, src_uid)

            if bot.line_api_wrapper.is_valid_room_group_id(execute_remote_gid):
                group_config_type = self._group_manager.get_group_config_type(execute_remote_gid)
            else:
                group_config_type = db.group_data_range.ALL

        # check the action is valid with the provided permission
        low_perm = cmd_data.lowest_permission
        if user_permission == bot.permission.RESTRICTED:
            self._line_api_wrapper.reply_message_text(token, error.permission.user_is_resticted())
            return True
        elif user_permission < low_perm:
            self._line_api_wrapper.reply_message_text(token, error.permission.restricted(low_perm))
            return True

        # handle command
        if attempt_to_remote:
            handle_result = cmd_function(src, execute_remote_gid, group_config_type, user_permission, text)
        else:
            handle_result = cmd_function(src, src_gid, group_config_type, user_permission, text)

        # reply handle result
        if handle_result is None:
            return self._line_api_wrapper.reply_message_text(token, error.sys_command.syntax_error(cmd_data.function_code))
        else:
            if isinstance(handle_result, (str, unicode)):
                self._line_api_wrapper.reply_message_text(token, handle_result)
            else:
                self._line_api_wrapper.reply_message(token, handle_result)

        return True

    def _get_cmd_data(self, text):
        text = text.upper()
        for cmd_key, cmd_obj in bot.sys_cmd_dict.iteritems():
            for header in cmd_obj.headers:
                if text.startswith(text_msg_handler.CH_HEAD + header) or self._get_cmd_data_match_en(text, header):
                    return cmd_key, cmd_obj

    def _get_cmd_data_match_en(self, text, header):
        s = text.split(u'\n')
        return s[0] == text_msg_handler.EN_HEAD.replace(u'\n', u'') and s[1] == header.replace(u'\n', u'')

    def _get_kwd_instance(self, src, config, execute_remote_gid=None):
        cid = bot.line_api_wrapper.source_channel_id(src)

        if bot.line_api_wrapper.is_valid_room_group_id(execute_remote_gid, True, True):
            config = self._group_manager.get_group_config_type(execute_remote_gid)
            control_remotely = True
        else:
            config = self._group_manager.get_group_config_type(cid)
            execute_remote_gid = None
            control_remotely = False

        if config is not None and config == db.group_data_range.ALL:
            manager_range = db.group_dict_manager_range.GROUP_AND_PUBLIC
        else:
            manager_range = db.group_dict_manager_range.GROUP_ONLY

        if control_remotely:
            if execute_remote_gid == bot.remote.GLOBAL_TOKEN():
                kwd_instance = self._kwd_public.clone_instance(db.PUBLIC_GROUP_ID, db.group_dict_manager_range.GLOBAL)
            elif execute_remote_gid == bot.remote.PUBLIC_TOKEN():
                kwd_instance = self._kwd_public.clone_instance(db.PUBLIC_GROUP_ID)
            else:
                kwd_instance = self._kwd_public.clone_instance(execute_remote_gid, manager_range)
        else:
            source_type = bot.line_event_source_type.determine(src)
            if source_type == bot.line_event_source_type.USER:
                kwd_instance = self._kwd_public
            elif source_type == bot.line_event_source_type.GROUP or source_type == bot.line_event_source_type.ROOM:
                kwd_instance = self._kwd_public.clone_instance(cid, manager_range)
            else:
                raise ValueError(u'Unknown source type. {}'.format(source_type))

        return kwd_instance

    def _get_query_result(self, pack_result, execute_in_gid, kwd_instance, exact_same):
        cmd_cat = pack_result.command_category
        prm_dict = pack_result.result

        if cmd_cat == param_packer.func_Q.command_category.BY_AVAILABLE:
            if prm_dict[param_packer.func_Q.param_category.GLOBAL]:
                expr = u'搜尋範圍: 全域回覆組'
                result_data = self._kwd_global.get_pairs_by_group_id(bot.remote.GLOBAL_TOKEN(), True)
            elif prm_dict[param_packer.func_Q.param_category.AVAILABLE]:
                expr = u'搜尋範圍: 本頻道( {} )可用的回覆組'.format(execute_in_gid)
                result_data = kwd_instance.search_all_available_pair()
            else:
                return ext.action_result(UndefinedParameterException(), False)
        elif cmd_cat == param_packer.func_Q.command_category.BY_ID_RANGE:
            expr = u'搜尋範圍: ID介於【{}】~【{}】之間的回覆組'.format(prm_dict[param_packer.func_Q.param_category.START_ID], 
                                                                     prm_dict[param_packer.func_Q.param_category.END_ID])
            result_data = kwd_instance.search_pair_by_index(prm_dict[param_packer.func_Q.param_category.START_ID], 
                                                            prm_dict[param_packer.func_Q.param_category.END_ID])
        elif cmd_cat == param_packer.func_Q.command_category.BY_GID:
            expr = u'搜尋範圍: 群組ID {} 內專屬的回覆組'.format(prm_dict[param_packer.func_Q.param_category.GID])
            result_data = self._kwd_global.get_pairs_by_group_id(prm_dict[param_packer.func_Q.param_category.GID], True)
        elif cmd_cat == param_packer.func_Q.command_category.BY_UID:
            get_name_result = self._get_user_name(prm_dict[param_packer.func_Q.param_category.UID])

            expr = u'搜尋範圍: 由 {} ({}) 製作的回覆組'.format(get_name_result.result, prm_dict[param_packer.func_Q.param_category.UID])
            result_data = kwd_instance.search_pair_by_creator(prm_dict[param_packer.func_Q.param_category.UID])
        elif cmd_cat == param_packer.func_Q.command_category.BY_KEY:
            if prm_dict[param_packer.func_Q.param_category.IS_ID]:
                search_source = prm_dict[param_packer.func_Q.param_category.ID]

                expr = u'搜尋範圍: ID為【{}】的回覆組'.format(u'、'.join([str(id) for id in search_source]))
                result_data = kwd_instance.search_pair_by_index(search_source)
            else:
                search_source = command_handler_collection.replace_newline(prm_dict[param_packer.func_Q.param_category.KEYWORD])

                expr = u'搜尋範圍: 關鍵字 或 回覆 {}【{}】的回覆組'.format(u'為' if exact_same else u'含', search_source)
                result_data = kwd_instance.search_pair_by_keyword(search_source, exact_same)
        else:
            raise UndefinedCommandCategoryException()

        return ext.action_result([expr, result_data], True)

    def _get_executor_uid(self, src):
        # try to get complete profile
        try:
            uid = bot.line_api_wrapper.source_user_id(src)
            self._line_api_wrapper.profile_name(uid)
        except bot.UserProfileNotFoundError as ex:
            return ext.action_result(error.line_bot_api.unable_to_receive_user_id(), False)

        # verify uid structure
        if not bot.line_api_wrapper.is_valid_user_id(uid):
            return ext.action_result(error.line_bot_api.illegal_user_id(uid), False)

        return ext.action_result(uid, True)

    def _get_user_name(self, uid):
        try:
            return ext.action_result(self._line_api_wrapper.profile_name(uid), True)
        except bot.UserProfileNotFoundError:
            return ext.action_result(error.main.line_account_data_not_found(), False)
    
    def _validate(self, packer_list, text):
        """
        Return (Result: bool, detail: packing_result or object)

        If packing result is all pass, return (True, packing_result)
        Else, return (False, error_detail)
        """
        for packer in packer_list:
            packing_result = packer.pack(text)
            if packing_result.status == param_packing_result_status.ALL_PASS:
                return True, packing_result
            elif packing_result.status == param_packing_result_status.ERROR_IN_PARAM:
                return False, error.sys_command.unable_to_parse(packing_result.result)
            elif packing_result.status == param_packing_result_status.NO_MATCH:
                pass
            else:
                raise UndefinedPackedStatusException(unicode(packing_result.status))

        return False, None

    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _S(self, src, execute_in_gid, group_config_type, executor_permission, text, pinned=False):
        validation_pass, return_object = self._validate(packer_factory._S, text)

        if validation_pass:
            S_handler = command_handler_collection._S(self._pymongo_client, return_object)

            text = S_handler.generate_output_head()
            try:
                text += S_handler.generate_output_mongo_result()
            except pymongo.errors.OperationFailure as ex:
                text += error.mongo_db.op_fail(ex)

            return text
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _A(self, src, execute_in_gid, group_config_type, executor_permission, text, pinned=False):
        if pinned:
            packer_list = packer_factory._M
        else:
            packer_list = packer_factory._A
        validation_pass, return_object = self._validate(packer_list, text)

        if validation_pass:
            A_handler = command_handler_collection._A(return_object)

            get_uid_result = self._get_executor_uid(src)
            if not get_uid_result.success:
                return get_uid_result.result

            kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
            kwd_add_result = A_handler.add_kw(kwd_instance, pinned, get_uid_result.result)

            return A_handler.generate_output(kwd_add_result)
        else:
            return return_object
        
    def _M(self, src, execute_in_gid, group_config_type, executor_permission, text):
        return self._A(src, execute_in_gid, group_config_type, executor_permission, text, True)
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _D(self, src, execute_in_gid, group_config_type, executor_permission, text, pinned=False):
        if pinned:
            packer_list = packer_factory._R
        else:
            packer_list = packer_factory._D

        validation_pass, return_object = self._validate(packer_list, text)

        if validation_pass:
            D_handler = command_handler_collection._D(return_object)

            get_uid_result = self._get_executor_uid(src)
            if not get_uid_result.success:
                return get_uid_result.result

            kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
            kwd_del_result = D_handler.del_kw(kwd_instance, pinned, get_uid_result.result)

            return D_handler.generate_output(kwd_del_result)
        else:
            return return_object

    def _R(self, src, execute_in_gid, group_config_type, executor_permission, text):
        return self._D(src, execute_in_gid, group_config_type, executor_permission, text, True)
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _Q(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._Q, text)

        if validation_pass:
            Q_handler = command_handler_collection._Q(self._config_manager, self._webpage_generator)

            kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
            query_result = self._get_query_result(return_object, execute_in_gid, kwd_instance, False)

            return Q_handler.generate_output(query_result)
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _I(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._I, text)

        if validation_pass:
            I_handler = command_handler_collection._I(self._line_api_wrapper, self._config_manager, self._webpage_generator)

            kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
            query_result = self._get_query_result(return_object, execute_in_gid, kwd_instance, True)

            return I_handler.generate_output(kwd_instance, query_result)
        else:
            return return_object
            
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _X(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._X, text)

        if validation_pass:
            X_handler = command_handler_collection._X(self._webpage_generator, self._kwd_global, return_object)

            get_uid_result = self._get_executor_uid(src)
            if not get_uid_result.success:
                return get_uid_result.result

            clone_result = X_handler.clone(execute_in_gid, get_uid_result.result, executor_permission)

            return X_handler.generate_output(clone_result)
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _X2(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._X2, text)

        if validation_pass:
            get_uid_result = self._get_executor_uid(src)
            if not get_uid_result.success:
                return get_uid_result.result

            X2_handler = command_handler_collection._X2(execute_in_gid, get_uid_result.result, executor_permission, self._kwd_global)

            return X2_handler.generate_output()
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _E(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._E, text)

        if validation_pass:
            E_handler = command_handler_collection._E(self._webpage_generator, return_object)

            get_uid_result = self._get_executor_uid(src)
            if not get_uid_result.success:
                return get_uid_result.result

            kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
            cmd_cat = return_object.command_category
            if cmd_cat == param_packer.func_E.command_category.MOD_LINKED:
                mod_result = E_handler.mod_linked(executor_permission, kwd_instance)
                return E_handler.generate_output_mod_linked(mod_result)
            elif cmd_cat == param_packer.func_E.command_category.MOD_PINNED:
                mod_result = E_handler.mod_pinned(executor_permission, kwd_instance)
                return E_handler.generate_output_mod_pinned(mod_result)
            else:
                raise UndefinedCommandCategoryException()
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _K(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._K, text)

        if validation_pass:
            K_handler = command_handler_collection._K(self._config_manager, return_object)
            
            kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
            
            limit = K_handler.get_limit()
            rnk_cat = return_object.result[param_packer.func_K.param_category.CATEGORY]
            
            if rnk_cat == special_param.func_K.ranking_category.USER:
                return kwd_instance.user_created_rank_string(limit, self._line_api_wrapper)
            elif rnk_cat == special_param.func_K.ranking_category.KEYWORD:
                return kwd_instance.get_ranking_call_count_string(limit)
            elif rnk_cat == special_param.func_K.ranking_category.RECENTLY_USED:
                return kwd_instance.recently_called_string(limit)
            else:
                raise UndefinedCommandCategoryException()
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _P(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._P, text)

        if validation_pass:
            P_handler = command_handler_collection._P(self._webpage_generator, self._config_manager, self._system_data, self._system_stats, 
                                                      self._group_manager, self._loop_prev, self._oxr_client, self._imgur_api_wrapper, self._db_measurement, return_object)

            cmd_cat = return_object.command_category
            
            if cmd_cat == param_packer.func_P.command_category.MESSAGE_RECORD:
                msg_rec = P_handler.get_msg_track_data()
                return P_handler.generate_output_msg_track(msg_rec)
            elif cmd_cat == param_packer.func_P.command_category.SYSTEM_RECORD:
                kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
                return P_handler.generate_output_sys_rec(kwd_instance)
            else:
                raise UndefinedCommandCategoryException()
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _P2(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._P2, text)

        if validation_pass:
            kwd_instance = self._get_kwd_instance(src, group_config_type, execute_in_gid)
            P2_handler = command_handler_collection._P2(self._line_api_wrapper, self._webpage_generator, kwd_instance, self._group_manager, return_object)

            get_name_result = P2_handler.get_profile_name(src, execute_in_gid)
            return P2_handler.generate_output(get_name_result)
        else:
            return return_object
            
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _G(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._G, text)

        if validation_pass:
            G_handler = command_handler_collection._G(self._webpage_generator, self._last_chat_rec, return_object, src)
            
            gid_result = G_handler.get_group_id(execute_in_gid)

            if gid_result.success:
                gid = gid_result.result

                kwd_instance = self._get_kwd_instance(src, group_config_type, gid)
                group_data = self._group_manager.get_group_by_id(gid, True)

                return G_handler.generate_output(gid_result, kwd_instance, group_data)
            else:
                return gid_result.result
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _GA(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._GA, text)

        if validation_pass:
            GA_handler = command_handler_collection._GA(self._group_manager, return_object)

            result = GA_handler.set_config_type(execute_in_gid, executor_permission)

            return GA_handler.generate_output(result)
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _GA2(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._GA2, text)

        if validation_pass:
            GA2_handler = command_handler_collection._GA2(self._line_api_wrapper, self._group_manager, return_object)

            return GA2_handler.generate_output(src, execute_in_gid)
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _GA3(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._GA3, text)

        if validation_pass:
            GA3_handler = command_handler_collection._GA3(self._group_manager, return_object)
            
            activate_result = GA3_handler.activate(execute_in_gid)

            return GA3_handler.generate_output(activate_result)
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _H(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._H, text)

        if validation_pass:
            H_handler = command_handler_collection._H(self._webpage_generator)

            return H_handler.get_channel_info(src)
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _O(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._O, text)

        if validation_pass:
            O_handler = command_handler_collection._O(self._oxford_dict, return_object)

            return O_handler.generate_output()
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _RD(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._RD, text)

        if validation_pass:
            RD_handler = command_handler_collection._RD(self._array_separator, return_object)
            
            return RD_handler.generate_output()
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _L(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._L, text)

        if validation_pass:
            L_handler = command_handler_collection._L(self._system_data, self._webpage_generator, return_object)
            last_array = L_handler.get_last_data_array(execute_in_gid)

            return [item for item in (L_handler.generate_txt_output(last_array), L_handler.generate_template_output(last_array)) if item is not None]
        else:
            return return_object
             
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _T(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._T, text)

        if validation_pass:
            T_handler = command_handler_collection._T(return_object)

            return T_handler.get_trans_result()
        else:
            return return_object
    
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _C(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._C, text)

        if validation_pass:
            C_handler = command_handler_collection._C(return_object, self._ppp, self._ctyccy, self._oxr_client)

            return C_handler.generate_output()
        else:
            return return_object
             
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _W(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._W, text)

        if validation_pass:
            W_handler = command_handler_collection._W(return_object, 
                                                      self._config_manager, self._weather_id_reg, self._weather_config, self._weather_reporter, self._webpage_generator)

            return W_handler.generate_output(src)
        else:
            return return_object
             
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _DL(self, src, execute_in_gid, group_config_type, executor_permission, text): 
        validation_pass, return_object = self._validate(packer_factory._DL, text)

        if validation_pass:
            DL_handler = command_handler_collection._DL(return_object, self._sticker_dl, self._webpage_generator)

            return DL_handler.generate_output()
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _STK(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._STK, text)

        if validation_pass:
            STK_handler = command_handler_collection._STK(return_object, self._stk_rec, self._config_manager, self._webpage_generator)

            return STK_handler.generate_output()
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _LUK(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._LUK, text)

        if validation_pass:
            LUK_handler = command_handler_collection._LUK(return_object)

            return LUK_handler.generate_output()
        else:
            return return_object
        
    ##### VALIDATING ALGORHITHM GENERATION: 3 #####
    def _F(self, src, execute_in_gid, group_config_type, executor_permission, text):
        validation_pass, return_object = self._validate(packer_factory._F, text)

        if validation_pass:
            get_uid_result = self._get_executor_uid(src)
            if not get_uid_result.success:
                return get_uid_result.result
            else:
                uid = get_uid_result.result

            F_handler = command_handler_collection._F(
                return_object, uid, self._line_api_wrapper.profile_name_safe(uid, src), executor_permission, self._rss_data_manager, execute_in_gid)

            return F_handler.generate_output()
        else:
            return return_object

    @staticmethod
    def can_try_handle(full_text):
        full_text = full_text.upper()
        return full_text.startswith(text_msg_handler.CH_HEAD) or \
               full_text.startswith(text_msg_handler.EN_HEAD) or \
               bot.line_api_wrapper.is_valid_room_group_id(full_text.split(text_msg_handler.REMOTE_SPLITTER)[0], True, True)
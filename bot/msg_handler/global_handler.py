# -*- coding: utf-8 -*-

import os, sys

from linebot.models import (
    TextMessage, StickerMessage, ImageMessage, VideoMessage, AudioMessage, LocationMessage
)
import zhconv

from text_msg import text_msg_handler
from .game_msg import game_msg_handler
from .misc import split

import db, bot, ext, tool, error

class global_msg_handle(object):
    SPLITTER = '\n'

    def __init__(self, line_api_wrapper, system_config, mongo_client, txt_handle, special_keyword_handler, game_handle, img_handle):
        self._line_api_wrapper = line_api_wrapper
        self._system_config = system_config

        self._txt_handle = txt_handle
        self._spec_txt_handle = special_keyword_handler
        self._game_handle = game_handle
        self._img_handle = img_handle

        self._group_manager = self._txt_handle._group_manager 
        self._webpage_generator = self._txt_handle._webpage_generator 
        self._system_stats = self._txt_handle._system_stats 
        self._system_data = self._txt_handle._system_data 
        self._string_calculator = self._txt_handle._string_calculator 
        self._get_kwd_instance = self._txt_handle._get_kwd_instance 
        self._stk_rec = self._txt_handle._stk_rec
        self._loop_preventer = self._txt_handle._loop_prev

        self._weather_reporter = self._spec_txt_handle._weather_reporter
        
        self._rps_data = self._game_handle._rps_holder

        self._intercept_key = os.getenv('COMMAND_INTERCEPT', None)
        if self._intercept_key is None:
            print 'Define COMMAND_INTERCEPT in environment variable to switch message interception.'
            sys.exit(1)

        self._silence_key = os.getenv('COMMAND_SILENCE', None)
        if self._silence_key is None:
            print 'Define COMMAND_SILENCE in environment variable to switch text message handling.'
            sys.exit(1)

        self._calc_debug_key = os.getenv('COMMAND_CALC_DEBUG', None)
        if self._calc_debug_key is None:
            print 'Define COMMAND_CALC_DEBUG in environment variable to switch string calculator debugging.'
            sys.exit(1)

        self._rep_error_key = os.getenv('COMMAND_REPLY_ERROR', None)
        if self._rep_error_key is None:
            print 'Define COMMAND_REPLY_ERROR in environment variable to switch report on error occurred.'
            sys.exit(1)

        self._send_error_report_key = os.getenv('COMMAND_SEND_ERROR_REPORT', None)
        if self._send_error_report_key is None:
            print 'Define COMMAND_SEND_ERROR_REPORT in environment variable to switch send error mail on error occurred.'
            sys.exit(1)

        self._intercept_display_name_key = os.getenv('COMMAND_INTERCEPT_DISPLAY_NAME', None)
        if self._intercept_display_name_key is None:
            print 'Define COMMAND_INTERCEPT_DISPLAY_NAME in environment variable to switch report on error occurred.'
            sys.exit(1)

    ##############
    ### GLOBAL ###
    ##############

    def _terminate(self):
        return self._system_config.get(db.config_data.SILENCE)

    def _handle_auto_reply(self, event, reply_data):
        """THIS WILL LOG MESSAGE ACTIVITY INSIDE METHOD IF MESSAGE HAS BEEN REPLIED."""
        self._system_stats.extend_function_used(db.extend_function_category.AUTO_REPLY)

        self._system_data.set(bot.system_data_category.LAST_PAIR_ID, bot.line_api_wrapper.source_channel_id(event.source), reply_data.seq_id)
        src = event.source
        msg = event.message

        if isinstance(msg, TextMessage):
            recv_msg_type = db.msg_type.TEXT
        elif isinstance(msg, StickerMessage):
            recv_msg_type = db.msg_type.STICKER
        elif isinstance(msg, ImageMessage):
            recv_msg_type = db.msg_type.PICTURE
        else:
            raise NotImplementedError()

        token = event.reply_token

        rep_type = reply_data.reply_type
        rep_content = reply_data.reply_true
        rep_att = reply_data.reply_attach_text
        rep_link = reply_data.linked_words

        rep_list = []

        if rep_type == db.word_type.TEXT:
            rep_list.append(bot.line_api_wrapper.wrap_text_message(rep_content, self._webpage_generator))

            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), recv_msg_type, db.msg_type.TEXT)
        elif rep_type == db.word_type.STICKER:
            rep_list.append(bot.line_api_wrapper.wrap_image_message((bot.line_api_wrapper.sticker_png_url(rep_content))))

            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), recv_msg_type, db.msg_type.STICKER)
        elif rep_type == db.word_type.PICTURE:
            rep_list.append(bot.line_api_wrapper.wrap_image_message(rep_content))
            
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), recv_msg_type, db.msg_type.PICTURE)
        else:
            raise ValueError(u'Unknown word type for reply. {}'.format(rep_type))

        if rep_att is not None and (rep_type == db.word_type.STICKER or rep_type == db.word_type.PICTURE):
            rep_list.append(bot.line_api_wrapper.wrap_text_message(rep_att, self._webpage_generator))

        if len(rep_link) > 0:
            # Max label text length is 20. Ref: https://developers.line.me/en/docs/messaging-api/reference/#template-action
            action_dict = { ext.simplify_string(word, 17): word for word in rep_link }
            alt_text = u'相關字詞: {}'.format(u'、'.join(word for word in rep_link))

            rep_list.append(bot.line_api_wrapper.wrap_template_with_action(action_dict, alt_text, u'相關回覆組'))
        
        self._line_api_wrapper.reply_message(token, rep_list) 

    def _handle_auto_ban(self, event, content, content_type):
        token = event.reply_token
        src = event.source
        uid = bot.line_api_wrapper.source_user_id(src)
        cid = bot.line_api_wrapper.source_channel_id(src)

        banned = self._loop_preventer.rec_last_content_and_get_status(uid, cid, content, content_type)

        if banned:
            pw_notice_text = self._loop_preventer.get_pw_notice_text(uid, self._line_api_wrapper)
            if pw_notice_text is not None:
                self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), content_type, db.msg_type.TEXT)
                self._line_api_wrapper.reply_message_text(token, pw_notice_text)
            else:
                unlock_result = self._loop_preventer.unlock(uid, content)
                if unlock_result is not None:
                    self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), content_type, db.msg_type.TEXT)
                    self._line_api_wrapper.reply_message_text(token, unlock_result)

            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), content_type, db.msg_type.TEXT)

            return True

        return False

    def _print_intercepted(self, event):
        intercept = self._system_config.get(db.config_data.INTERCEPT)
        intercept_display_name = self._system_config.get(db.config_data.INTERCEPT_DISPLAY_NAME)
        if intercept:
            src = event.source
            uid = bot.line_api_wrapper.source_user_id(src)

            if intercept_display_name:
                try:
                    user_name = self._line_api_wrapper.profile_name(uid)
                    if user_name is None:
                        user_name = 'Empty'
                except bot.UserProfileNotFoundError:
                    user_name = 'Unknown'
            else:
                user_name = '(Set to not to display.)'

            print '==========================================='
            print 'From Channel ID \'{}\''.format(bot.line_api_wrapper.source_channel_id(src))
            print 'From User ID \'{}\' ({})'.format(uid, user_name.encode('utf-8'))
            if isinstance(event.message, TextMessage):
                print 'Message \'{}\''.format(event.message.text.encode('utf-8'))
            elif isinstance(event.message, StickerMessage):
                print 'Sticker ID: {} Package ID: {}'.format(event.message.sticker_id, event.message.package_id)
            elif isinstance(event.message, LocationMessage):
                print 'Latitude: {} Longitude: {}'.format(event.message.latitude, event.message.longitude)
            else:
                print '(intercept output not implemented.)'
                print event.message
            print '=================================================================='

    def _get_group_config(self, cid):
        return self._group_manager.get_group_config_type(cid)

    def _get_user_permission(self, src):
        src_gid = bot.line_api_wrapper.source_channel_id(src)
        src_uid = bot.line_api_wrapper.source_user_id(src)
        return self._group_manager.get_user_permission(src_gid, src_uid)

    def _chinese_convert_to_trad(self, text):
        text = text.replace(u'群', u'-{群}-')

        return zhconv.convert_for_mw(text, 'zh-hant')

    def _strip(self, text):
        return text.strip()

    #############################
    ### HANDLE TEXT - PRIVATE ###
    #############################

    def _handle_text_sys_config(self, event):
        """Return whether message has been replied."""
        full_text = event.message.text

        action_dict = { self._silence_key: (db.config_data.SILENCE, 'BOT SILENCE: {}'),
                        self._intercept_key: (db.config_data.INTERCEPT, 'MESSAGE INTERCEPTION: {}'),
                        self._intercept_display_name_key: (db.config_data.INTERCEPT_DISPLAY_NAME, 'DISPLAY NAME IN MESSAGE INTERCEPTION: {}'),
                        self._calc_debug_key: (db.config_data.CALCULATOR_DEBUG, 'CALCULATOR DEBUG: {}'),
                        self._rep_error_key: (db.config_data.REPLY_ERROR, 'REPLY ON ERROR: {}'),
                        self._send_error_report_key: (db.config_data.SEND_ERROR_REPORT, 'SEND ERROR REPORT: {}') }

        action = action_dict.get(full_text, None)
        if action is not None:
            new_setting = self._system_config.set(action[0], not self._system_config.get(action[0])).get(action[0])
            self._line_api_wrapper.reply_message_text(event.reply_token, action[1].format('ENABLED' if new_setting else 'DISABLED'))
            return True

        return False

    def _handle_text_sys_command(self, event, user_permission, group_config_type):
        """Return whether message has been replied."""
        full_text = unicode(event.message.text)
        if text_msg_handler.can_try_handle(full_text):
            return self._txt_handle.handle_text(event, user_permission, group_config_type)
        elif game_msg_handler.can_try_handle(full_text):
            return self._game_handle.handle_text(event, user_permission)

        return False

    def _handle_text_rps(self, event):
        """Return whether message has been replied."""
        content = event.message.text
        src = event.source
        src_cid = bot.line_api_wrapper.source_channel_id(src)
        src_uid = bot.line_api_wrapper.source_user_id(src)

        rps_result = self._rps_data.play(src_cid, src_uid, content, False)

        if rps_result is not None and all(rps_result != res_str for res_str in (db.rps_message.error.game_instance_not_exist(), db.rps_message.error.game_is_not_enabled(), db.rps_message.error.player_data_not_found(), db.rps_message.error.unknown_battle_item())):
            self._system_stats.command_called(u'猜拳遊戲')
            self._line_api_wrapper.reply_message_text(event.reply_token, rps_result)
            return True  

        return False

    def _handle_text_auto_reply(self, event, config):
        """Return whether message has been replied. THIS WILL LOG MESSAGE ACTIVITY INSIDE METHOD IF MESSAGE HAS BEEN REPLIED."""
        full_text = event.message.text
        src = event.source
        reply_data = self._get_kwd_instance(src, config).get_reply_data(full_text)
        if reply_data is not None:
            self._handle_auto_reply(event, reply_data)
            return True

        return False

    def _handle_text_str_calc(self, event):
        """Return whether message has been replied."""
        full_text = event.message.text
        calc_result = self._string_calculator.calculate(full_text, self._system_config.get(db.config_data.CALCULATOR_DEBUG), event.reply_token)
        if calc_result.success:
            self._system_stats.extend_function_used(db.extend_function_category.BASIC_CALCUALTE)
                
            result_text = calc_result.get_basic_text()

            if calc_result.latex_avaliable:
                latex_url = self._webpage_generator.rec_webpage(calc_result.latex, db.webpage_content_type.LATEX)
                result_text += u'\nLaTeX: {}'.format(latex_url)

            if u'^' in full_text:
                result_text += u'\n'
                result_text += error.warning.txt_calc.possible_wrong_operator_pow()

            self._line_api_wrapper.reply_message_text(calc_result.token, result_text) 
            return True

        return False

    def _handle_text_spec_text(self, event):
        token = event.reply_token
        text = event.message.text

        replied = self._spec_txt_handle.handle_text(event)

        if replied:
            self._system_stats.extend_function_used(db.extend_function_category.SPECIAL_TEXT_KEYWORD)

        return replied

    ############################
    ### HANDLE TEXT - PUBLIC ###
    ############################

    def handle_text(self, event):
        event.message.text = self._strip(event.message.text)
        event.message.text = self._chinese_convert_to_trad(event.message.text)

        self._print_intercepted(event)

        src = event.source
        token = event.reply_token
        full_text = event.message.text

        if full_text == 'ERRORERRORERRORERROR':
            raise Exception('THIS ERROR IS CREATED FOR TESTING PURPOSE.')

        #########################################################
        ### TERMINATE CHECK - MAIN SYSTEM CONFIG CHANGING KEY ###
        #########################################################

        terminate = self._handle_text_sys_config(event)

        if terminate:
            print 'terminate - changing system config'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT, db.msg_type.TEXT)
            return

        ####################################################
        ### TERMINATE CHECK - SILENCE CONFIG FROM SYSTEM ###
        ####################################################

        terminate = self._terminate()
        if terminate:
            print 'terminate - system config set to silence'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT)
            return

        ##############################################
        ######## ASSIGN NECESSARY VARIABLES 1 ########
        ##############################################

        cid = bot.line_api_wrapper.source_channel_id(src)
        uid = bot.line_api_wrapper.source_user_id(src)
        
        self._system_data.set(bot.system_data_category.LAST_MESSAGE, cid, full_text)

        #####################################
        ### TERMINATE CHECK - LOOP TO BAN ###
        #####################################

        terminate = self._handle_auto_ban(event, full_text, db.msg_type.TEXT)

        if terminate:
            print 'terminate - user auto ban temporarily'
            return

        ##############################################
        ######## ASSIGN NECESSARY VARIABLES 2 ########
        ##############################################

        group_config = self._get_group_config(cid)
        user_permission = self._get_user_permission(src)
        self._system_data.set(bot.system_data_category.LAST_UID, cid, uid)

        #########################################
        ### TERMINATE CHECK - USER RESTIRCTED ###
        #########################################

        terminate = user_permission == bot.permission.RESTRICTED

        if terminate:
            print 'terminate - group set to silence or user is restricted'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT)
            return

        #########################################
        ### TERMINATE CHECK - TEXT CALCULATOR ###
        #########################################

        terminate = self._handle_text_str_calc(event)

        if terminate:
            print 'terminate - text calculator used'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT, db.msg_type.TEXT)
            return

        ####################################
        ### TERMINATE CHECK - GAME (RPS) ###
        ####################################
        
        terminate = self._handle_text_rps(event)

        if terminate:
            print 'terminate - game (Rock-Paper-Scissor) action submitted'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT, db.msg_type.TEXT)
            return

        ########################################
        ### TERMINATE CHECK - SYSTEM COMMAND ###
        ########################################

        terminate = self._handle_text_sys_command(event, user_permission, group_config)

        if terminate or group_config <= db.group_data_range.SYS_ONLY:
            print 'terminate - system command'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT, db.msg_type.TEXT)
            return

        #########################################
        ### TERMINATE CHECK - SPECIAL KEYWORD ###
        #########################################
        
        terminate = self._handle_text_spec_text(event)
             
        if terminate:
            print 'terminate - special keyword'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT, db.msg_type.TEXT)
            return

        ####################################
        ### TERMINATE CHECK - AUTO REPLY ###
        ####################################

        terminate = self._handle_text_auto_reply(event, group_config)
             
        if terminate:
            print 'terminate - auto reply system'
            return

        self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.TEXT)

    ################################
    ### HANDLE STICKER - PRIVATE ###
    ################################

    def _handle_sticker_rps(self, event, sticker_id):
        """Return whether message has been replied."""
        content = event.message.sticker_id
        src = event.source
        src_cid = bot.line_api_wrapper.source_channel_id(src)
        src_uid = bot.line_api_wrapper.source_user_id(src)

        rps_result = self._rps_data.play(src_cid, src_uid, content, True)

        if rps_result is not None and all(rps_result != res_str for res_str in (db.rps_message.error.game_instance_not_exist(), db.rps_message.error.game_is_not_enabled(), db.rps_message.error.player_data_not_found(), db.rps_message.error.unknown_battle_item())):
            self._system_stats.command_called(u'猜拳遊戲')
            self._line_api_wrapper.reply_message_text(event.reply_token, rps_result)
            return True  

        return False

    def _handle_sticker_data(self, event):
        """Return whether message has been replied."""
        if bot.line_event_source_type.determine(event.source) == bot.line_event_source_type.USER:
            self._system_stats.extend_function_used(db.extend_function_category.GET_STICKER_ID)
            sticker_id = event.message.sticker_id
            package_id = event.message.package_id

            action_dict = { '貼圖包下載 - {}'.format(package_id): text_msg_handler.CH_HEAD + u'下載貼圖圖包 ' + str(package_id) }
            
            reply_data = [
                bot.line_api_wrapper.wrap_text_message(u'貼圖圖包ID: {}\n貼圖圖片ID: {}'.format(package_id, sticker_id), self._webpage_generator),
                bot.line_api_wrapper.wrap_template_with_action(action_dict, u'貼圖圖包下載樣板', '圖包下載')
            ]

            self._line_api_wrapper.reply_message(event.reply_token, reply_data)
            return True
        
        return False

    def _handle_sticker_auto_reply(self, event, config):
        """Return whether message has been replied. THIS WILL LOG MESSAGE ACTIVITY INSIDE METHOD IF MESSAGE HAS BEEN REPLIED."""
        reply_data = self._get_kwd_instance(event.source, config).get_reply_data(unicode(event.message.sticker_id), db.word_type.STICKER)
        if reply_data is not None:
            self._handle_auto_reply(event, reply_data)
            return True

        return False

    ###############################
    ### HANDLE STICKER - PUBLIC ###
    ###############################

    def handle_sticker(self, event):
        package_id = event.message.package_id
        sticker_id = event.message.sticker_id
        token = event.reply_token
        src = event.source
        cid = bot.line_api_wrapper.source_channel_id(src)
        uid = bot.line_api_wrapper.source_user_id(src)
        
        self._print_intercepted(event)
        self._stk_rec.record(package_id, sticker_id)
        
        ####################################################
        ### TERMINATE CHECK - SILENCE CONFIG FROM SYSTEM ###
        ####################################################
        
        terminate = self._terminate()
        
        if terminate:
            print 'terminate - system config set to silence'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.STICKER)
            return

        ############################################
        ######## ASSIGN NECESSARY VARIABLES ########
        ############################################

        group_config = self._get_group_config(bot.line_api_wrapper.source_channel_id(src))
        user_permission = self._get_user_permission(src)

        self._system_data.set(bot.system_data_category.LAST_UID, cid, uid)
        self._system_data.set(bot.system_data_category.LAST_STICKER, cid, bot.sticker_data(package_id, sticker_id))

        #######################################################
        ### TERMINATE CHECK - GROUP CONFIG IS SILENCE CHECK ###
        #######################################################

        terminate = group_config <= db.group_data_range.SILENCE or user_permission == bot.permission.RESTRICTED

        if terminate:
            print 'terminate - group set to silence or user is restricted'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.STICKER)
            return

        #####################################
        ### TERMINATE CHECK - LOOP TO BAN ###
        #####################################

        terminate = self._handle_auto_ban(event, sticker_id, db.msg_type.STICKER)

        if terminate:
            print 'terminate - user auto ban temporarily'
            return

        ####################################
        ### TERMINATE CHECK - GAME (RPS) ###
        ####################################

        terminate = self._handle_sticker_rps(event, sticker_id)

        if terminate or group_config <= db.group_data_range.SYS_ONLY:
            print 'terminate - game (Rock-Paper-Scissor) action submitted'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.STICKER, db.msg_type.TEXT)
            return

        ######################################
        ### TERMINATE CHECK - STICKER DATA ###
        ######################################

        terminate = self._handle_sticker_data(event)

        if terminate:
            print 'terminate - sticker data requested'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.STICKER, db.msg_type.TEXT)
            return

        ####################################
        ### TERMINATE CHECK - AUTO REPLY ###
        ####################################

        terminate = self._handle_sticker_auto_reply(event, group_config)

        if terminate:
            print 'terminate - auto reply system'
            return

        self._group_manager.log_message_activity(cid, db.msg_type.STICKER)

    ##############################
    ### HANDLE IMAGE - PRIVATE ###
    ##############################

    def _handle_image_upload(self, event, image_sha):
        if bot.line_event_source_type.determine(event.source) == bot.line_event_source_type.USER:
            self._system_stats.extend_function_used(db.extend_function_category.IMGUR_UPLOAD)
            upload_result = self._img_handle.upload_imgur(event.message)

            rep_list = [bot.line_api_wrapper.wrap_text_message(u'檔案雜湊碼(SHA224)', self._webpage_generator), 
                        bot.line_api_wrapper.wrap_text_message(image_sha, self._webpage_generator)]

            if upload_result.image_url is not None:
                rep_list.append(bot.line_api_wrapper.wrap_text_message(upload_result.result_string, self._webpage_generator))
                rep_list.append(bot.line_api_wrapper.wrap_text_message(upload_result.image_url, self._webpage_generator))

            self._line_api_wrapper.reply_message(event.reply_token, rep_list)
            return True

        return False

    def _handle_image_auto_reply(self, event, image_sha, config):
        """Return whether message has been replied. THIS WILL LOG MESSAGE ACTIVITY INSIDE METHOD IF MESSAGE HAS BEEN REPLIED."""
        reply_data = self._get_kwd_instance(event.source, config).get_reply_data(image_sha, db.word_type.PICTURE)
        if reply_data is not None:
            self._handle_auto_reply(event, reply_data)
            return True

        return False

    #############################
    ### HANDLE IMAGE - PUBLIC ###
    #############################

    def handle_image(self, event):
        src = event.source
        token = event.reply_token
        cid = bot.line_api_wrapper.source_channel_id(src)
        uid = bot.line_api_wrapper.source_user_id(src)

        ####################################################
        ### TERMINATE CHECK - SILENCE CONFIG FROM SYSTEM ###
        ####################################################
        
        terminate = self._terminate()
        
        if terminate:
            print 'terminate - system config set to silence'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.PICTURE)
            return

        ############################################
        ######## ASSIGN NECESSARY VARIABLES ########
        ############################################

        group_config = self._get_group_config(cid)
        user_permission = self._get_user_permission(src)
        image_sha = self._img_handle.image_sha224_of_message(event.message)
        
        self._system_data.set(bot.system_data_category.LAST_UID, cid, uid)
        self._system_data.set(bot.system_data_category.LAST_PIC_SHA, cid, image_sha)

        #######################################################
        ### TERMINATE CHECK - GROUP CONFIG IS SILENCE CHECK ###
        #######################################################

        terminate = group_config <= db.group_data_range.SYS_ONLY or user_permission == bot.permission.RESTRICTED

        if terminate:
            print 'terminate - group set to silence or user is restricted'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.PICTURE)
            return

        #####################################
        ### TERMINATE CHECK - LOOP TO BAN ###
        #####################################

        terminate = self._handle_auto_ban(event, image_sha, db.msg_type.PICTURE)

        if terminate:
            print 'terminate - user auto ban temporarily'
            return

        ######################################
        ### TERMINATE CHECK - UPLOAD IMAGE ###
        ######################################
        
        terminate = self._handle_image_upload(event, image_sha)
        
        if terminate:
            print 'terminate - image uploading'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.PICTURE, db.msg_type.TEXT, 1, 4)
            return

        ####################################
        ### TERMINATE CHECK - AUTO REPLY ###
        ####################################
        
        terminate = self._handle_image_auto_reply(event, image_sha, group_config)
             
        if terminate:
            print 'terminate - auto reply system'
            return

        self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.PICTURE)

    #################################
    ### HANDLE LOCATION - PRIVATE ###
    #################################

    def _handle_location_weather(self, event):
        src = event.source
        token = event.reply_token

        latitude = event.message.latitude
        longitude = event.message.longitude

        src_type = bot.line_event_source_type.determine(src)

        if src_type == bot.line_event_source_type.GROUP or src_type == bot.line_event_source_type.ROOM:
            op_config = tool.weather.output_type.SIMPLE
        elif src_type == bot.line_event_source_type.USER:
            op_config = tool.weather.output_type.DETAIL
        else:
            raise NotImplementedError(src_type)

        reply_text = self._weather_reporter.get_data_by_coord(tool.weather.Coordinate(latitude, longitude), op_config, 3, 9)
        if reply_text is not None:
            self._system_stats.extend_function_used(db.extend_function_category.REQUEST_WEATHER_REPORT)

            self._line_api_wrapper.reply_message_text(token, reply_text)
            return True

        return False

    ################################
    ### HANDLE LOCATION - PUBLIC ###
    ################################

    def handle_location(self, event):
        src = event.source
        token = event.reply_token
        cid = bot.line_api_wrapper.source_channel_id(src)
        uid = bot.line_api_wrapper.source_user_id(src)

        self._print_intercepted(event)

        ####################################################
        ### TERMINATE CHECK - SILENCE CONFIG FROM SYSTEM ###
        ####################################################
        
        terminate = self._terminate()
        
        if terminate:
            print 'terminate - system config set to silence'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.LOCATION)
            return

        ############################################
        ######## ASSIGN NECESSARY VARIABLES ########
        ############################################

        group_config = self._get_group_config(cid)
        user_permission = self._get_user_permission(src)

        latitude = event.message.latitude
        longitude = event.message.longitude

        #######################################################
        ### TERMINATE CHECK - GROUP CONFIG IS SILENCE CHECK ###
        #######################################################

        terminate = group_config <= db.group_data_range.SYS_ONLY or user_permission == bot.permission.RESTRICTED

        if terminate:
            print 'terminate - group set to silence or user is restricted'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.LOCATION)
            return

        #####################################
        ### TERMINATE CHECK - LOOP TO BAN ###
        #####################################

        terminate = self._handle_auto_ban(event, (latitude, longitude), db.msg_type.LOCATION)

        if terminate:
            print 'terminate - user auto ban temporarily'
            return

        ########################################
        ### TERMINATE CHECK - REPORT WEATHER ###
        ########################################

        terminate = self._handle_location_weather(event)

        if terminate:
            print 'terminate - weather of location reported'
            self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.LOCATION)
            return

        self._group_manager.log_message_activity(bot.line_api_wrapper.source_channel_id(src), db.msg_type.LOCATION)
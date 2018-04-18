# -*- coding: utf-8 -*-

import bot, db, tool
from error import error

from .misc import *

class game_msg_handler(object):
    HEAD = u'小遊戲 '
    SPLITTER = u'\n'

    def __init__(self, mongo_client, line_api_wrapper):
        self._rps_holder = db.rps_holder(mongo_client)
        self._line_api_wrapper = line_api_wrapper
        
    def handle_text(self, event, user_permission):
        """Return whether message has been replied"""
        token = event.reply_token
        text = unicode(event.message.text)
        src = event.source

        src_uid = bot.line_api_wrapper.source_user_id(src)

        if user_permission == bot.permission.RESTRICTED:
            self._line_api_wrapper.reply_message_text(token, error.permission.user_is_resticted())
            return True

        cmd_data = None
        for cmd_kw, cmd_obj in bot.game_cmd_dict.iteritems():
            if text.upper().startswith(game_msg_handler.HEAD + cmd_kw):
                cmd_data = cmd_obj
                break

        if cmd_data is None:
            print 'Called an not existed command.'
            return False

        cmd_function = getattr(self, '_{}'.format(cmd_data.function_code))

        handle_result = cmd_function(src, user_permission, text)
        if handle_result is None:
            return self._line_api_wrapper.reply_message_text(token, error.sys_command.syntax_error(cmd_data.function_code))
        else:
            if isinstance(handle_result, (str, unicode)):
                self._line_api_wrapper.reply_message_text(token, handle_result)
                return True
            else:
                self._line_api_wrapper.reply_message(token, handle_result)
                return True

        return False
    
    def _RPS(self, src, executor_permission, text):
        regex_list = [ur'小遊戲 猜拳(狀況|啟用|停用|重設|註冊|結束)',
                      ur'小遊戲 猜拳開始 ?(\d+) (\d+) (\d+)',
                      ur'小遊戲 猜拳代表 ?(剪刀|石頭|布) ?((貼圖) ?(\d+)|(\w+))']
        
        regex_result = tool.regex_finder.find_match(regex_list, text)

        if regex_result is None:
            return
        
        executor_cid = bot.line_api_wrapper.source_channel_id(src)
        executor_uid = bot.line_api_wrapper.source_user_id(src)

        if regex_result.match_at == 0:
            action = regex_result.group(1)

            if action == u'狀況':
                return self._rps_holder.game_statistics(executor_cid)
            elif action == u'啟用':
                return self._rps_holder.set_enabled(executor_cid, True)
            elif action == u'停用':
                return self._rps_holder.set_enabled(executor_cid, True)
            elif action == u'重設':
                return self._rps_holder.reset_statistics(executor_cid)
            elif action == u'結束':
                return self._rps_holder.delete_game(executor_cid)
            elif action == u'註冊':
                try:
                    player_name = self._line_api_wrapper.profile_name(executor_uid)
                except bot.UserProfileNotFoundError:
                    return error.line_bot_api.unable_to_receive_user_id()

                if bot.line_api_wrapper.is_valid_user_id(executor_uid):
                    return self._rps_holder.register_player(executor_cid, executor_uid, player_name)
                else:
                    return error.line_bot_api.unable_to_receive_user_id()
            else:
                return error.sys_command.action_not_implemented(u'RPS', regex_result.match_at, action)
        elif regex_result.match_at == 1:
            scissor = regex_result.group(1)
            rock = regex_result.group(2)
            paper = regex_result.group(3)

            try:
                creator_name = self._line_api_wrapper.profile_name(executor_uid)
            except bot.UserProfileNotFoundError:
                return error.line_bot_api.unable_to_receive_user_id()

            return self._rps_holder.create_game(executor_cid, executor_uid, creator_name, rock, paper, scissor)
        elif regex_result.match_at == 2:
            repr_dict = { u'剪刀': db.battle_item.SCISSOR, u'石頭': db.battle_item.ROCK, u'布': db.battle_item.PAPER }
            repr = repr_dict.get(regex_result.group(1))
            if repr is None:
                return error.sys_command.action_not_implemented(u'RPS', regex_result.match_at, repr)

            is_sticker = regex_result.group(3) is not None

            if is_sticker:
                repr_content = regex_result.group(4)
            else:
                repr_content = regex_result.group(5)
                
            return self._rps_holder.register_battleitem(executor_cid, repr_content, is_sticker, repr)
        else:
            raise RegexNotImplemented(error.sys_command.regex_not_implemented(u'RPS', regex_result.match_at, regex_result.regex))

    @staticmethod
    def can_try_handle(full_text):
        full_text = full_text.upper()
        return full_text.startswith(game_msg_handler.HEAD)

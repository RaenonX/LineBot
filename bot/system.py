# -*- coding: utf-8 -*-

import os, sys
import time
import requests
from datetime import datetime, timedelta
from collections import deque
from sets import Set
import json

import hashlib
import operator
import traceback

from linebot import exceptions

from linebot.models import (
    SourceGroup, SourceRoom, SourceUser,
    TextSendMessage, ImageSendMessage, TemplateSendMessage,
    CarouselTemplate, ButtonsTemplate, CarouselColumn, MessageTemplateAction, URITemplateAction
)


import error, tool

import db, bot
import ext
from .config import config_manager

class system_data_category(ext.EnumWithName):
    LAST_STICKER = 0, '最近貼圖ID'
    LAST_PIC_SHA = 1, '最近圖片雜湊(SHA224)'
    LAST_PAIR_ID = 2, '最近回覆組ID'
    LAST_UID = 3, '最近訊息傳送者(不含小水母)UID'
    LAST_MESSAGE = 4, '最近訊息'

class system_data(object):
    EXPIRE_SEC = 15 * 60

    def __init__(self):
        self._boot_up = datetime.now() + timedelta(hours=8)

        self._field_dict = { e: {} for e in list(system_data_category) }

    def set(self, category_enum, cid, content):
        d = self._field_dict[category_enum]

        if cid not in d:
            d[cid] = tool.ttldict.TTLOrderedDict(system_data.EXPIRE_SEC)

        d[cid][time.time()] = content
        self._field_dict[category_enum] = d

    def get(self, category_enum, cid):
        return self._field_dict[category_enum].get(cid)

    @property
    def boot_up(self):
        return self._boot_up

class infinite_loop_preventer(object):
    def __init__(self, max_loop_count, unlock_pw_length):
        self._last_message = {}
        self._max_loop_count = max_loop_count
        self._unlock_pw_length = unlock_pw_length

    def rec_last_content_and_get_status(self, uid, cid, content, msg_type):
        if uid in self._last_message:
            banned = self._last_message[uid].banned
            if banned:
                return True
            self._last_message[uid].rec_content(cid, content, msg_type)
        else:
            self._last_message[uid] = infinite_loop_prevent_data(self._max_loop_count, uid, self._unlock_pw_length, cid, content, msg_type)

        return self._last_message[uid].banned

    def get_all_banned_str(self):
        banned_dict = dict((k, v) for k, v in self._last_message.iteritems() if v.banned)
        if len(banned_dict) < 1:
            return u'(無)'
        output = []
        for k, v in banned_dict.iteritems():
            output.append(u'UUID: {}\n驗證碼: {}\n訊息紀錄:\n{}'.format(k, v.unlock_key, v.rec_content_str()))
        return u'\n==========\n'.join(output)

    def get_pw_notice_text(self, uid, line_api_wrapper):
        """Return None if pw is generated. Else, return str."""
        if uid is None:
            return

        if uid in self._last_message:
            data = self._last_message[uid]
            data.unlock_noticed = True
            pw = data.generate_pw()
            if pw is not None:
                try:
                    user_name = line_api_wrapper.profile_name(uid)
                except UserProfileNotFoundError:
                    user_name = u'(不明)'

                return u'目標: {} ({})\n\n因於同頻道中，連續發送相同的訊息內容、訊息文字超過{}次，有洗板、濫用小水母之疑慮，故小水母已鎖定使用者的所有操作。請輸入驗證碼以解鎖。\n驗證碼: {}。\n\n訊息紀錄:\n{}'.format(uid, user_name, self._max_loop_count, pw, data.rec_content_str())
        else:
            self._last_message[uid] = infinite_loop_prevent_data(self._max_loop_count, uid, self._unlock_pw_length)

    def unlock(self, uid, password):
        """Return str if unlocked. Else, return None."""
        if uid in self._last_message:
            data = self._last_message[uid]
            data.unlock_noticed = False
            unlock_result = data.unlock(password)
            if unlock_result:
                return u'使用者UUID: {}\n解鎖成功。'.format(uid)
        else:
            self._last_message[uid] = infinite_loop_prevent_data(self._max_loop_count, uid, self._unlock_pw_length)

class infinite_loop_prevent_data(object):
    def __init__(self, max_loop_count, uid, unlock_pw_length, init_cid=None, init_content=None, init_content_type=db.msg_type.TEXT):
        self._uid = uid
        self._max_loop_count = max_loop_count
        self._repeat_count = int(init_content is not None)
        self._message_record = deque(maxlen=max_loop_count)
        if self._repeat_count == 1:
            self.rec_content(init_cid, init_content, init_content_type)

        self._unlock_noticed = False
        self._unlock_key = None
        self._unlock_key_length = unlock_pw_length

    @property
    def user_id(self):
        return self._uid

    @property
    def banned(self):
        return self._repeat_count >= self._max_loop_count

    @property
    def unlock_key(self):
        return self._unlock_key

    @property
    def unlock_noticed(self):
        return self._unlock_noticed

    @unlock_noticed.setter
    def unlock_noticed(self, value):
        self._unlock_noticed = value

    def generate_pw(self):
        """if generated, return None"""
        if self._unlock_key is None:
            self._unlock_key = tool.random_drawer.generate_random_string(self._unlock_key_length)
            return self._unlock_key

    def unlock(self, password):
        """Clear password if success. Return result of unlocking."""
        if password == self._unlock_key:
            self._repeat_count = 0
            self._unlock_key = None
            return True

        return False

    def rec_content(self, cid, content, msg_type):
        new_data = message_pack(content, cid, msg_type)

        msg_rec_count = len(self._message_record)
        if msg_rec_count > 0:
            last_data = self._message_record[msg_rec_count - 1]
        else:
            last_data = None 

        self._message_record.append(new_data)

        if new_data == last_data:
            self._repeat_count += 1
        else:
            self._repeat_count = 0

    def rec_content_str(self):
        """Only gives unique result"""
        content_set = Set([])
        msgtype_set = Set([])
        timestamp_set = Set([])
        cid_set = Set([])
        for msg_pack in self._message_record:
            content_set.add(msg_pack.content)
            msgtype_set.add(unicode(msg_pack.msg_type))
            timestamp_set.add(msg_pack.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'))
            cid_set.add(msg_pack.channel_id)

        return u'發送頻道ID: {}\n內容: {}\n訊息種類: {}\n時間: {}'.format(u'、'.join(cid_set), u'、'.join(content_set), u'、'.join(msgtype_set), u'、'.join(timestamp_set))

class message_pack(object):
    def __init__(self, content, channel_id, msg_type=db.msg_type.TEXT):
        self._content = content
        self._channel_id = channel_id
        self._msg_type = msg_type
        self._timestamp = datetime.now() + timedelta(hours=8)

    def __eq__(self, other):
        if other is None:
            return False

        def equal_dicts(d1, d2, ignore_keys):
            ignored = set(ignore_keys)
            for k1, v1 in d1.iteritems():
                if k1 not in ignored and (k1 not in d2 or d2[k1] != v1):
                    return False
            for k2, v2 in d2.iteritems():
                if k2 not in ignored and k2 not in d1:
                    return False
            return True

        return equal_dicts(self.__dict__, other.__dict__, ['_timestamp'])

    @property
    def content(self):
        return self._content
    
    @property
    def channel_id(self):
        return self._channel_id
    
    @property
    def msg_type(self):
        return self._msg_type
    
    @property
    def timestamp(self):
        return self._timestamp

class line_event_source_type(ext.EnumWithName):
    USER = 0, '私訊'
    GROUP = 1, '群組'
    ROOM = 2, '房間'

    @staticmethod
    def determine(event_source):
        if isinstance(event_source, SourceUser):
            return line_event_source_type.USER
        elif isinstance(event_source, SourceGroup):
            return line_event_source_type.GROUP
        elif isinstance(event_source, SourceRoom):
            return line_event_source_type.ROOM
        else:
            raise ValueError(u'Undefined type of event source instance. {}'.format(event_source))

class line_api_wrapper(object):
    TEST_REPLY_TOKEN = "TEST"
    LEGAL_ID_LENGTH = 33

    def __init__(self, line_api, webpage_generator, mongo_client):
        self._line_api = line_api
        self._webpage_generator = webpage_generator
        self._uid_ref = db.user_id_ref_manager(mongo_client)
        self._cache_profile = {}

    def acquire_uid(self, uid):
        if isinstance(uid, (str, unicode)):
            if line_api_wrapper.is_valid_user_id(uid):
                return uid
            else:
                raise ValueError(u'Illegal LINE UID: {}'.format(uid))
        elif isinstance(uid, int):
            uid = self._uid_ref.get_uid(uid)

            if uid is None:
                self._uid_ref.get_ref_id_or_record(uid)

            return uid
        else:
            raise ValueError(u'unknown/unhandled uid data: {} / {}'.format(uid, type(uid)))

    def profile(self, uid, src=None):
        print "(uid in self._cache_profile)"
        print (uid in self._cache_profile)
        print "uid"
        print uid
        print "src"
        print src
        if uid not in self._cache_profile:
            try:
                uid = self.acquire_uid(uid)
                profile = self.profile_friend_list(uid)
                
                print "profile"
                print profile
                print "src"
                print src

                if profile is not None:
                    self._cache_profile[uid] = profile
                    return profile

                if src is None:
                    return profile
                else:
                    source_type = line_event_source_type.determine(src)
                    print "source_type"
                    print source_type
                    if source_type == line_event_source_type.USER:
                        p = profile
                    elif source_type == line_event_source_type.GROUP:
                        p = self.profile_group(line_api_wrapper.source_channel_id(src), uid)
                    elif source_type == line_event_source_type.ROOM:
                        p = self.profile_room(line_api_wrapper.source_channel_id(src), uid)
                    else:
                        raise ValueError('Instance not defined.')

                    self._cache_profile[uid] = p
                    return p
            except exceptions.LineBotApiError as ex:
                if ex.status_code == 404:
                    return None
        else:
            return self._cache_profile[uid]

    def profile_name(self, uid, src=None):
        """Raise UserProfileNotFoundError if user name is unreachable."""
        uid = self.acquire_uid(uid)
        prof = self.profile(uid, src)
        if prof is None:
            raise UserProfileNotFoundError()
        else:
            return prof.display_name

    def profile_name_safe(self, uid, src=None):
        """Return '(Unknown)' if user name is unreachable."""
        try:
            return self.profile_name(uid, src)
        except UserProfileNotFoundError:
            return u'(Unknown)'
        except ValueError:
            return u'(Unable to acquire UID)'

    def profile_group(self, gid, uid):
        try:
            print self._line_api.get_group_member_profile(gid, self.acquire_uid(uid))
            return self._line_api.get_group_member_profile(gid, self.acquire_uid(uid))
        except exceptions.LineBotApiError as ex:
            if ex.status_code == 404:
                raise UserProfileNotFoundError()
            else:
                raise ex

    def profile_room(self, rid, uid):
        try:
            return self._line_api.get_room_member_profile(rid, self.acquire_uid(uid))
        except exceptions.LineBotApiError as ex:
            if ex.status_code == 404:
                raise UserProfileNotFoundError()
            else:
                raise ex

    def profile_friend_list(self, uid):
        try:
            return self._line_api.get_profile(self.acquire_uid(uid))
        except exceptions.LineBotApiError as ex:
            if ex.status_code == 404:
                return None
            else:
                raise ex

    def get_content(self, msg_id):
        return self._line_api.get_message_content(msg_id)

    def reply_message(self, reply_token, msgs):
        if reply_token == line_api_wrapper.TEST_REPLY_TOKEN:
            print '================= REPLY ================='
            print repr(msgs).replace('\\\\', "\\").decode("unicode-escape").encode("utf-8")
            print '========================================='
        else:
            self._line_api.reply_message(reply_token, msgs)

    def reply_message_text(self, reply_token, msgs):
        if isinstance(msgs, (str, unicode)):
            msgs = [msgs]
        self.reply_message(reply_token, [line_api_wrapper.wrap_text_message(msg, self._webpage_generator) for msg in msgs])

    @staticmethod
    def source_channel_id(event_source):
        return event_source.sender_id
    
    @staticmethod
    def source_user_id(event_source):
        return event_source.user_id
    
    @staticmethod
    def is_valid_user_id(uid):
        return uid is not None and len(uid) == line_api_wrapper.LEGAL_ID_LENGTH and uid.startswith('U')
    
    @staticmethod
    def is_valid_room_group_id(gid, allow_public=False, allow_global=False):
        return gid is not None and (len(gid) == line_api_wrapper.LEGAL_ID_LENGTH and (gid.startswith('C') or gid.startswith('R')) or (allow_public and gid == bot.remote.PUBLIC_TOKEN()) or (allow_global and gid == bot.remote.GLOBAL_TOKEN()))
    
    @staticmethod
    def determine_id_type(cid):
        if cid.startswith('C'):
            return line_event_source_type.GROUP
        elif cid.startswith('R'):
            return line_event_source_type.ROOM
        elif cid.startswith('U'):
            return line_event_source_type.USER

    @staticmethod
    def wrap_template_with_action(data_dict, alt_text_unicode, title_unicode):
        """
        data_dict should follow the format below, and the length of dict must less than or equals to 30. Result may be unexpected if the format is invalid.
            {label: message}

        title will display as "{title} {index}", index is the index of carousel.
        title should be str type.

        Return TemplateSendMessage.
        """
        MAX_ACTIONS_IN_CAROUSEL = 3
        MAX_LABEL_TEXT_LENGTH = 17

        data_dict = [(key, value) for key, value in data_dict.iteritems()]

        length_action_dict = len(data_dict)

        if length_action_dict > error.error.line_bot_api.MAX_TEMPLATE_ACTIONS:
            error_msg = error.error.line_bot_api.too_many_linked_words(length_action_dict)

            return TextSendMessage(text=error_msg)

        column_list = []
        for i in range(0, length_action_dict, MAX_ACTIONS_IN_CAROUSEL):
            d = data_dict[i : i + MAX_ACTIONS_IN_CAROUSEL]

            if i >= MAX_ACTIONS_IN_CAROUSEL:
                while len(d) < MAX_ACTIONS_IN_CAROUSEL:
                    d.append((u'(空)', u'小水母'))

            explain_text = '#{} ~ {}'.format(i + 1, i + MAX_ACTIONS_IN_CAROUSEL)
            action_list = [MessageTemplateAction(label=ext.simplify_string(repr_text, MAX_LABEL_TEXT_LENGTH), text=action_text) for repr_text, action_text in d]

            column_list.append(CarouselColumn(text=explain_text, title=title_unicode, actions=action_list))

        return TemplateSendMessage(alt_text=alt_text_unicode, template=CarouselTemplate(columns=column_list))
    
    @staticmethod
    def wrap_image_message(picture_url, preview_url=None):
        """
        Return ImageSendMessage.
        """
        MAX_URL_CHARACTER_LENGTH = 1000 # Ref: https://developers.line.me/en/docs/messaging-api/reference/#image

        if len(picture_url) > MAX_URL_CHARACTER_LENGTH:
            raise ValueError(u'String length of picture_url must less than or equals to {}.'.format(MAX_URL_CHARACTER_LENGTH))

        if preview_url is not None and len(preview_url) > MAX_URL_CHARACTER_LENGTH:
            raise ValueError(u'String length of preview_url must less than or equals to {}.'.format(MAX_URL_CHARACTER_LENGTH))

        if preview_url is None:
            preview_url = picture_url

        return ImageSendMessage(original_content_url=picture_url, preview_image_url=preview_url)

    @staticmethod
    def wrap_text_message(text, webpage_gen):
        """
        Return TextSendMessage.
        """
        length = len(text)

        if isinstance(text, str):
            text = text.decode('utf-8')

        count_nl = text.count('\n')
        count_unl = text.count(u'\n')

        if length > error.error.line_bot_api.MAX_CHARACTER_COUNT:
            text = error.error.line_bot_api.text_length_too_long(length, error.error.line_bot_api.MAX_CHARACTER_COUNT, webpage_gen.rec_webpage(text, db.webpage_content_type.TEXT))  
        elif count_nl > error.error.line_bot_api.MAX_NEWLINE:
            text = error.error.line_bot_api.too_many_newlines(count_nl, error.error.line_bot_api.MAX_NEWLINE, webpage_gen.rec_webpage(text, db.webpage_content_type.TEXT))
        elif count_unl > error.error.line_bot_api.MAX_NEWLINE:
            text = error.error.line_bot_api.too_many_newlines(count_unl, error.error.line_bot_api.MAX_NEWLINE, webpage_gen.rec_webpage(text, db.webpage_content_type.TEXT))

        return TextSendMessage(text=text)

    @staticmethod
    def introduction_template():
        buttons_template = ButtonsTemplate(title='機器人簡介', text='歡迎使用小水母！', 
                actions=[URITemplateAction(label='點此開啟使用說明', uri='https://sites.google.com/view/jellybot'),
                         URITemplateAction(label='點此導向問題回報網址', uri='https://github.com/RaenonX/LineBot/issues'),
                         URITemplateAction(label='群組管理權限申請單', uri='https://goo.gl/forms/91RWtMKZNMvGrpk32')])
        return TemplateSendMessage(alt_text='機器人簡介', template=buttons_template)

    @staticmethod
    def sticker_png_url(sticker_id):
        return 'https://sdl-stickershop.line.naver.jp/stickershop/v1/sticker/{}/android/sticker.png'.format(sticker_id)

    @staticmethod
    def sticker_apng_url(sticker_id):
        return 'https://sdl-stickershop.line.naver.jp/products/0/0/1/{}/android/animation/{}.png'.format(sticker_id)

    @staticmethod
    def sticker_meta(package_id):
        return 'http://dl.stickershop.line.naver.jp/products/0/0/1/{}/android/productInfo.meta'
        return 'http://dl.stickershop.line.naver.jp/products/0/0/12/{}/android/productInfo.meta'

class sticker_data(object):
    def __init__(self, pkg_id, stk_id):
        self._pkg_id = pkg_id
        self._stk_id = stk_id

    @property
    def package_id(self):
        return self._pkg_id

    @property
    def sticker_id(self):
        return self._stk_id

    def __str__(self):
        return '圖包ID: {} | 貼圖ID: {}'.format(self._pkg_id, self._stk_id)

    def __unicode__(self):
        return unicode(str(self).decode('utf-8'))

class imgur_api_wrapper(object):
    def __init__(self, imgur_api):
        self._imgur_api = imgur_api
    
    def upload(self, content, image_name):
        config = {
	    	'album': None,
	    	'name':  image_name,
	    	'title': image_name,
	    	'description': 'Automatically uploaded by line bot.(LINE ID: @fcb0332q)'
	    }
        return self._imgur_api.upload(content, config=config, anon=False)['link']

    @property
    def user_limit(self):
        return int(self._imgur_api.credits['UserLimit'])

    @property
    def user_remaining(self):
        return int(self._imgur_api.credits['UserRemaining'])

    @property
    def user_reset(self):
        """UNIX EPOCH @UTC <Type 'datetime'>"""
        return datetime.fromtimestamp(float(self._imgur_api.credits['UserReset']))

    @property
    def client_limit(self):
        return int(self._imgur_api.credits['ClientLimit'])

    @property
    def client_remaining(self):
        return int(self._imgur_api.credits['ClientRemaining'])

    def get_status_string(self, ip_addr=None):
        text = u''
        try:
            if ip_addr is not None:
                text += u'連結IP: {}\n'.format(ip_addr)
                text += u'IP可用額度: {} ({:.2%})\n'.format(self.user_remaining, float(self.user_remaining) / float(self.user_limit))
                text += u'IP上限額度: {}\n'.format(self.user_limit)
                text += u'IP積分重設時間: {} (UTC+8)\n\n'.format((self.user_reset + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'))

            text += u'目前API擁有額度: {} ({:.2%})\n'.format(self.client_remaining, float(self.client_remaining) / float  (self.client_limit))
            text += u'今日API上限額度: {}'.format(self.client_limit)
        except TypeError:
            text = u'資料整理失敗，原始資料: \n'
            text += json.dumps(self._imgur_api.credits)

        return text

class oxford_api_wrapper(object):
    SECTION_SPLITTER = u'.................................................................'
    
    KEY_RESULTS = 'results'
    KEY_LEXICAL_ENTRIES = 'lexicalEntries'
    KEY_LEXICAL_CATEGORY = 'lexicalCategory'
    KEY_DERIVATIVE_OF = 'derivativeOf'
    KEY_ENTRIES = 'entries'
    KEY_SENSES = 'senses'
    KEY_DEFINITIONS = 'definitions'
    KEY_EXAMPLES = 'examples'
    KEY_CROSS_REF = 'crossReferenceMarkers'
    KEY_REGISTERS = 'registers'
    KEY_TEXT = 'text'

    def __init__(self, language):
        """
        Set environment variable "OXFORD_ID", "OXFORD_KEY" as presented api id and api key.
        """
        self._language = language
        self._id = os.getenv('OXFORD_ID', None)
        self._key = os.getenv('OXFORD_KEY', None)
        self._url = 'https://od-api.oxforddictionaries.com:443/api/v1/entries/{}/'.format(self._language)
        self._enabled = False if self._id is None or self._key is None else True

    def get_data_json(self, word):
        if self._enabled:
            url = self._url + word.lower()
            r = requests.get(url, headers = {'app_id': self._id, 'app_key': self._key})
            status_code = r.status_code

            if status_code != requests.codes.ok:
                return status_code
            else:
                return r.json()
        else:
            raise RuntimeError(u'Oxford dictionary not enabled.').encode('utf-8')

    @staticmethod
    def json_to_string(voc, json):
        if type(json) is int:
            code = json

            if code == 404:
                text_list = [error.error.oxford_api.no_result(voc)]
            else:
                text_list = [error.error.oxford_api.err_with_status_code(code)]
        else:
            text_list = []

            lexents = json[oxford_api_wrapper.KEY_RESULTS][0][oxford_api_wrapper.KEY_LEXICAL_ENTRIES]
            for lexent in lexents:
                text_list.append(u'== {} ({}) =='.format(lexent[oxford_api_wrapper.KEY_TEXT], lexent[oxford_api_wrapper.KEY_LEXICAL_CATEGORY]))
                
                if oxford_api_wrapper.KEY_DERIVATIVE_OF in lexent:
                    derivative_arr = lexent[oxford_api_wrapper.KEY_DERIVATIVE_OF]
                    text_list.append(u'Derivative: {}'.format(u', '.join([derivative_data[oxford_api_wrapper.KEY_TEXT] for derivative_data in derivative_arr])))

                lexentarr = lexent[oxford_api_wrapper.KEY_ENTRIES]
                for lexentElem in lexentarr:
                    if oxford_api_wrapper.KEY_SENSES in lexentElem:
                        sens = lexentElem[oxford_api_wrapper.KEY_SENSES]
                        
                        text_list.append(u'Definition:')
                        for index, sen in enumerate(sens, start=1):
                            if oxford_api_wrapper.KEY_DEFINITIONS in sen:
                                proc_definitions = [u'{}. {} {}'.format(index, de, u'({})'.format(u', '.join(sen[oxford_api_wrapper.KEY_REGISTERS])) if oxford_api_wrapper.KEY_REGISTERS in sen else u'') for de in sen[oxford_api_wrapper.KEY_DEFINITIONS]]

                                text_list.extend(proc_definitions)
                                    
                            if oxford_api_wrapper.KEY_CROSS_REF in sen:
                                proc_cross_ref = [u'{}. {} (Cross Reference Marker)'.format(index, crm) for crm in sen[oxford_api_wrapper.KEY_CROSS_REF]]

                                text_list.extend(proc_cross_ref)
                            
                            if oxford_api_wrapper.KEY_EXAMPLES in sen:
                                proc_examples = [u'------{}'.format(ex[oxford_api_wrapper.KEY_TEXT]) for ex in sen[oxford_api_wrapper.KEY_EXAMPLES]]

                                text_list.extend(proc_examples)
                    else:
                        text_list.append(error.error.oxford_api.sense_not_found())

                text_list.append(oxford_api_wrapper.SECTION_SPLITTER)

        text_list.append(u'Powered by Oxford Dictionary.')

        return u'\n'.join(text_list)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

class UserProfileNotFoundError(Exception):
    def __init__(self, *args):
        super(UserProfileNotFoundError, self).__init__(*args)

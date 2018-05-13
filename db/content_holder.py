# -*- coding: utf-8 -*-
import time
import enum
from datetime import datetime, timedelta
import pymongo
from collections import defaultdict

from .base import db_base, dict_like_mapping
import error
from tool import random_gen
import bot
import ext

CONTENT_HOLDER_DB_NAME = 'content'

###############
### WEBPAGE ###
###############

class webpage_content_type(ext.EnumWithName):
    ERROR = 0, '詳細錯誤紀錄'
    QUERY = 1, '資料查詢紀錄(簡略)'
    INFO = 2, '資料查詢紀錄(詳細)'
    TEXT = 3, '文字'
    LATEX = 4, 'LaTeX (數學)'
    STICKER_RANKING = 5, '熱門貼圖排行'

class webpage_content_holder(db_base):
    COLLECTION_NAME = 'webpage'
    DATA_EXPIRE_SECS = 15 * 24 * 60 * 60

    def __init__(self, mongo_client):
        return super(webpage_content_holder, self).__init__(mongo_client, CONTENT_HOLDER_DB_NAME, webpage_content_holder.COLLECTION_NAME, True)
        self.create_index([(webpage_data.TIMESTAMP, pymongo.DESCENDING)], expireAfterSeconds=webpage_content_holder.DATA_EXPIRE_SECS)

    def _get_timestamp_in_datetime(self):
        return datetime.now() + timedelta(hours=8)

    def rec_data(self, content, type, short_description=None):
        """Return sequence id of recorded content document."""
        timestamp = self._get_timestamp_in_datetime()
        return self.insert_one(webpage_data.init_by_field(timestamp, type, content, short_description)).inserted_seq_id

    def get_data(self, id):
        """Return None if nothing found."""
        page_data = self.find_one({ webpage_data.SEQUENCE_ID: id })
        if page_data is not None:
            data = webpage_data(page_data)
            
            if data.content_type == webpage_content_type.LATEX:
                data.content += bot.webpage_manager.LATEX_SPLITTER

            webpage_foot = u'\n\n網頁內容將在{}後清除。'.format((data.timestamp + timedelta(seconds=webpage_content_holder.DATA_EXPIRE_SECS)).strftime('%Y-%m-%d %H:%M:%S'))
            webpage_foot += u'\n\n網頁紀錄時間: {}'.format(data.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
            webpage_foot += u'\n網頁種類: {}'.format(unicode(data.content_type))
                
            if data.content_type == webpage_content_type.STICKER_RANKING:
                data.content.append(webpage_foot)
            else:
                data.content += webpage_foot

            return data
        else:
            return None

    def get_error_page_list(self, limit=None):
        """Return list of webpage_data of error message webpage"""
        find_cursor = self.find({ webpage_data.TYPE: webpage_content_type.ERROR }, sort=[(webpage_data.SEQUENCE_ID, pymongo.DESCENDING)])
        find_cursor = self.cursor_limit(find_cursor, limit)
        data_list = list(find_cursor)
        return [webpage_data(page) for page in data_list]

class webpage_data(dict_like_mapping):
    """
    {
        seq_id: INTEGER,
        timestamp: DATETIME,
        type: WEBPAGE_CONTENT_TYPE,
        content: STRING
    }
    """
    SEQUENCE_ID = db_base.SEQUENCE
    TIMESTAMP = 'time'
    TYPE = 'type'
    SHORT_DESCRIPTION = 'desc'
    CONTENT = 'cont'

    @staticmethod
    def init_by_field(time, type, content, short_description):
        init_dict = {
            webpage_data.TIMESTAMP: time,
            webpage_data.TYPE: type,
            webpage_data.CONTENT: content,
            webpage_data.SHORT_DESCRIPTION: short_description
        }
        return webpage_data(init_dict)

    @staticmethod
    def no_content_template():
        init_dict = {
            webpage_data.TIMESTAMP: time.time(),
            webpage_data.TYPE: webpage_content_type.ERROR,
            webpage_data.CONTENT: error.error.webpage.no_content(),
            webpage_data.SHORT_DESCRIPTION: error.error.webpage.no_content()
        }
        return webpage_data(init_dict)

    def __init__(self, org_dict):
        if org_dict is None:
            raise ValueError(u'Dict is None.')

        if not all(k in org_dict for k in (webpage_data.CONTENT, webpage_data.TIMESTAMP, webpage_data.TYPE)):
            raise ValueError(u'Incomplete webpage data keys. {}'.format(org_dict))

        if webpage_data.SHORT_DESCRIPTION not in org_dict:
            org_dict[webpage_data.SHORT_DESCRIPTION] = None

        return super(webpage_data, self).__init__(org_dict)

    @property
    def seq_id(self):
        return self[webpage_data.SEQUENCE_ID]

    @property
    def timestamp(self):
        return self[webpage_data.TIMESTAMP]

    @property
    def content_type(self):
        return webpage_content_type(self[webpage_data.TYPE])

    @property
    def content(self):
        return self[webpage_data.CONTENT]

    @content.setter
    def content(self, value):
        self[webpage_data.CONTENT] = value

    @property
    def short_description(self):
        return self[webpage_data.SHORT_DESCRIPTION]

#################################
### GAME - ROCK-PAPER-SCISSOR ###
#################################

class rps_holder(db_base):
    COLLECTION_NAME = 'rps'

    def __init__(self, mongo_client):
        super(rps_holder, self).__init__(mongo_client, CONTENT_HOLDER_DB_NAME, rps_holder.COLLECTION_NAME, False, [rps_online.CHAT_INSTANCE_ID])

        rps_list = list(self.find())
        self._cache_local = { rps_data[rps_online.CHAT_INSTANCE_ID]: rps_local() for rps_data in rps_list }
        self._cache_repr = { rps_data[rps_online.CHAT_INSTANCE_ID]: battle_item_repr_manager(rps_data[rps_online.REPRESENTATIVES]) for rps_data in rps_list }
        self._cache_enabled = { rps_data[rps_online.CHAT_INSTANCE_ID]: rps_data[rps_online.PROPERTIES][rps_online.ENABLED] for rps_data in rps_list }
        self._cache_players = { rps_data[rps_online.CHAT_INSTANCE_ID]: set([key for key in rps_data[rps_online.PLAYERS].iterkeys()]) for rps_data in rps_list }

    def create_game(self, cid, creator_id, creator_name, rock_stk_id, paper_stk_id, scissor_stk_id):
        """Return result string."""
        try:
            new_game_online = rps_online.init_by_field(cid, creator_id, creator_name, rock_stk_id, paper_stk_id, scissor_stk_id)

            self.insert_one(new_game_online)
            self._create_cache_repr(cid, new_game_online.representatives)
            self._set_cache_local(cid, rps_local())
            self._set_cache_enabled(cid, new_game_online.enabled)
            self._set_cache_player(cid, creator_id)
            if new_game_online.is_vs_bot:
                self._set_cache_player(cid, battle_player.BOT_UID)
            return rps_message.message.successfully_created(rock_stk_id, paper_stk_id, scissor_stk_id)
        except pymongo.errors.DuplicateKeyError:
            return rps_message.error.game_instance_already_exist()

    def play(self, cid, uid, content, is_sticker):
        """
        Return result string.
        If battle_item is undetermined, return None.
        If game is not exist, return rps_message.error.game_instance_not_exist().
        If game is disabled, return rps_message.error.game_is_not_enabled().
        If count of player of the game is insufficient, return rps_message.error.insufficient_player_count().
        If player data not found, return rps_message.error.player_data_not_found().
        """

        if not self._check_instance_exist(cid):
            return rps_message.error.game_instance_not_exist()

        if not self._get_cache_enabled(cid):
            return rps_message.error.game_is_not_enabled()

        player_item = self._get_cache_repr(cid, content, is_sticker)
        if player_item is None:
            return rps_message.error.unknown_battle_item()

        if not self._has_cache_player(cid, uid):
            return rps_message.error.player_data_not_found()

        if self._get_cache_player_length(cid) < 2:
            return rps_message.error.insufficient_player_count()

        rps_at_local = self._get_cache_local(cid)
        is_vs_bot = bot.line_api_wrapper.is_valid_user_id(cid)
        play_result = rps_at_local.play(uid, player_item, is_vs_bot)

        self._set_cache_local(cid, rps_at_local)

        if play_result == battle_result.UNDEFINED:
            return rps_message.result.waiting()
        elif play_result == battle_result.DUPLICATED:
            return rps_message.error.duplicate_play()
        else:
            player_datas = self._get_player_data(cid, uid, rps_at_local, is_vs_bot)
            if player_datas is None:
                return rps_message.error.player_data_not_found()

            player_data1, player_data2 = player_datas
            player_data1 = battle_player(player_data1)
            player_data2 = battle_player(player_data2)

            update_dict = self._generate_update_dict_by_result(play_result, player_data1, player_data2, rps_at_local)

            self.find_one_and_update({ rps_online.CHAT_INSTANCE_ID: cid }, update_dict, None, None, False, pymongo.ReturnDocument.AFTER)

            return rps_message.result.result_report(player_data1.name, player_data2.name, play_result, rps_at_local.gap_time) + u'\n' + rps_message.result.statistics([player_data1, player_data2], False) 

    def register_player(self, cid, uid, uid_name):
        """
        Return result string.
        If game is not exist, return rps_message.error.game_instance_not_exist().
        If game is disabled, return rps_message.error.game_is_not_enabled().
        If player is already registered, return rps_message.error.player_already_exist().
        """
        if not self._check_instance_exist(cid):
            return rps_message.error.game_instance_not_exist()

        if not self._get_cache_enabled(cid):
            return rps_message.error.game_is_not_enabled()

        if self._has_cache_player(cid, uid):
            return rps_message.error.player_already_exist(uid)

        self._set_cache_player(cid, uid)
        self.find_one_and_update({ rps_online.CHAT_INSTANCE_ID: cid }, { '$set': { rps_online.PLAYERS + '.' + uid: battle_player.init_by_field(uid, uid_name) } }, None, None, False, pymongo.ReturnDocument.AFTER)

        return rps_message.message.player_data_registered(uid, uid_name)

    def register_battleitem(self, cid, content, is_sticker, item_enum):
        """
        Return result string.
        If game is not exist, return rps_message.error.game_instance_not_exist().
        """
        if not self._check_instance_exist(cid):
            return rps_message.error.game_instance_not_exist()

        if self._get_cache_repr(cid, content, is_sticker) is not None:
            return rps_message.error.battle_item_alreay_exist()

        new_repr = battle_item_representative.init_by_field(item_enum, is_sticker, content)

        self._set_cache_repr(cid, new_repr)
        self.find_one_and_update({ rps_online.CHAT_INSTANCE_ID: cid }, 
                                 { '$set': { rps_online.REPRESENTATIVES + '.' + battle_item_representative.generate_key(is_sticker, content): new_repr } }, None, None, False, pymongo.ReturnDocument.AFTER)

        return rps_message.message.battle_item_registered(new_repr)

    def reset_statistics(self, cid):
        """
        Return result string.
        If game is not exist, return rps_message.error.game_instance_not_exist().
        """
        if not self._check_instance_exist(cid):
            return rps_message.error.game_instance_not_exist()

        rps_at_online = rps_online(self.find_one({ rps_online.CHAT_INSTANCE_ID: cid }))
        rps_at_online.reset_statistics()
        self.find_one_and_replace({ rps_online.CHAT_INSTANCE_ID: cid }, rps_at_online)

        return rps_message.message.statisics_reset_complete()

    def set_enabled(self, cid, enabled):
        """
        Return result string.
        If game is not exist, return rps_message.error.game_instance_not_exist().
        """
        if not self._check_instance_exist(cid):
            return rps_message.error.game_instance_not_exist()

        self._set_cache_enabled(cid, enabled)
        self.update_one({ rps_online.CHAT_INSTANCE_ID: cid }, { '$set': { rps_online.PROPERTIES + '.' + rps_online.ENABLED: enabled } })

        return rps_message.message.game_enabled_changed(enabled)

    def delete_game(self, cid):
        """
        Return result string.
        If game is not exist, return rps_message.error.game_instance_not_exist().
        """
        if not self._check_instance_exist(cid):
            return rps_message.error.game_instance_not_exist()

        self._clear_cache_repr(cid)
        self._del_cache_enabled(cid)
        self._del_cache_local(cid)
        self._clear_cache_player(cid)

        self.delete_one({ rps_online.CHAT_INSTANCE_ID: cid })

        return rps_message.message.game_deleted()

    def game_statistics(self, cid):
        """
        Return result string.
        If game is not exist, return rps_message.error.game_instance_not_exist().
        """
        if not self._check_instance_exist(cid):
            return rps_message.error.game_instance_not_exist()

        rps_at_online = rps_online(self.find_one({ rps_online.CHAT_INSTANCE_ID: cid }))

        text_to_join = [u'【遊戲{}中】\n'.format(rps_message.message.game_enabled(rps_at_online.enabled)),
                        rps_at_online.players_data_str(True),
                        rps_message.message.item_representatives_str(rps_at_online.representatives.itervalues())]

        return u'\n'.join(text_to_join)

    def _get_player_data(self, cid, uid, rps_at_local, is_vs_bot):
        aggr_data = self.aggregate([
            { '$match': { 
                rps_online.CHAT_INSTANCE_ID: cid,
                '$or': [
                    { rps_online.PLAYERS + '.' + uid + '.' + battle_player.USER_ID: uid }, 
                    { rps_online.PLAYERS + '.' + rps_at_local.temp_uid_1 + '.' + battle_player.USER_ID: rps_at_local.temp_uid_1 }
                ]
            } },
            { '$replaceRoot': { 
                'newRoot': '$' + rps_online.PLAYERS
            } }
        ]).next()

        if len(aggr_data) >= 2 and all(k in aggr_data for k in (rps_at_local.temp_uid_1, rps_at_local.temp_uid_2)):
            return aggr_data[rps_at_local.temp_uid_1], aggr_data[rps_at_local.temp_uid_2]
        else:
            return None

    def _generate_update_dict_by_result(self, result_enum, player1_data, player2_data, rps_at_local):
        player1_data.rec_last_item(rps_at_local.temp_item_1)
        player2_data.rec_last_item(rps_at_local.temp_item_2)
        if result_enum == battle_result.PLAYER1_WIN:
            player1_data.win()
            player2_data.lose()
        elif result_enum == battle_result.PLAYER2_WIN:
            player1_data.lose()
            player2_data.win()
        elif result_enum == battle_result.TIED:
            player1_data.tied()
            player2_data.tied()
        else:
            raise ValueError(u'Unhandled battle enum. {}'.format(result_enum))

        return { '$set': { rps_online.PLAYERS + '.' + player1_data.user_id: player1_data, 
                           rps_online.PLAYERS + '.' + player2_data.user_id: player2_data } }

    def _check_instance_exist(self, cid):
        return cid in self._cache_local

    def _set_cache_local(self, cid, rps_local):
        self._cache_local[cid] = rps_local

    def _del_cache_local(self, cid):
        del self._cache_local[cid]

    def _get_cache_local(self, cid):
        """Return None if nothing found"""
        return self._cache_local.get(cid, None)

    def _create_cache_repr(self, cid, repr_dict):
        """Provide content only to delete representative."""
        self._cache_repr[cid] = battle_item_repr_manager(repr_dict)

    def _set_cache_repr(self, cid, repr_obj=None):
        """Set repr_obj to None to delete representative."""
        self._cache_repr[cid].set_battle_item(repr_obj)

    def _clear_cache_repr(self, cid):
        del self._cache_repr[cid]

    def _get_cache_repr(self, cid, content, is_sticker):
        """Return None if nothing match."""
        return self._cache_repr[cid].get_battle_item(content, is_sticker)

    def _set_cache_enabled(self, cid, enabled):
        self._cache_enabled[cid] = enabled

    def _del_cache_enabled(self, cid):
        del self._cache_enabled[cid]

    def _get_cache_enabled(self, cid):
        return self._cache_enabled.get(cid, False)

    def _set_cache_player(self, cid, uid):
        if cid in self._cache_players:
            self._cache_players[cid].add(uid)
        else:
            self._cache_players[cid] = set([uid])

    def _get_cache_player_length(self, cid):
        if cid in self._cache_players:
            return len(self._cache_players[cid])
        else:
            return 0

    def _has_cache_player(self, cid, uid):
        if cid in self._cache_players:
            return uid in self._cache_players[cid]
        else:
            return False

    def _del_cache_player(self, cid, uid):
        if cid in self._cache_players:
            self._cache_players[cid].remove(uid)

    def _clear_cache_player(self, cid):
        del self._cache_players[cid]

class battle_result(ext.IntEnum):
    DUPLICATED = -2
    UNDEFINED = -1
    TIED = 0
    PLAYER1_WIN = 1
    PLAYER2_WIN = 2

    @staticmethod
    def calculate_result(player1_item, player2_item):
        """Set either player1_item or player2_item to None to return UNDEFINED."""
        if player1_item is None or player2_item is None:
            return battle_result.UNDEFINED

        return battle_result((player1_item - player2_item) % 3)

class battle_item(ext.EnumWithName):
    UNDEFINED = -1, '無'
    ROCK = 0, '石頭'
    PAPER = 1, '布'
    SCISSOR = 2, '剪刀'

class battle_item_representative(dict_like_mapping):
    """
    {
        battle_item: BATTLE_ITEM,
        is_sticker: BOOLEAN,
        content: STRING
    }
    """
    BATTLE_ITEM = 'bi'
    IS_STICKER = 'stk'
    CONTENT = 'cont'

    @staticmethod
    def init_by_field(battle_item_enum, is_sticker, content):
        init_dict = {
            battle_item_representative.BATTLE_ITEM: battle_item_enum,
            battle_item_representative.IS_STICKER: is_sticker,
            battle_item_representative.CONTENT: content
        }
        return battle_item_representative(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (battle_item_representative.BATTLE_ITEM, battle_item_representative.IS_STICKER, battle_item_representative.CONTENT)):
            raise ValueError(u'Incomplete battle representative. {}'.format(org_dict))

        super(battle_item_representative, self).__init__(org_dict)

    def item_str(self):
        content = self[battle_item_representative.CONTENT]
        if self[battle_item_representative.IS_STICKER]:
            content = u'(貼圖ID {})'.format(content)

        return u'{}，代表物件 - {}'.format(content, unicode(battle_item(self[battle_item_representative.BATTLE_ITEM])))

    @property
    def is_sticker(self):
        return self[battle_item_representative.IS_STICKER]

    @property
    def battle_item(self):
        return self[battle_item_representative.BATTLE_ITEM]

    @property
    def content(self):
        return self[battle_item_representative.CONTENT]

    @staticmethod
    def generate_key(is_sticker, content):
        return '{}_{}'.format(is_sticker, content.encode('utf-8'))

class battle_item_repr_manager(object):
    def __init__(self, repr_dict):
        self._repr_dict = repr_dict

    def get_battle_item(self, content, is_sticker):
        """Return None if nothing match."""
        key_str = battle_item_representative.generate_key(is_sticker, content)
        item_repr = self._repr_dict.get(key_str, None)
        if item_repr is None:
            return None
        else:
            return battle_item(item_repr[battle_item_representative.BATTLE_ITEM])

    def set_battle_item(self, repr_obj):
        """Set battle_item_enum to None to delete representative."""
        key_str = battle_item_representative.generate_key(repr_obj.is_sticker, repr_obj.content)

        if repr_obj is None:
            del self._repr_dict[key_str]
        else:
            self._repr_dict[key_str] = repr_obj

class battle_player(dict_like_mapping):
    """
    {
        NAME: STRING,
        USER_ID: STRING,
        RECORD: {
            WIN: INTEGER,
            LOSE: INTEGER,
            TIED: INTEGER,
        },
        STATISTICS: {
            MAX_CONTINUOUS_WIN: INTEGER,
            MAX_CONTINUOUS_LOSE: INTEGER,
            CONTINUOUS_COUNT: INTEGER,
            IS_CONTINUNOUS_WIN: BOOLEAN
        }
    }
    """
    BOT_UID = 'U--------------------------------'

    NAME = 'nm'
    USER_ID = 'uid'

    RECORD = 'rec'
    WIN = 'W'
    LOSE = 'L'
    TIED = 'T'

    STATISTICS = 'stats'
    MAX_CONTINUOUS_WIN = 'mx_cw'
    MAX_CONTINUOUS_LOSE = 'mx_cl'
    CONTINUOUS_COUNT = 'c_ct'
    IS_CONTINUNOUS_WIN = 'c_w'
    LAST_10_RESULT = 'l10r'
    LAST_10_ITEM = 'l10i'

    @staticmethod
    def init_by_field(user_id, name):
        init_dict = {
            battle_player.USER_ID: user_id,
            battle_player.NAME: name
        }

        return battle_player(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (battle_player.NAME, battle_player.USER_ID)):
            raise ValueError(u'Data incomplete. {}'.format(org_dict))

        if battle_player.RECORD not in org_dict:
            org_dict[battle_player.RECORD] = {
                battle_player.WIN: 0,
                battle_player.LOSE: 0,
                battle_player.TIED: 0
            }

        if battle_player.STATISTICS not in org_dict:
            org_dict[battle_player.STATISTICS] = {
                battle_player.MAX_CONTINUOUS_WIN: 0,
                battle_player.MAX_CONTINUOUS_LOSE: 0,
                battle_player.CONTINUOUS_COUNT: 0,
                battle_player.IS_CONTINUNOUS_WIN: False,
                battle_player.LAST_10_RESULT: '----------',
                battle_player.LAST_10_ITEM: [battle_item.UNDEFINED for i in range(10)]
            }

        super(battle_player, self).__init__(org_dict)

    @property
    def user_id(self):
        return self[battle_player.USER_ID]

    @property
    def name(self):
        return self[battle_player.NAME]

    def statistic_string(self, detailed=False):
        w = self[battle_player.RECORD][battle_player.WIN]
        l = self[battle_player.RECORD][battle_player.LOSE]
        t = self[battle_player.RECORD][battle_player.TIED]

        cont_w = self[battle_player.STATISTICS][battle_player.IS_CONTINUNOUS_WIN]
        cont_count = self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT]
        cont_mw = self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_WIN]
        cont_ml = self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_LOSE]

        try:
            wr = w / float(w + l)
        except ZeroDivisionError:
            wr = 0.0

        result = u'{}\n{}戰 {}勝{}敗{}和 勝率{:.3f} {}連{}中 最高{}連勝、{}連敗'.format(self[battle_player.NAME], w + l + t, w, l, t, wr, cont_count, u'勝' if cont_w else u'敗', cont_mw, cont_ml)

        if detailed:
            l10r = self[battle_player.STATISTICS][battle_player.LAST_10_RESULT]
            l10i = u''.join([unicode(battle_item(item))[0] for item in self[battle_player.STATISTICS][battle_player.LAST_10_ITEM]])

            result += u'\n近10場戰績: {}\n近10場出拳: {}'.format(l10r, l10i)

        return result

    def win(self):
        self[battle_player.RECORD][battle_player.WIN] += 1
        self[battle_player.STATISTICS][battle_player.LAST_10_RESULT] = self[battle_player.STATISTICS][battle_player.LAST_10_RESULT][1:] + battle_player.WIN

        if self[battle_player.STATISTICS][battle_player.IS_CONTINUNOUS_WIN]:
            self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT] += 1
        else:
            self[battle_player.STATISTICS][battle_player.IS_CONTINUNOUS_WIN] = True
            self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT] = 1

        if self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT] > self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_WIN]:
            self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_WIN] = self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT]

    def tied(self):
        self[battle_player.RECORD][battle_player.TIED] += 1
        self[battle_player.STATISTICS][battle_player.LAST_10_RESULT] = self[battle_player.STATISTICS][battle_player.LAST_10_RESULT][1:] + battle_player.TIED

    def lose(self):
        self[battle_player.RECORD][battle_player.LOSE] += 1
        self[battle_player.STATISTICS][battle_player.LAST_10_RESULT] = self[battle_player.STATISTICS][battle_player.LAST_10_RESULT][1:] + battle_player.LOSE

        if not self[battle_player.STATISTICS][battle_player.IS_CONTINUNOUS_WIN]:
            self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT] += 1
        else:
            self[battle_player.STATISTICS][battle_player.IS_CONTINUNOUS_WIN] = False
            self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT] = 1

        if self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT] > self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_LOSE]:
            self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_LOSE] = self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT]

    def rec_last_item(self, item):
        self[battle_player.STATISTICS][battle_player.LAST_10_ITEM] = self[battle_player.STATISTICS][battle_player.LAST_10_ITEM][1:] + [item]

    def reset(self):
        self[battle_player.RECORD][battle_player.WIN] = 0
        self[battle_player.RECORD][battle_player.LOSE] = 0
        self[battle_player.RECORD][battle_player.TIED] = 0
        self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_WIN] = 0
        self[battle_player.STATISTICS][battle_player.MAX_CONTINUOUS_LOSE] = 0
        self[battle_player.STATISTICS][battle_player.CONTINUOUS_COUNT] = 0
        self[battle_player.STATISTICS][battle_player.IS_CONTINUNOUS_WIN] = 0

class rps_online(dict_like_mapping):
    """
    {
        chat_instance_id: STRING,
        players: 
            { user_id: BATTLE_PLAYER, 
              user_id: BATTLE_PLAYER, 
              user_id: BATTLE_PLAYER,
              ... },
        representatives: 
            { [is_sticker]_[content]: BATTLE_ITEM_REPRESENTATIVES, 
              [is_sticker]_[content]: BATTLE_ITEM_REPRESENTATIVES, 
              [is_sticker]_[content]: BATTLE_ITEM_REPRESENTATIVES,
              ... },
        properties: {
            vs_bot: BOOLEAN,
            enabled: BOOLEAN
        }
    }
    """
    CHAT_INSTANCE_ID = 'cid'
    PLAYERS = 'plyrs'
    REPRESENTATIVES = 'repr'

    PROPERTIES = 'prop'
    VS_BOT = 'vs_bot'
    ENABLED = 'en'

    @staticmethod
    def init_by_field(cid, creator_id, creator_name, rock_stk_id, paper_repr_id, scissor_repr_id):
        vs_bot = bot.line_api_wrapper.is_valid_user_id(cid)

        init_dict = {
            rps_online.CHAT_INSTANCE_ID: cid,
            rps_online.PLAYERS: { creator_id: battle_player.init_by_field(creator_id, creator_name) },
            rps_online.REPRESENTATIVES: { battle_item_representative.generate_key(True, rock_stk_id) : battle_item_representative.init_by_field(battle_item.ROCK, True, rock_stk_id),
                                          battle_item_representative.generate_key(True, paper_repr_id): battle_item_representative.init_by_field(battle_item.PAPER, True, paper_repr_id),
                                          battle_item_representative.generate_key(True, scissor_repr_id): battle_item_representative.init_by_field(battle_item.SCISSOR, True, scissor_repr_id) },
            rps_online.PROPERTIES: {
                rps_online.VS_BOT: vs_bot,
                rps_online.ENABLED: True
            }
        }

        if vs_bot:
            init_dict[rps_online.PLAYERS][battle_player.BOT_UID] = battle_player.init_by_field(battle_player.BOT_UID, '(電腦)')

        return rps_online(init_dict)

    def __init__(self, org_dict):
        if not all(k in org_dict for k in (rps_online.CHAT_INSTANCE_ID, rps_online.PLAYERS, rps_online.REPRESENTATIVES, rps_online.PROPERTIES)):
            raise ValueError(u'Incomplete data. {}'.format(org_dict))

        return super(rps_online, self).__init__(org_dict)

    def players_data_str(self, detailed):
        return rps_message.result.statistics(self[rps_online.PLAYERS].values(), detailed)

    def reset_statistics(self):
        self[rps_online.PLAYERS] = { uid: battle_player.init_by_field(data[battle_player.USER_ID], data[battle_player.NAME]) for uid, data in self[rps_online.PLAYERS].iteritems() }

    @property
    def representatives(self):
        return self[rps_online.REPRESENTATIVES]

    @property
    def enabled(self):
        return self[rps_online.PROPERTIES][rps_online.ENABLED]

    @property
    def is_vs_bot(self):
        return self[rps_online.PROPERTIES][rps_online.VS_BOT]

class rps_local(object):
    TIME_NOT_STARTED = -1.0

    def __init__(self):
        self._result = battle_result.UNDEFINED
        self._result_generated = False
        self._waiting = False

        self._start_time = rps_local.TIME_NOT_STARTED
        self._gap_time = rps_local.TIME_NOT_STARTED

        self._temp_item1 = None
        self._temp_uid1 = None
        self._temp_item2 = None
        self._temp_uid2 = None

    def play(self, uid, player_item, is_vs_bot=False):

        if is_vs_bot:
            self._start_time = time.time()

            self._temp_uid1 = uid
            self._temp_uid2 = battle_player.BOT_UID

            self._temp_item1 = player_item
            self._temp_item2 = random_gen.random_drawer.draw_from_list(list([battle_item.PAPER, battle_item.ROCK, battle_item.SCISSOR]))

            self._gap_time = time.time() - self._start_time
            self._result_generated = True
            self._waiting = False
        else:
            if self._waiting:
                if self._temp_uid1 is not None and self._temp_uid1 == uid:
                    return battle_result.DUPLICATED

                self._gap_time = time.time() - self._start_time
                self._start_time = rps_local.TIME_NOT_STARTED

                self._temp_item2 = player_item
                self._temp_uid2 = uid

                self._result_generated = True
                self._waiting = False
            else:
                self._gap_time = rps_local.TIME_NOT_STARTED
                self._start_time = time.time()

                self._temp_item1 = player_item
                self._temp_uid1 = uid
                self._temp_item2 = None

                self._result_generated = False
                self._waiting = True

        self._result = battle_result.calculate_result(self._temp_item1, self._temp_item2)

        return self._result

    @property
    def temp_uid_1(self):
        return self._temp_uid1

    @property
    def temp_item_1(self):
        return self._temp_item1

    @property
    def temp_uid_2(self):
        return self._temp_uid2

    @property
    def temp_item_2(self):
        return self._temp_item2

    @property
    def gap_time(self):
        return self._gap_time

class rps_message(object):
    class error(object):
        @staticmethod
        def duplicate_play():
            return u'同一玩家不可重複出拳。'

        @staticmethod
        def player_data_not_found():
            return u'找不到玩家資料。'

        @staticmethod
        def game_instance_not_exist():
            return u'遊戲資料不存在，請建立遊戲後重試。'

        @staticmethod
        def game_is_not_enabled():
            return u'遊戲已暫停。'

        @staticmethod
        def insufficient_player_count():
            return u'玩家人數不足，需要兩名玩家或以上。'

        @staticmethod
        def player_already_exist(uid):
            return u'玩家資料已存在。(UID: {})'.format(uid)

        @staticmethod
        def battle_item_alreay_exist():
            return u'拳代表已存在。'

        @staticmethod
        def game_instance_already_exist():
            return u'遊戲資料已存在。'

        @staticmethod
        def unknown_battle_item():
            return u'無法判斷拳代表物件的種類。'

        @staticmethod
        def unknown_content_type():
            return u'無法判斷內容種類。'

    class message(object):
        @staticmethod
        def successfully_created(rock, paper, scissor):
            return u'遊戲已建立。\n剪刀代表貼圖ID: {}\n石頭代表貼圖ID: {}\n布代表貼圖ID: {}'.format(scissor, rock, paper)

        @staticmethod
        def player_data_registered(uid, uid_name):
            return u'玩家 {} 資料註冊成功。(UID: {})'.format(uid_name, uid)

        @staticmethod
        def battle_item_registered(repr):
            return u'已新增【{}】代表物件。\n{}'.format(unicode(repr.battle_item), repr.item_str())

        @staticmethod
        def statisics_reset_complete():
            return u'遊戲玩家統計資料已重設。'

        @staticmethod
        def game_enabled(enabled):
            enabled_dict = { True: u'啟用', False: u'停用' }
            return enabled_dict[enabled]

        @staticmethod
        def game_enabled_changed(enabled):
            return u'遊戲狀態已更改為{}。'.format(rps_message.message.game_enabled(enabled))

        @staticmethod
        def game_deleted():
            return u'遊戲資料已刪除。'

        @staticmethod
        def item_representatives_str(battle_item_repr_list):
            text_to_join = [u'【戰鬥代表物件清單】']
            text_to_join.extend([battle_item_representative(item_repr).item_str() for item_repr in battle_item_repr_list])

            return u'\n'.join(text_to_join)

    class result(object):
        @staticmethod
        def waiting():
            return u'等待下一位玩家出拳中...'

        @staticmethod
        def result_report(player1_name, player2_name, result_enum, gap_time):
            if result_enum == battle_result.PLAYER1_WIN:
                result = u'【{}】勝利'.format(player1_name)
            elif result_enum == battle_result.PLAYER2_WIN:
                result = u'【{}】勝利'.format(player2_name)
            elif result_enum == battle_result.TIED:
                result = u'平手'
            elif result_enum == battle_result.UNDEFINED:
                return u'等待下一位玩家出拳中...'
            else:
                raise ValueError(u'Unhandled result_enum. {}'.format(result_enum))

            return u'{}\n\n兩拳相隔時間(含程式處理) {:.3f} 秒'.format(result, gap_time)

        @staticmethod
        def statistics(player_data_list, detailed=False):
            def sort_func(data):
                w = data[battle_player.RECORD][battle_player.WIN]
                l = data[battle_player.RECORD][battle_player.LOSE]
                t = data[battle_player.RECORD][battle_player.TIED]

                try:
                    wr = w / float(w + l)
                except ZeroDivisionError:
                    wr = 0.0

                return (w + l + t) + wr

            text_to_join = [u'【玩家資料】']
            text_to_join.extend([battle_player(data).statistic_string(detailed) for data in sorted(player_data_list, key=sort_func, reverse=True)])

            return u'\n'.join(text_to_join)
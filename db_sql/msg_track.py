# -*- coding: utf-8 -*-

import os, sys
from collections import defaultdict
from error import error
from enum import Enum

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError
from db import group_ban, gb_col
import hashlib

from .db_base import db_base_obj

class message_tracker(db_base_obj):

    def __init__(self, db_query_mgr):
        super(message_tracker, self).__init__(db_query_mgr)
        self.channel_id_length = 33



    @property
    def table_structure(self):
        cmd = u'CREATE TABLE msg_track( \
                cid VARCHAR(33) PRIMARY KEY, \
                text_msg INTEGER NOT NULL DEFAULT 0, \
                text_msg_trig INTEGER NOT NULL DEFAULT 0, \
                stk_msg INTEGER NOT NULL DEFAULT 0, \
                stk_msg_trig INTEGER NOT NULL DEFAULT 0, \
                text_rep INTEGER NOT NULL DEFAULT 0, \
                stk_rep INTEGER NOT NULL DEFAULT 0, \
                last_msg_recv TIMESTAMP NOT NULL DEFAULT NOW() AT TIME ZONE \'CCT\' \
                pic_msg INTEGER NOT NULL DEFAULT 0);'
        return cmd

    def log_message_activity(self, cid, type_of_event):
        if len(cid) != self.channel_id_length:
            raise ValueError(error.main.incorrect_thing_with_correct_format(u'頻道ID', u'33字元長度', cid));
        else:
            update_last_message_recv = True
            if type_of_event == msg_event_type.send_stk or type_of_event == msg_event_type.send_txt:
                update_last_message_recv = False
            
            cmd = u'SELECT * FROM msg_track WHERE cid = %(cid)s'
            cmd_dict = {'cid': cid}
            result = self.sql_cmd(cmd, cmd_dict)
            
            if result is None:
                self.new_data(cid)
            
            column_to_add = msg_track_col(int(type_of_event)).column_name

            cmd = u'UPDATE msg_track SET {col} = {col} + 1{recv_time} WHERE cid = %(cid)s'.format(
                recv_time=u', last_msg_recv = NOW() AT TIME ZONE \'CCT\'' if update_last_message_recv else u'',
                col=column_to_add)
            self.sql_cmd(cmd, cmd_dict)
        
    def new_data(self, cid):
        if len(cid) != self.channel_id_length:
            raise ValueError();
        else:
            try:
                cmd = u'INSERT INTO msg_track (cid) VALUES (%(cid)s)'
                cmd_dict = {'cid': cid}
                self.sql_cmd(cmd, cmd_dict)
                return True
            except IntegrityError as e:
                return False

    def get_data(self, cid):
        """return group entry"""
        if len(cid) != self.channel_id_length:
            raise ValueError();
        else:
            cmd = u'SELECT * FROM msg_track WHERE cid = %(cid)s'
            cmd_dict = {'cid': cid}
            result = self.sql_cmd(cmd, cmd_dict)
            return None if result is None else result[0]

    def count_sum(self):
        results = defaultdict(int)

        cmd = u'SELECT MAX(last_msg_recv), SUM(text_msg), SUM(text_msg_trig), SUM(stk_msg), SUM(stk_msg_trig), SUM(text_rep), SUM(stk_rep), MAX(last_msg_recv), SUM(pic_msg) FROM msg_track'
        sql_result = self.sql_cmd_only(cmd)
        if sql_result is None:
            return None
        sql_result = sql_result[0]
        results[msg_event_type.recv_txt] = sql_result[int(msg_track_col.text_msg)]
        results[msg_event_type.recv_txt_repl] = sql_result[int(msg_track_col.text_msg_trig)]
        results[msg_event_type.recv_stk] = sql_result[int(msg_track_col.stk_msg)]
        results[msg_event_type.recv_stk_repl] = sql_result[int(msg_track_col.stk_msg_trig)]
        results[msg_event_type.recv_pic] = sql_result[int(msg_track_col.pic_msg)]
        results[msg_event_type.send_txt] = sql_result[int(msg_track_col.text_rep)]
        results[msg_event_type.send_stk] = sql_result[int(msg_track_col.stk_rep)]
        return results

    def order_by_recorded_msg_count(self, limit=1000):
        cmd = u'SELECT *, RANK() OVER (ORDER BY SUM(text_msg) + SUM(text_msg_trig) + SUM(stk_msg) + \
                                                SUM(stk_msg_trig) + SUM(pic_msg) DESC) AS total_msg FROM msg_track GROUP BY cid ORDER BY total_msg ASC LIMIT %(limit)s;'
        cmd_dict = {'limit': limit}
        
        result = self.sql_cmd(cmd, cmd_dict)
        return result




    @staticmethod
    def entry_detail(data, group_ban=None):
        if data is not None:
            gid = data[int(msg_track_col.cid)]

            if group_ban is not None:
                if gid.startswith('U'):
                    activation_status = u'私訊頻道'
                else:
                    group_data = group_ban.get_group_by_id(gid)
                    if group_data is not None:
                        activation_status = u'停用回覆' if group_data[int(gb_col.silence)] else u'啟用回覆'
                    else:
                        activation_status = u'啟用回覆'
            else:
                activation_status = u'啟用回覆'

            text = u'群組/房間ID: {} 【{}】'.format(gid, activation_status)
            text += u'\n收到(無對應回覆組): {}則文字訊息 | {}則貼圖訊息 | {}則圖片訊息'.format(data[int(msg_track_col.text_msg)], 
                                                                                        data[int(msg_track_col.stk_msg)], 
                                                                                        data[int(msg_track_col.pic_msg)])
            text += u'\n收到(有對應回覆組): {}則文字訊息 | {}則貼圖訊息'.format(data[int(msg_track_col.text_msg_trig)], 
                                                                             data[int(msg_track_col.stk_msg_trig)])
            text += u'\n回覆: {}則文字訊息 | {}則貼圖訊息'.format(data[int(msg_track_col.text_rep)], 
                                                                data[int(msg_track_col.stk_rep)])
        else:
            text = u'查無群組資料。'

        return text

    @staticmethod
    def entry_detail_list(data_list, limit=10, group_ban=None):
        """return two object to access by [\'limited\'] and [\'full\']."""
        ret = {'limited': u'', 'full': u''}
        count = 0 if data_list is None else len(data_list)

        if data_list is None:
            ret['limited'] = error.main.no_result()
        else:
            ret['limited'] = u'\n\n'.join([message_tracker.entry_detail(data, group_ban) for data in data_list[0:limit]])
            if count - limit > 0:
                ret['limited'] += u'\n\n...還有{}筆資料'.format(count - limit)

            ret['full'] = u'\n\n'.join([message_tracker.entry_detail(data, group_ban) for data in data_list])
        return ret


class msg_track_col(Enum):
    cid = 0, 'cid'
    text_msg = 1, 'text_msg'
    text_msg_trig = 2, 'text_msg_trig'
    stk_msg = 3, 'stk_msg'
    stk_msg_trig = 4, 'stk_msg_trig'
    text_rep = 5, 'text_rep'
    stk_rep = 6, 'stk_rep'
    last_msg_recv = 7, 'last_msg_recv'
    pic_msg = 8, 'pic_msg'

    def __new__(cls, value, col_name):
        member = object.__new__(cls)
        member._value_ = value
        member.column_name = col_name
        return member

    def __int__(self):
        return self.value

class msg_event_type(Enum):
    recv_txt = 1
    recv_txt_repl = 2
    recv_stk = 3
    recv_stk_repl = 4
    recv_pic = 8
    send_txt = 5
    send_stk = 6

    def __int__(self):
        return self.value
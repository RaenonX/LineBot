# -*- coding: utf-8 -*-

from collections import OrderedDict
import time
from datetime import datetime, timedelta
from flask import Flask, url_for, render_template

from error import error

import db

class webpage_manager(object):
    LATEX_SPLITTER = '(LaTeX_END)'

    def __init__(self, flask_app, mongo_client, max_error_list_output, sys_config, gmail_api=None):
        self._system_config = sys_config

        self._flask_app = flask_app
        self._route_method_name = 'get_webpage'
        self._error_list_route_name = 'get_error_list'
        self._max_error_list_output = max_error_list_output
        self._gmail_api = gmail_api

        self._system_stats = db.system_statistics(mongo_client)
        self._content_holder = db.webpage_content_holder(mongo_client)

    def rec_error(self, error_instance, decoded_traceback, occurred_at, simplified=None):
        """Return (Error ID, email sent)"""
        send_email = self._system_config.get(db.config_data.SEND_ERROR_REPORT)

        try:
            with self._flask_app.app_context():
                err_type = error_instance.__class__.__name__

                err_detail = u'錯誤發生時間: {}\n'.format(datetime.now() + timedelta(hours=8))
                err_detail += u'頻道ID: {}\n\n'.format(occurred_at)
                err_detail += decoded_traceback
                if simplified is not None:
                    err_detail += u'\n\n'
                    try:
                        err_detail += simplified
                    except UnicodeEncodeError:
                        err_detail += simplified.encode('utf-8')
                    except UnicodeDecodeError:
                        err_detail += simplified.decode('utf-8')
                
                print '===================================='
                print '!!!!!!!!!!!!! AN ERROR HAS OCCURRED !!!!!!!!!!!!!'
                print err_detail.encode('utf-8')
                print '===================================='

                error_url = self.rec_webpage(err_detail, db.webpage_content_type.ERROR, err_type)
                error_id = int(error_url.split('/')[-1])
                
                if send_email:
                    err_detail += u'\n\nError URL: {}'.format(error_url)
                    self._gmail_api.send_message(' ({})'.format(err_type.encode('utf-8')), err_detail)

                return error_id, send_email
        except Exception as e:
            print e
            import traceback
            print traceback.format_exc()
    
    def rec_webpage(self, content, webpage_type, short_description=None, get_id=False):
        """Return recorded webpage url."""
        with self._flask_app.app_context():
            try:
                webpage_id = self._content_holder.rec_data(content, webpage_type, short_description)
                return webpage_id if get_id else url_for(self._route_method_name, seq_id=webpage_id)
            except Exception as e:
                return u'(網頁無法紀錄 - {} ({}))'.format(type(e), e.message)

    def get_error_dict(self):
        """
        { seq_id: url }
        """
        return OrderedDict([(u'{} - {}'.format(data.timestamp.strftime('%Y-%m-%d %H:%M:%S'), data.short_description), url_for(self._route_method_name, seq_id=data.seq_id)) for data in self._content_holder.get_error_page_list(self._max_error_list_output)])

    def get_webpage_data(self, id):
        if isinstance(id, (str, unicode)):
            id = int(id)
        webpage_data = self._content_holder.get_data(id)

        if webpage_data is None:
            return db.webpage_data.no_content_template()
        else:
            return webpage_data

    @staticmethod
    def render_webpage(page_data):
        content = page_data.content
        title = unicode(page_data.content_type)

        if page_data.content_type == db.webpage_content_type.LATEX:
            latex_script, normal_content = content.split(webpage_manager.LATEX_SPLITTER)
            return render_template('LaTeX.html', LaTeX_script=latex_script, Contents=webpage_manager.proc_str_to_render(normal_content), Title=title)
        elif page_data.content_type == db.webpage_content_type.STICKER_RANKING:
            content_data, foot = content[:-1], content[-1]
            return render_template('StickerRanking.html', Data=content_data, Foot=webpage_manager.proc_str_to_render(foot), Title=title)
        else:
            return webpage_manager.html_render_webpage(content, title)

    @staticmethod
    def proc_str_to_render(s):
        return [re.sub(r'((?:http|ftp|https)://(?:[\w_-]+(?:(?:\.[\w_-]+)+))(?:[\w.,@?^=%&:/~+#\!-]*[\w@?^=%&/~+#\!-]))', r'<a href="\1">\1</a>', s) for s in s.split('\n')]

    @staticmethod
    def html_render_error_list(boot_up, error_dict):
        """
        { output_text: url }
        """
        return render_template('ErrorList.html', boot_up=boot_up, ErrorDict=error_dict)

    @staticmethod
    def html_render_webpage(content, title):
        return render_template('WebPage.html', Contents=webpage_manager.proc_str_to_render(content), Title=title)
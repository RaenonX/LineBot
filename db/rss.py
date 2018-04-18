# -*- coding: utf-8 -*-

import os, sys
from datetime import datetime
import requests

from flask import request
from werkzeug.contrib.atom import AtomFeed

import db, bot, ext

from .base import db_base, dict_like_mapping

DB_NAME = 'rss'

RSS_ID_URL_BASE = os.getenv('RSS_ID_URL_BASE')
if RSS_ID_URL_BASE is None:
    print 'Specify RSS_ID_URL_BASE - the base url of rss atom id to environment variable.'
    sys.exit(1)

class rss_manager(db_base):
    COLLECTION_NAME = 'rss_data'

    def __init__(self, mongo_client):
        return super(rss_manager, self).__init__(mongo_client, DB_NAME, rss_manager.COLLECTION_NAME, True)

    def new_post(self, author_uid, author_name, render_text, title=None, url=None, affiliated_group=None):
        """
        *Return inserted seq_id if success, else return None. 
        *Automatically assign public group id to affiliated group id if affiliated_group is None.
        """
        if title is None:
            title = rss_manager.get_title_default(title)
            
        if url is not None and not rss_manager.validate_url(url):
            return None

        return super(rss_manager, self).insert_one(rss_data.init_by_field(title, render_text, author_name, author_uid, datetime.utcnow(), 
                                                                          affiliated_group=affiliated_group, skip_seq_id_check=True)).inserted_seq_id

    def del_post(self, author_uid, seq_id):
        """Return success or not in boolean. Seq_id can be either iterable or not."""

        seq_ids = ext.to_list(seq_id)

        cmd = super(rss_manager, self).delete_many({ rss_data.SEQUENCE_ID: { '$in': seq_ids }, rss_data.AUTHOR_UID: author_uid }).deleted_count

        return cmd == len(seq_ids) and len(seq_ids) > 0

    def search_post(self, execute_in_gid, keywords):
        """
        Return posts found in list(rss_data), else empty list. keyword can be either iterable or not.
        Posts will belongs to execute_in_gid or public post.
        """
        keywords = ext.to_list(keywords)
        find_cursor = super(rss_manager, self).find({ '$or': [ { rss_data.RENDER_TEXT: { '$regex': keyword } } for keyword in keywords ],
                                                      '$or': [ { rss_data.AFFILIATED_GROUP: execute_in_gid, rss_data.AFFILIATED_GROUP: db.PUBLIC_GROUP_ID } ] })

        return [rss_data(data) for data in find_cursor]

    def update_post(self, author_uid, author_name, seq_id, render_text, title=None, url=None):
        """Return updated or not in boolean."""
        update_dict = { rss_data.RENDER_TEXT: render_text, rss_data.AUTHOR_NAME: author_name }
        if title is not None:
            update_dict[rss_data.TITLE] = title
        if url is not None:
            update_dict[rss_data.URL] = url

        return super(rss_manager, self).update_one({ rss_data.SEQUENCE_ID: seq_id, rss_data.AUTHOR_UID: author_uid }, { '$set': update_dict }).modified_count > 0

    def get_post(self, seq_id):
        """Return rss_data if found, else None"""
        find_data = super(rss_manager, self).find_one({ rss_data.SEQUENCE_ID: seq_id }) 
        return None if find_data is None else rss_data(find_data)

    def get_posts(self, limit, affiliated_group=None):
        if affiliated_group is None:
            affiliated_group = db.PUBLIC_GROUP_ID

        find_cursor = super(rss_manager, self).find({ rss_data.AFFILIATED_GROUP: affiliated_group }).limit(limit)
        return [rss_data(data) for data in find_cursor]

    def get_atom_feed(self, group_id=None, rss_id=None):
        feed = AtomFeed(self.get_atom_title(), feed_url=request.url, url=request.url_root)

        if rss_id is None:
            rss_data_arr = self.get_posts(15, group_id)

            for rss_data in rss_data_arr:
                feed.add(rss_data.title, rss_data.render_text,
                         content_type='text',
                         author=rss_data.author_name,
                         url=rss_data.url_for_id(),
                         updated=rss_data.updated,
                         published=rss_data.published)
            return feed.get_response()
        else:
            rss_data = self.get_post(rss_id)
            return bot.webpage_manager.html_render_webpage(rss_data.to_string(), rss_data.title)

    def get_atom_title(self, group_id=None, rss_id=None):
        title = u'小水母公告'

        if group_id is not None:
            title += u' (群組: {})'.format(group_id)
        elif rss_id is not None:
            title += u' (# {})'.format(rss_id)

        return title

    @staticmethod
    def get_title_default(str, characters=10):
        return u'{}...'.format(str[0:10])

    @staticmethod
    def validate_url(url):
        response = requests.get(url)
        return response.ok

    @staticmethod
    def url_by_id(id):
        return u'{}{}'.format(RSS_ID_URL_BASE, id)

class rss_data(dict_like_mapping):
    SEQUENCE_ID = db_base.SEQUENCE

    TITLE = 't'
    RENDER_TEXT = 'rt'
    AUTHOR_NAME = 'an'
    AUTHOR_UID = 'au'
    URL = 'u'
    PUBLISHED = 'p'
    UPDATED = 'u'
    AFFILIATED_GROUP = 'g'

    @staticmethod
    def init_by_field(title, render_text, author_name, author_uid, published, updated=None, url=None, affiliated_group=None, skip_seq_id_check=False):
        init_dict = {
            rss_data.TITLE: title,
            rss_data.RENDER_TEXT: render_text,
            rss_data.AUTHOR_NAME: author_name,
            rss_data.AUTHOR_UID: author_uid,
            rss_data.URL: url,
            rss_data.PUBLISHED: published
        }

        init_dict[rss_data.UPDATED] = published if updated is None else updated
        init_dict[rss_data.AFFILIATED_GROUP] = db.PUBLIC_GROUP_ID if affiliated_group is None else affiliated_group

        return rss_data(init_dict, skip_seq_id_check)

    def __init__(self, org_dict, skip_seq_check=False):
        if org_dict is not None:
            main_check_list = [rss_data.TITLE, rss_data.RENDER_TEXT, rss_data.AUTHOR_NAME, 
                               rss_data.AUTHOR_UID, rss_data.PUBLISHED, rss_data.AFFILIATED_GROUP]
            if not skip_seq_check:
                main_check_list.append(rss_data.SEQUENCE_ID)

            if all(k in org_dict for k in main_check_list):
                pass
            else:
                raise ValueError('Incomplete pair data.')
        else:
            raise ValueError('Dictionary is none.')

        return super(rss_data, self).__init__(org_dict)

    @property
    def seq_id(self):
        return self[rss_data.SEQUENCE_ID]

    @seq_id.setter
    def seq_id(self, id):
        self[rss_data.SEQUENCE_ID] = id

    @property
    def title(self):
        return self[rss_data.TITLE]

    @property
    def render_text(self):
        return self[rss_data.RENDER_TEXT]

    @property
    def author_name(self):
        return self[rss_data.AUTHOR_NAME]

    @property
    def author_uid(self):
        return self[rss_data.AUTHOR_UID]

    @property
    def url(self):
        """Never lacks, but could be None if no url refer to"""
        return self[rss_data.URL]

    @property
    def published(self):
        return self[rss_data.PUBLISHED]

    @property
    def updated(self):
        return self[rss_data.UPDATED]

    @property
    def affiliated_group(self):
        return self[rss_data.AFFILIATED_GROUP]

    def url_for_id(self):
        return rss_manager.url_by_id(self.seq_id)

    def to_string(self):
        ret = []

        ret.append(u'#{} {}'.format(self.seq_id, self.title))
        ret.append(u'')
        ret.append(self.render_text)
        ret.append(u'')
        ret.append(u'張貼者: {} ({}...)'.format(self.author_name, self.author_uid[0:8]))
        ret.append(u'公告所屬群組: {}'.format(self.affiliated_group))
        ret.append(u'發布日期: UTC {}'.format(self._to_string_format_datetime(self.published)))
        if self.updated is not None and self.updated != self.published:
            ret.append(u'最後更新: UTC {}'.format(self._to_string_format_datetime(self.updated)))

        return u'\n'.join(ret)

    def to_simp_string(self):
        return u'#{} {} {} - UTC {}'.format(self.seq_id, u'公' if self.affiliated_group == db.PUBLIC_GROUP_ID else u'群', 
                                            self.title, self.published.strftime('%m/%d %H:%M'))

    def _to_string_format_datetime(self, dt):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
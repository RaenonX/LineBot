# -*- coding: utf-8 -*-

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError
import traceback
from multiprocessing.pool import ThreadPool

from bot import webpage_auto_gen 

class db_query_manager(object):
    def __init__(self, scheme, db_url, flask_app):
        urlparse.uses_netloc.append(scheme)

        self.url = urlparse.urlparse(db_url)
        self.set_connection()
        self._auto_gen = webpage_auto_gen.webpage(flask_app)
        self.pool = ThreadPool(processes=1)

    def sql_cmd_only(self, cmd):
        return self.sql_cmd(cmd, None)

    def sql_cmd(self, cmd, dict):
        apply_result = self.pool.apply(self._query_worker, (cmd, dict))
        return apply_result

    def _query_worker(self, cmd, dict):
        try:
            self.cur.execute(cmd, dict)
            result = self.cur.fetchall()
            self.conn.commit()
        except psycopg2.ProgrammingError as ex:
            if ex.message == 'no results to fetch':
                result = None
            elif ex.message == 'can\'t execute an empty query':
                result = None
            else:
                raise ex
        except psycopg2.InternalError as uiex:
            text = uiex.message
            text += u'\nSQL Query: {}'.format(cmd)
            text += u'\nSQL Parameter Dict: {}'.format(dict)

            result = None

            self._auto_gen.rec_error(text, traceback.format_exc().decode('utf-8'), u'(SQL DB)')
            self.close_connection()
            self.set_connection()
            self.sql_cmd(cmd, dict)
        except Exception as e:
            text = e.message
            text += u'\nSQL Query: {}'.format(cmd)
            text += u'\nSQL Parameter Dict: {}'.format(dict)

            result = None

            self._auto_gen.rec_error(text, traceback.format_exc().decode('utf-8'), u'(SQL DB)')
            raise e
        
        if result is not None:
            if len(result) > 0:
                return result
            else:
                return None
        else:
            return None


    def close_connection(self):
        self.conn.close()

    def set_connection(self):
        self.conn = psycopg2.connect(
            database=self.url.path[1:],
            user=self.url.username,
            password=self.url.password,
            host=self.url.hostname,
            port=self.url.port
        )
        self.conn.autocommit = True
        self.cur = self.conn.cursor()




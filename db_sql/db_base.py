# -*- coding: utf-8 -*-

import urlparse
import psycopg2
from sqlalchemy.exc import IntegrityError

class db_base_obj(object):
    def __init__(self, db_query_mgr):
        self.db_query_mgr = db_query_mgr

    def sql_cmd_only(self, cmd):
        return self.db_query_mgr.sql_cmd_only(cmd)

    def sql_cmd(self, cmd, dict):
        return self.db_query_mgr.sql_cmd(cmd, dict)



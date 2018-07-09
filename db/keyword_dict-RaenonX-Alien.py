# -*- coding: utf-8 -*-
import pymongo
from datetime import timedelta, datetime

from error import error
import ext

from .uid_ref import user_id_ref_manager
from .base import db_base, dict_like_mapping
from .misc import PackedStringResult, PackedResult

PUBLIC_GROUP_ID = 'C--------------------------------'

class word_type(ext.EnumWithName):
    TEXT = 0, '文字'
    STICKER = 1, '貼圖'
    PICTURE = 2, '圖片'

class group_dict_manager_range(ext.EnumWithName):
    GROUP_ONLY = 1, '群組'
    GROUP_AND_PUBLIC = 2, '群組+公用'
    GLOBAL = 3, '全域'

class UnknownFlagError(Exception):
    def __init__(self, *args):
        super(UnknownFlagError, self).__init__(*args)

class UnknownRangeError(Exception):
    def __init__(self, *args):
        return super(UnknownRangeError, self).__init__(*args)

class ActionNotAllowed(Exception):
    def __init__(self, *args):
        return super(ActionNotAllowed, self).__init__(*args)

class group_dict_manager(db_base):
    WORD_DICT_DB_NAME = 'word_dict'

    VALIDATION_JSON = """{
                           "grp": {
                             "$regex": "^[CR]{1}[0-9-a-f]{32}$",
                             "$options": ""
                           },
                           "kw": {
                             "$type": 2
                           },
                           "rep": {
                             "$type": 2
                           },
                           "prop": {
                             "$exists": true
                           },
                           "prop.dis": {
                             "$type": 8
                           },
                           "prop.pin": {
                             "$type": 8
                           },
                           "prop.kw_type": {
                             "$type": 16
                           },
                           "prop.rep_type": {
                             "$type": 16
                           },
                           "prop.lk_words": {
                             "$exists": true
                           },
                           "stats": {
                             "$exists": true
                           },
                           "stats.cr_uid": {
                             "$regex": "^[U]{1}[0-9a-f]{32}$",
                             "$options": ""
                           },
                           "stats.cr_time": {
                             "$type": 9
                           },
                           "stats.count": {
                             "$gte": 0
                           },
                           "$and": [
                             {
                               "$or": [
                                 {
                                   "prop.rep_txt": {
                                     "$type": 2
                                   }
                                 },
                                 {
                                   "prop.rep_txt": {
                                     "$type": 10
                                   }
                                 }
                               ]
                             },
                             {
                               "$or": [
                                 {
                                   "stats.dis_uid": {
                                     "$type": 2
                                   }
                                 },
                                 {
                                   "stats.dis_uid": {
                                     "$type": 10
                                   }
                                 }
                               ]
                             },
                             {
                               "$or": [
                                 {
                                   "stats.dis_time": {
                                     "$type": 9
                                   }
                                 },
                                 {
                                   "stats.dis_time": {
                                     "$type": 10
                                   }
                                 }
                               ]
                             }
                           ]
                         }"""

    # utilities
    def __init__(self, mongo_client, duplicate_cd_secs, repeat_call_cd_secs, group_id=PUBLIC_GROUP_ID, range=group_dict_manager_range.GROUP_ONLY):
        self._group_id = group_id
        self._available_range = range
        self._duplicate_cd_secs = duplicate_cd_secs
        self._repeat_call_cd_secs = repeat_call_cd_secs

        self._mongo_client = mongo_client
        self._uid_ref = user_id_ref_manager(mongo_client)

        super(group_dict_manager, self).__init__(mongo_client, group_dict_manager.WORD_DICT_DB_NAME, group_dict_manager.WORD_DICT_DB_NAME, True)

    def clone_instance(self, group_id, available_range=group_dict_manager_range.GROUP_ONLY):
        return group_dict_manager(self._mongo_client, self._duplicate_cd_secs, self._repeat_call_cd_secs, group_id, available_range)

    @property
    def is_public(self):
        return self._group_id == PUBLIC_GROUP_ID

    @property
    def available_range(self):
        return self._available_range

    # override
    def aggregate(self, pipeline, **kwargs):
        if self._available_range == group_dict_manager_range.GLOBAL:
            filter_dict = { pair_data.SEQUENCE: { '$exists': True }}
        elif self._available_range == group_dict_manager_range.GROUP_AND_PUBLIC:
            filter_dict = { '$or': [{ pair_data.AFFILIATED_GROUP: self._group_id }, { pair_data.AFFILIATED_GROUP: PUBLIC_GROUP_ID }] }
        elif self._available_range == group_dict_manager_range.GROUP_ONLY:
            filter_dict = { pair_data.AFFILIATED_GROUP: self._group_id }
        else:
            raise UnknownRangeError()

        pipeline = [ { '$match': filter_dict } ] + pipeline

        return super(group_dict_manager, self).aggregate(pipeline, **kwargs)

    def delete_many(self, filter, collation=None):
        if self._available_range == group_dict_manager_range.GLOBAL:
            raise ActionNotAllowed()
        elif self._available_range == group_dict_manager_range.GROUP_AND_PUBLIC or self._available_range == group_dict_manager_range.GROUP_ONLY:
            filter[pair_data.AFFILIATED_GROUP] = self._group_id
        else:
            raise UnknownRangeError()

        return super(group_dict_manager, self).delete_many(filter, collation)

    def insert_one(self, document, bypass_document_validation=False):
        if any(self._available_range == t for t in (group_dict_manager_range.GROUP_AND_PUBLIC, group_dict_manager_range.GROUP_ONLY, group_dict_manager_range.GLOBAL)):
            document[pair_data.AFFILIATED_GROUP] = self._group_id
        else:
            raise UnknownRangeError()

        return super(group_dict_manager, self).insert_one(document, bypass_document_validation)

    def find(self, *args, **kwargs):
        if len(args) < 1:
            args = [{}]

        if self._available_range == group_dict_manager_range.GLOBAL:
            pass
        elif self._available_range == group_dict_manager_range.GROUP_AND_PUBLIC:
            or_list = [{ pair_data.AFFILIATED_GROUP: self._group_id }, { pair_data.AFFILIATED_GROUP: PUBLIC_GROUP_ID }]

            if '$or' in args[0]:
                args[0]['$and'] = [{'$or': or_list}, {'$or': args[0]['$or']}]
                del args[0]['$or']
            else:
                args[0]['$or'] = or_list
        elif self._available_range == group_dict_manager_range.GROUP_ONLY:
            args[0][pair_data.AFFILIATED_GROUP] = self._group_id
        else:
            raise UnknownRangeError()
        
        return super(group_dict_manager, self).find(*args, **kwargs)

    def find_one(self, filter=None, *args, **kwargs):
        if self._available_range == group_dict_manager_range.GLOBAL:
            pass
        elif self._available_range == group_dict_manager_range.GROUP_AND_PUBLIC:
            or_list = [{ pair_data.AFFILIATED_GROUP: self._group_id }, { pair_data.AFFILIATED_GROUP: PUBLIC_GROUP_ID }]

            if '$or' in filter:
                filter['$and'] = [{'$or': or_list}, {'$or': filter['$or']}]
                del filter['$or']
            else:
                filter['$or'] = or_list
        elif self._available_range == group_dict_manager_range.GROUP_ONLY:
            filter[pair_data.AFFILIATED_GROUP] = self._group_id
        else:
            raise UnknownRangeError()

        return super(group_dict_manager, self).find_one(filter, *args, **kwargs)

    def find_one_and_update(self, filter, update, projection=None, sort=None, upsert=False, return_document=pymongo.ReturnDocument.BEFORE, **kwargs):
        if self._available_range == group_dict_manager_range.GLOBAL:
            pass
        elif self._available_range == group_dict_manager_range.GROUP_AND_PUBLIC:
            or_list = [{ pair_data.AFFILIATED_GROUP: self._group_id }, { pair_data.AFFILIATED_GROUP: PUBLIC_GROUP_ID }]

            if '$or' in filter:
                filter['$and'] = [{'$or': or_list}, {'$or': filter['$or']}]
                del filter['$or']
            else:
                filter['$or'] = or_list
        elif self._available_range == group_dict_manager_range.GROUP_ONLY:
            filter[pair_data.AFFILIATED_GROUP] = self._group_id
        else:
            raise UnknownRangeError()

        sort_tuple = (pair_data.AFFILIATED_GROUP, pymongo.DESCENDING)
        if sort is None:
            sort = [sort_tuple]
        else:
            sort.append(sort_tuple)
        return super(group_dict_manager, self).find_one_and_update(filter, update, projection, sort, upsert, return_document, **kwargs)

    def find_and_modify(self, query=None, update=None, upsert=False, sort=None, full_response=False, manipulate=False, **kwargs):
        if query is None:
            query = {}

        query[pair_data.AFFILIATED_GROUP] = self._group_id

        sort_tuple = (pair_data.AFFILIATED_GROUP, pymongo.DESCENDING)
        if sort is None:
            sort = [sort_tuple]
        else:
            sort.append(sort_tuple)

        return super(group_dict_manager, self).find_and_modify(query, update, upsert, sort, full_response, manipulate, **kwargs)

    def count(self, filter=None, **kwargs):
        if filter is None:
            filter = {}

        if self._available_range == group_dict_manager_range.GLOBAL:
            pass
        elif self._available_range == group_dict_manager_range.GROUP_AND_PUBLIC:
            or_list = [{ pair_data.AFFILIATED_GROUP: self._group_id }, { pair_data.AFFILIATED_GROUP: PUBLIC_GROUP_ID }]

            if '$or' in filter:
                filter['$and'] = [{'$or': or_list}, {'$or': filter['$or']}]
                del filter['$or']
            else:
                filter['$or'] = or_list
        elif self._available_range == group_dict_manager_range.GROUP_ONLY:
            filter[pair_data.AFFILIATED_GROUP] = self._group_id
        else:
            raise UnknownRangeError()

        return super(group_dict_manager, self).count(filter, **kwargs)

    # collection control
    def insert_keyword(self, keyword, reply, creator_id, pinned, kw_type, rep_type, linked_word=None, rep_attach_text=None):
        """Return error message in unicode type OR new pair data"""
        creator_id_ref = self._uid2ref(creator_id)

        if keyword.replace(' ', '') == '':
            return error.main.invalid_thing_with_correct_format(u'關鍵字', u'字數大於0，但小於500字(中文250字)的字串', keyword)
        elif reply.replace(' ', '') == '':
            return error.main.invalid_thing_with_correct_format(u'回覆', u'字數大於0，但小於500字(中文250字)的字串', reply)
        elif not isinstance(linked_word, (list, tuple)):
            if linked_word is None or len(linked_word) == 0:
                linked_word = []
            else:
                raise ValueError('linked word should be list or tuple type.')
        elif len(linked_word) > error.line_bot_api.MAX_TEMPLATE_ACTIONS:
            return error.main.miscellaneous(u'相關關鍵字最高只能寫入{}組關鍵字。'.format(error.line_bot_api.MAX_TEMPLATE_ACTIONS))

        cursor = self.find({ pair_data.KEYWORD: keyword }, sort=[(pair_data.SEQUENCE, pymongo.DESCENDING)], limit=1)

        for data in cursor:
            linked_word.extend(pair_data(data).linked_words)

        if kw_type == word_type.STICKER:
            keyword = keyword.replace(' ', '')

        if rep_type == word_type.STICKER:
            reply = reply.replace(' ', '')

        if not pinned:
            check_result = self.count({
                '$and': [
                    { pair_data.KEYWORD: keyword }, 
                    { pair_data.PROPERTIES + '.' + pair_data.PINNED: True },
                    { pair_data.PROPERTIES + '.' + pair_data.DISABLED: False }]})
            if check_result > 0:
                return error.main.miscellaneous(u'已存在置頂回覆組，無法覆寫。')

        if self._group_id == PUBLIC_GROUP_ID and pinned:
            return error.main.miscellaneous(u'公用資料庫無法製作置頂回覆組。')

        pair = pair_data.init_by_field(self._group_id, keyword, reply, datetime.now(), creator_id_ref, kw_type, rep_type, pinned, linked_word, rep_attach_text, True)
        insert_result = self.insert_one(pair)

        if insert_result is not None:
            self.disable_keyword(keyword, creator_id_ref, pinned, insert_result.inserted_seq_id)
            self.find_and_modify({ pair_data.KEYWORD: keyword.lower(),
                                   pair_data.STATISTICS + '.' + pair_data.CREATED_TIME: { '$gt': datetime.now() - timedelta(seconds=self._duplicate_cd_secs) },
                                   pair_data.SEQUENCE: { '$ne': insert_result.inserted_seq_id }}, sort=[(pair_data.SEQUENCE, pymongo.DESCENDING)], remove=True)

            return pair
        else:
            return None

    def disable_keyword(self, keywords, disabler, pinned=False, exclude_id=None):
        """Return disabled data list in type pair_data. None if nothing updated."""
        if isinstance(keywords, (str, unicode)):
            keywords = [keywords]

        query_dict = { pair_data.KEYWORD: { '$in': [kw.lower() for kw in keywords] } }

        if exclude_id is not None:
            query_dict[pair_data.SEQUENCE] = { '$ne': exclude_id }
            
        return self._disable(query_dict, disabler, pinned)

    def disable_keyword_by_id(self, id_or_id_list, disabler, pinned=False):
        """Return disabled data list in type pair_data. None if nothing updated."""
        if not isinstance(id_or_id_list, list):
            id_or_id_list = [id_or_id_list]

        query_dict = { pair_data.SEQUENCE: { '$in': id_or_id_list } }
        return self._disable(query_dict, disabler, pinned)

    def _disable(self, query_dict, disabler, pinned):
        query_dict[pair_data.PROPERTIES + '.' + pair_data.PINNED] = pinned
        query_dict[pair_data.PROPERTIES + '.' + pair_data.DISABLED] = False
        
        disabled_pair_data = list(self.find(query_dict))
        self.update_many(query_dict, 
        {
            '$set': { pair_data.PROPERTIES + '.' + pair_data.DISABLED: True, 
                      pair_data.STATISTICS + '.' + pair_data.DISABLED_TIME: datetime.now(), 
                      pair_data.STATISTICS + '.' + pair_data.DISABLER: self._uid2ref(disabler) }
        })
        return [pair_data(data) for data in disabled_pair_data]

    def get_reply_data(self, keyword, kw_type=word_type.TEXT):
        """Return none if nothing found, else return result in pair_data class"""
        data_result = self.find_one({
            pair_data.KEYWORD: keyword.lower(),
            pair_data.PROPERTIES + '.' + pair_data.DISABLED: False,
            pair_data.PROPERTIES + '.' + pair_data.KEYWORD_TYPE: int(kw_type)
        }, sort=[(pair_data.PROPERTIES + '.' + pair_data.PINNED, pymongo.DESCENDING), 
                 (pair_data.SEQUENCE, pymongo.DESCENDING)])

        if data_result is not None:
            data_result = pair_data(data_result)
            if data_result.last_call is None or data_result.last_call < datetime.now() - timedelta(seconds=self._repeat_call_cd_secs):
                self.update({ pair_data.SEQUENCE: data_result.seq_id }, {
                    '$inc': { pair_data.STATISTICS + '.' + pair_data.CALLED_COUNT: 1 },
                    '$set': { pair_data.STATISTICS + '.' + pair_data.LAST_CALL: datetime.now() }
                })

            return pair_data(data_result)

    def set_pinned_by_index(self, ids, pinned=True):
        """
        Add Linked words by ID(s) to specified keyword pair. Keyword pair is specified by ID(s).

        Parameters:
            ids: ID of pair(s) to execute. This can be list(in int, str, or unicode), int, str or unicode. Contents will be automatically transformed to int type. 

        Returns:
            Return true if matched count is equal to modified count AND matched count is greater than 0.
        """

        if isinstance(ids, (int, long)):
            ids = [ids]

        ids = [int(id) for id in ids]

        update_result = self.update_many({ '$and': [{ pair_data.SEQUENCE: { '$in': ids } }, { pair_data.PROPERTIES + '.' + pair_data.DISABLED: False }] }, 
                                         { '$set': { pair_data.PROPERTIES + '.' + pair_data.PINNED: pinned }})

        return update_result.matched_count == update_result.modified_count and update_result.matched_count > 0

    def set_pinned_by_keyword(self, keywords, pinned=True):
        """
        Add Linked words by ID(s) to specified keyword pair. Keyword pair is specified by ID(s).

        Parameters:
            target_ids: ID of pair(s) to execute. This can be list(in int, str, or unicode), int, str or unicode. Contents will be automatically transformed to int type. 
            linked_words: Word(s) to execute. This can be list(in str, or unicode), str or unicode.

        Returns:
            Return true if matched count is equal to modified count AND matched count is greater than 0.
        """

        if isinstance(keywords, (str, unicode)):
            keywords = [keywords]

        update_result = self.update_many({ '$and': [{ pair_data.KEYWORD: { '$in': [kw.lower() for kw in keywords] } }, 
                                                    { pair_data.PROPERTIES + '.' + pair_data.DISABLED: False }] }, 
                                         { '$set': { pair_data.PROPERTIES + '.' + pair_data.PINNED: pinned }})

        return update_result.matched_count == update_result.modified_count and update_result.matched_count > 0

    def search_pair_by_keyword(self, keyword, data_exact_same=False):
        """Return none if nothing found, else return result in list of pair_data class"""
        keyword = unicode(keyword).lower()

        filter_dict = {
            '$or': [
                { pair_data.KEYWORD: keyword if data_exact_same else { '$regex': keyword, '$options': 'i' } },
                { pair_data.REPLY: keyword if data_exact_same else { '$regex': keyword, '$options': 'i' } }
            ]
        }

        return self._search(filter_dict)

    def _filter_keyword_regex(self, keyword):
        for c in ['(', ')', '[', ']', '*']:
            keyword = keyword.replace(c, '\\' + c)

        return keyword

    def search_pair_by_index(self, start_id_or_id_list, end_id=None):
        """Return none if nothing found, else return result in list of pair_data class"""
        if not isinstance(start_id_or_id_list, (int, long, list)) or (not isinstance(end_id, (int, long)) and end_id is not None):
            raise ValueError('Start index must be integer, long or list. End index must be integer or long.')

        if isinstance(start_id_or_id_list, list):
            filter_dict = { pair_data.SEQUENCE: { '$in': start_id_or_id_list } }
        else:
            if end_id is None:
                filter_dict = { pair_data.SEQUENCE: int(start_id_or_id_list) }
            else:
                filter_dict = { pair_data.SEQUENCE: { '$gte': int(start_id_or_id_list), '$lte': int(end_id) } }

        return self._search(filter_dict)

    def search_all_available_pair(self):
        """Return none if nothing found, else return result in list of pair_data class"""
        return self._search({})

    def search_pair_by_creator(self, uid):
        """Return none if nothing found, else return result in list of pair_data class"""
        filter_dict = { pair_data.STATISTICS + '.' + pair_data.CREATOR: disabler }
        return self._search(filter_dict)
    
    def _preproc_linked_by_id(self, target_ids, linked_ids, able_to_mod_pin):
        if isinstance(target_ids, (int, str)):
            target_ids = [int(target_ids)]

        target_ids = [int(i) for i in target_ids]

        if isinstance(linked_ids, (str, unicode)):
            linked_ids = [linked_ids]
            
        filter_dict = { pair_data.SEQUENCE: { '$in': target_ids } }
        if not able_to_mod_pin:
            filter_dict[pair_data.PROPERTIES + '.' + pair_data.PINNED] = False

        return filter_dict, linked_ids

    def add_linked_word_by_id(self, target_ids, linked_ids, able_to_mod_pin=False):
        """
        Add Linked words by ID(s) to specified keyword pair. Keyword pair is specified by ID(s).

        Parameters:
            target_ids: ID of pair(s) to execute. This can be list(in int, str, or unicode), int, str or unicode. Contents will be automatically transformed to int type. 
            linked_words: Word(s) to execute. This can be list(in str, or unicode), str or unicode.

        Returns:
            Return true if matched count is equal to modified count AND matched count is greater than 0.
        """
        filter_dict, linked_ids = self._preproc_linked_by_id(target_ids, linked_ids, able_to_mod_pin)

        return self._postproc_linked(filter_dict, linked_ids, True)

    def del_linked_word_by_id(self, target_ids, linked_ids, able_to_mod_pin=False):
        """
        Delete Linked words from specified keyword pair. Keyword pair is specified by ID(s).

        Parameters:
            target_ids: ID of pair(s) to execute. This can be list(in int, str, or unicode), int, str or unicode. Contents will be automatically transformed to int type. 
            linked_words: Word(s) to execute. This can be list(in str, or unicode), str or unicode.

        Returns:
            Return true if matched count is equal to modified count AND matched count is greater than 0.
        """
        filter_dict, linked_ids = self._preproc_linked_by_id(target_ids, linked_ids, able_to_mod_pin)

        return self._postproc_linked(filter_dict, linked_ids, False)

    def _preproc_linked_by_word(self, target_words, linked_words, able_to_mod_pin):
        if isinstance(target_words, (str, unicode)):
            target_words = [target_words]
        target_words = [w.lower() for w in target_words]

        if isinstance(linked_words, (str, unicode)):
            linked_words = [linked_words]
        linked_words = list(filter(None, linked_words))

        filter_dict = { pair_data.KEYWORD: { '$in': target_words } }
        if not able_to_mod_pin:
            filter_dict[pair_data.PROPERTIES + '.' + pair_data.PINNED] = False

        return filter_dict, linked_words

    def add_linked_word_by_word(self, target_words, linked_words, able_to_mod_pin=False):
        """
        Add Linked words by ID(s) to specified keyword pair. Keyword pair is specified by keyword(s).

        Parameters:
            target_words: Keyword of pair(s) to execute. This can be list(in str, or unicode), str or unicode.
            linked_words: Word(s) to execute. This can be list(in str, or unicode), str or unicode.

        Returns:
            Return true if matched count is equal to modified count AND matched count is greater than 0.
        """
        filter_dict, linked_words = self._preproc_linked_by_word(target_words, linked_words, able_to_mod_pin)
        
        return self._postproc_linked(filter_dict, linked_words, True)

    def del_linked_word_by_word(self, target_words, linked_words, able_to_mod_pin=False):
        """
        Delete Linked words from specified keyword pair. Keyword pair is specified by keyword.

        Parameters:
            target_words: Keyword of pair(s) to execute. This can be list(in str, or unicode), str or unicode.
            linked_words: Word(s) to execute. This can be list(in str, or unicode), str or unicode.

        Returns:
            Return true if matched count is equal to modified count AND matched count is greater than 0.
        """
        filter_dict, linked_words = self._preproc_linked_by_word(target_words, linked_words, able_to_mod_pin)

        return self._postproc_linked(filter_dict, linked_words, False)

    def _postproc_linked(self, filter_dict, linked_words, is_add, mod_disabled=False):
        """is_add: True=ADD, False=DEL"""
        if not mod_disabled:
            filter_dict[pair_data.PROPERTIES + "." + pair_data.DISABLED] = False

        if len(linked_words) < 1:
            return False

        if is_add:
            result = self.update_many(filter_dict, { '$push': { pair_data.PROPERTIES + '.' + pair_data.LINKED_WORDS: { '$each': linked_words } } })
        else:
            result = self.update_many(filter_dict, { '$pullAll': { pair_data.PROPERTIES + '.' + pair_data.LINKED_WORDS: linked_words } })
        return result.matched_count > 0 and result.matched_count == result.modified_count

    def _search(self, filter_dict):
        result = self.find(filter_dict).sort([(pair_data.SEQUENCE, pymongo.DESCENDING)])
        return None if result.count() <= 0 else [pair_data(data) for data in result]

    # statistics (output dict)
    def most_used(self, including_disabled=False, limit=None):
        return self._sort_call_count(including_disabled, pymongo.DESCENDING, limit)

    def least_used(self, including_disabled=False, limit=None):
        return self._sort_call_count(including_disabled, pymongo.ASCENDING, limit)

    def _sort_call_count(self, including_disabled, asc_or_dsc, limit):
        if including_disabled:
            result = self.find()
        else:
            result = self.find({ pair_data.PROPERTIES + '.' + pair_data.DISABLED: False })

        result = result.sort([(pair_data.STATISTICS + '.' + pair_data.CALLED_COUNT, asc_or_dsc), (pair_data.SEQUENCE, asc_or_dsc)])
        result = self.cursor_limit(result, limit, 1)
        return None if result is None else [data for data in result]

    def user_created_id_array(self, uid):
        """Return empty array if nothing found, else return array of sequence id."""
        result = self.find({ pair_data.STATISTICS + '.' + pair_data.CREATOR: self._uid2ref(uid) }, 
                           { pair_data.SEQUENCE: True } ).sort(pair_data.SEQUENCE, pymongo.ASCENDING)

        if result is not None:
            return [data[pair_data.SEQUENCE] for data in result]
        else:
            return []

    def rank_of_used_count(self, count):
        # TODO: https://stackoverflow.com/questions/25843255/mongodb-aggregate-count-on-multiple-fields-simultaneously
        return self.count({ pair_data.STATISTICS + '.' + pair_data.CALLED_COUNT: { '$gt': count } }) + 1 

    @staticmethod
    def _list_result(data_list, string_format_function, limit=None, append_first_list=None, no_result_text=None):
        _list_limited = []
        _list_full = []

        if append_first_list is not None:
            _list_limited.extend(append_first_list)
            _list_full.extend(append_first_list)

        count = 0 if data_list is None else len(data_list)

        if count <= 0:
            if no_result_text is None:
                no_res = error.main.no_result()
            else:
                no_res = no_result_text

            _list_limited.append(no_res)
            _list_full.append(no_res)
        else:
            _list_full.append(u'共有{}筆結果\n'.format(count))
            
            if limit is not None:
                _limited_data_list = data_list[:limit]
            else:
                _limited_data_list = data_list

            _list_limited.extend([string_format_function(data) for data in _limited_data_list])
            _list_full.extend([string_format_function(data) for data in data_list])

            if limit is not None:
                data_left = count - limit
            else:
                data_left = -1

            if data_left > 0:
                _list_limited.append(u'...(還有{}筆)'.format(data_left))

        return PackedStringResult(_list_limited, _list_full)

    @staticmethod
    def _keyword_repr(kw_data, simplify=True, simplify_max_length=8):
        kw = kw_data.keyword_true
        kw_type = kw_data.keyword_type

        if kw_type == word_type.STICKER:
            return u'(貼圖ID {})'.format(kw)
        elif kw_type == word_type.PICTURE:
            if simplify:
                kw = kw[0:7]
            return u'(圖片雜湊 {})'.format(kw)
        elif kw_type == word_type.TEXT:
            if simplify:
                kw = ext.simplify_string(kw, simplify_max_length)
            return kw
        else:
            raise ValueError('Undefined keyword type.')

    @staticmethod
    def _reply_repr(rep_data, simplify=True, simplify_max_length=8):
        rep = rep_data.reply_true
        rep_type = rep_data.reply_type

        if rep_type == word_type.STICKER:
            return u'(貼圖ID {})'.format(rep)
        elif rep_type == word_type.PICTURE:
            return u'(圖片URL: {})'.format(rep)
        elif rep_type == word_type.TEXT:
            if simplify:
                rep = ext.simplify_string(rep, simplify_max_length)
            return rep
        else:
            raise ValueError('Undefined reply type.')

    # statistics (output unicode)
    def get_ranking_call_count_string(self, limit=None):
        if not isinstance(limit, (int, long)):
            raise ValueError('Limit must be integer.')

        cursor = self.find().sort(pair_data.STATISTICS + '.' + pair_data.CALLED_COUNT, pymongo.DESCENDING)
        result = list(self.cursor_limit(cursor, limit))

        if len(result) > 0:
            data_list = list(result)
            
            text_to_join = []
            ranking = u'' if limit is None else u' (前{}名)'.format(limit)
            text_to_join.append(u'呼叫次數排行{}:'.format(ranking))

            last = [0, 0]

            for index, data in enumerate(data_list, start=1):
                data = pair_data(data)
                if data.call_count == last[1]:
                    index = last[0]

                text_to_join.append(u'第{}名 - #{} - {} ({}次{})'.format(index, data.seq_id, group_dict_manager._keyword_repr(data), data.call_count, u' - 已固定' if data.disabled else ''))

                last[0] = index
                last[1] = data.call_count
        else:
            text_to_join.append(error.main.no_result())

        return '\n'.join(text_to_join)

    def user_created_rank_string(self, limit=None, line_api_wrapper=None):
        pipeline = [
            { '$project': { 
                pair_data.CREATOR: '$' + pair_data.STATISTICS + '.' + pair_data.CREATOR,
                pair_data.CALLED_COUNT: '$' + pair_data.STATISTICS + '.' + pair_data.CALLED_COUNT,
                pair_data.SEQUENCE: True } }, 
            { '$group': { 
                '_id': '$' + pair_data.CREATOR,
                PairCreatorRankingData.PAIR_COUNT: { '$sum': 1 },
                PairCreatorRankingData.PAIR_USED_COUNT: { '$sum': '$' + pair_data.CALLED_COUNT },
                PairCreatorRankingData.AVG_USED_COUNT: { '$avg': '$' + pair_data.CALLED_COUNT },
                PairCreatorRankingData.CREATED_PAIR_SEQ: { '$push': '$' + pair_data.SEQUENCE }
            } },
            { '$addFields': {
                PairCreatorRankingData.UID_REF: '$_id', 
                PairCreatorRankingData.ACTIVITY_POINT: { '$let': {
                    'vars': {
                        'sum_num': { '$add': ['$' + PairCreatorRankingData.PAIR_USED_COUNT, '$' + PairCreatorRankingData.PAIR_COUNT] },
                        'ct_pow': { '$pow': ['$' + PairCreatorRankingData.PAIR_USED_COUNT, 2] }
                    },
                    'in': { '$cond': [
                        { '$eq': [ '$$sum_num', 0 ] },
                        0,
                        { '$divide': [ '$$ct_pow', '$$sum_num' ] }
                    ] }
                } }
            } }, 
            { '$sort': { PairCreatorRankingData.ACTIVITY_POINT: pymongo.DESCENDING } }
        ]
        if limit is not None:
            pipeline.append({ '$limit': limit })
        aggregate_result = list(self.aggregate(pipeline))

        if len(aggregate_result) > 0:
            data_list = PairCreatorRankingResult(list(aggregate_result))
            
            text_to_join = []
            ranking = u'' if limit is None else u' (前{}名)'.format(limit)
            text_to_join.append(u'使用者製作排行{}:'.format(ranking))

            for index, user_data in enumerate(data_list, start=1):
                creator_uid_ref = user_data.creator_uid_ref

                if line_api_wrapper is None:
                    uname = u'用戶參照編號 #'.format(creator_uid_ref)
                else:
                    profile = line_api_wrapper.profile(creator_uid_ref)
                    if profile is None:
                        uname = error.main.line_account_data_not_found()
                    else:
                        uname = profile.display_name

                text_to_join.append(u'第{}名 - {}\n{}組 | {}次 | {:.2f}次/組 | {} pt'.format(
                    index, uname, user_data.created_pair_count, user_data.created_pair_used_count, user_data.created_pair_avg_used_count, ext.simplify_num(user_data.activity_point)))
        else:
            text_to_join = [error.main.no_result()]

        return '\n'.join(text_to_join)

    def recently_called_string(self, limit=None):
        result = self.find({ pair_data.STATISTICS + '.' + pair_data.LAST_CALL: { '$ne': None } }).sort(pair_data.STATISTICS + '.' + pair_data.LAST_CALL, pymongo.DESCENDING)
        result = self.cursor_limit(result, limit)
        data_list = None if result is None else list(result)

        SIMPLIFY_MAX_STRING_LENGTH = 8

        def format_string(data):
            data = pair_data(data)
            kw = group_dict_manager._keyword_repr(data, True, SIMPLIFY_MAX_STRING_LENGTH)

            return u'#{} {} @{}'.format(data.seq_id, kw, (data.last_call + timedelta(hours=8)).strftime('%m/%d %H:%M'))

        return PackedStringResult.init_by_field(data_list, format_string, limit, u'回覆組呼叫排行(前{}名):'.format(len(data_list)), error.main.no_result()).limited

    def get_statistics_string(self, is_active_only=False):
        result = KeywordDictionaryStatistics()

        result.pair_count = self.count()
        result.pair_count_disabled = self.count({ pair_data.PROPERTIES + '.' + pair_data.DISABLED: True })

        SUM_USED_COUNT = 'sum_ct'

        ######################
        ### GETTING RESULT ###
        ######################

        try:
            result.used_count = self.aggregate([
                { '$project': { pair_data.STATISTICS + '.' + pair_data.CALLED_COUNT: True }  }, 
                { '$group': {
                    '_id': 1,
                    SUM_USED_COUNT: { '$sum': '$' + pair_data.STATISTICS + '.' + pair_data.CALLED_COUNT }
                } }
            ]).next()[SUM_USED_COUNT]

            aggregate_type_group_dict = {str(type_num): { '$sum': '$' + str(type_num) } for type_num in list(map(int, word_type)) }
            aggregate_type_group_dict['_id'] = None
            
            aggregate_kw_type_project_dict = {str(type_num): { '$cond': [{ '$eq': ['$' + pair_data.PROPERTIES + '.' + pair_data.KEYWORD_TYPE, type_num] }, 1, 0] } for type_num in list(map(int,    word_type)) }
            aggregate_rep_type_project_dict = {str(type_num): { '$cond': [{ '$eq': ['$' + pair_data.PROPERTIES + '.' + pair_data.REPLY_TYPE, type_num] }, 1, 0] } for type_num in list(map(int,     word_type)) }

            result.keyword_type_count = self.aggregate([
                { '$project': aggregate_kw_type_project_dict },
                { '$group': aggregate_type_group_dict }
            ]).next()
            del result.keyword_type_count['_id']

            result.reply_type_count = self.aggregate([
                { '$project': aggregate_rep_type_project_dict },
                { '$group': aggregate_type_group_dict }
            ]).next()
            del result.reply_type_count['_id']

            now_time = datetime.now() + timedelta(hours=8)
            result.created_in_days = self.aggregate([
                { '$project': {
                    CreatedInDaysData.IN_1DAY: { '$cond': [{ '$gte': ['$' + pair_data.STATISTICS + '.' + pair_data.CREATED_TIME, now_time - timedelta(days=1)] }, 1, 0] },
                    CreatedInDaysData.IN_3DAYS: { '$cond': [{ '$gte': ['$' + pair_data.STATISTICS + '.' + pair_data.CREATED_TIME, now_time - timedelta(days=3)] }, 1, 0] },
                    CreatedInDaysData.IN_7DAYS: { '$cond': [{ '$gte': ['$' + pair_data.STATISTICS + '.' + pair_data.CREATED_TIME, now_time - timedelta(days=7)] }, 1, 0] },
                    CreatedInDaysData.IN_15DAYS: { '$cond': [{ '$gte': ['$' + pair_data.STATISTICS + '.' + pair_data.CREATED_TIME, now_time - timedelta(days=15)] }, 1, 0] }
                } },
                { '$group' : {
                    '_id': None,
                    CreatedInDaysData.IN_1DAY: { '$sum': '$' + CreatedInDaysData.IN_1DAY },
                    CreatedInDaysData.IN_3DAYS: { '$sum': '$' + CreatedInDaysData.IN_3DAYS },
                    CreatedInDaysData.IN_7DAYS: { '$sum': '$' + CreatedInDaysData.IN_7DAYS },
                    CreatedInDaysData.IN_15DAYS: { '$sum': '$' + CreatedInDaysData.IN_15DAYS }
                } }
            ]).next()
        except StopIteration:
            result = KeywordDictionaryStatistics()

        #####################
        ### STRING OUTPUT ###
        #####################

        text_to_join = []

        text_to_join.append(u'{}組 (失效{}) | {}次 | {:.2f}次/組 | 可用率{:.2%}'.format(result.pair_count, result.pair_count_disabled, result.used_count, result.avg, result.usable_rate))
        if result.created_in_days is not None:
            cr_his_str = result.created_in_days.get_string()
            text_to_join.append(u'回覆組製作量: {}'.format(cr_his_str))

        if result.keyword_type_count is None:
            text_to_join.append(u'沒有統計資料。')
        else:
            text_to_join.append(u'關鍵字種類: {}'.format(' '.join([u'{} {}組'.format(unicode(word_type(int(type))), count) for type, count in result.keyword_type_count.iteritems()])))
            text_to_join.append(u'回覆種類: {}'.format(' '.join([u'{} {}組'.format(unicode(word_type(int(type))), count) for type, count in result.reply_type_count.iteritems()])))

        return '\n'.join(text_to_join)

    # statistics format
    @staticmethod
    def list_keyword(data_list, limit=None, append_first=None, no_result=None, max_str_length=8):
        def format_string(data):
            data = pair_data(data)
            kw = group_dict_manager._keyword_repr(data, True, max_str_length)
            rep = group_dict_manager._reply_repr(data, True, max_str_length)

            return u'#{}{}{} {} → {}'.format(data.seq_id, u'X' if data.disabled else u'', u'P' if data.pinned else u'', kw, rep)

        return PackedStringResult.init_by_field(data_list, format_string, limit, append_first, no_result)

    @staticmethod
    def list_keyword_info(data_list, kwd_mgr=None, line_api_wrapper=None, limit=3, append_first=None, no_result=None):
        SINGLE_LIMIT = 50

        def format_string(data):
            data = pair_data(data)
            return data.detailed_text(True, line_api_wrapper, kwd_mgr)

        data_count = len(data_list) if data_list is not None else 0

        if data_count > SINGLE_LIMIT:
            err_msg_list = [error.keyword_pair.too_many_matched_data(data_count, SINGLE_LIMIT)]
            return PackedStringResult(err_msg_list, err_msg_list)
        else:
            return PackedStringResult.init_by_field(data_list, format_string, limit, append_first, no_result, '\n\n')

    @staticmethod
    def get_upper_index(str):
        return [i for i, c in enumerate(unicode(str)) if c.isupper()]

    # utilities
    def _uid2ref(self, uid):
        return self._uid_ref.get_ref_id_or_record(uid)

    def _ref2uid(self, ref):
        """Return none if not found"""
        return self._uid_ref.get_uid(ref)

class pair_data(dict_like_mapping):
    """
    {
        _seq: INTEGER - INDEX
        keyword: STRING
        reply: STRING
        properties: {
            disabled: BOOLEAN,
            pinned: BOOLEAN,
            keyword_type: WORD_TYPE
            reply_type: WORD_TYPE
            reply_attach_text: STRING
            linked_word: ARRAY(STRING) (MAX 30)
        }
        statistics: {
            created_time: TIMESTAMP
            creator: STRING
            disabled_time: TIMESTAMP
            disabler: STRING
            last_call: TIMESTAMP
            called_count: INT
        }
    }
    """
    
    HASH_LENGTH = 56
    HASH_TYPE = 'SHA224'

    SEQUENCE = db_base.SEQUENCE

    AFFILIATED_GROUP = 'grp'
    KEYWORD = 'kw'
    KEYWORD_UPPER_INDEX = 'kw_i'
    REPLY = 'rep'
    REPLY_UPPER_INDEX = 'rep_i'

    PROPERTIES = 'prop'
    DISABLED = 'dis'
    PINNED = 'pin'
    KEYWORD_TYPE = 'kw_type'
    REPLY_TYPE = 'rep_type'
    REPLY_ATTACH_TEXT = 'rep_txt'
    LINKED_WORDS = 'lk_words'

    STATISTICS = 'stats'
    CREATED_TIME = 'cr_time'
    CREATOR = 'cr_uid'
    DISABLED_TIME = 'dis_time'
    DISABLER = 'dis_uid'
    LAST_CALL = 'last_time'
    CALLED_COUNT = 'count'

    @staticmethod
    def init_by_field(affiliated_group, keyword, reply, created_time, creator, kw_type=word_type.TEXT, rep_type=word_type.TEXT, pinned=False, linked_words=None, reply_attach_text=None, skip_seq_id_check=False):
        if linked_words is None:
            linked_words = []

        init_dict = {
            pair_data.AFFILIATED_GROUP: affiliated_group,
            pair_data.KEYWORD: keyword.lower(),
            pair_data.KEYWORD_UPPER_INDEX: group_dict_manager.get_upper_index(keyword),
            pair_data.REPLY: reply.lower(),
            pair_data.REPLY_UPPER_INDEX: group_dict_manager.get_upper_index(reply),
            pair_data.PROPERTIES: {
                pair_data.DISABLED: False,
                pair_data.PINNED: pinned,
                pair_data.KEYWORD_TYPE: int(kw_type),
                pair_data.REPLY_TYPE: int(rep_type),
                pair_data.REPLY_ATTACH_TEXT: reply_attach_text,
                pair_data.LINKED_WORDS: linked_words
            },
            pair_data.STATISTICS: {
                pair_data.CREATED_TIME: created_time,
                pair_data.CREATOR: creator,
                pair_data.DISABLED_TIME: None,
                pair_data.DISABLER: None,
                pair_data.LAST_CALL: None,
                pair_data.CALLED_COUNT: 0
            }
        }

        return pair_data(init_dict, skip_seq_id_check)

    def __init__(self, org_dict, skip_seq_id_check=False):
        if org_dict is not None:
            main_check_list = [pair_data.AFFILIATED_GROUP, pair_data.KEYWORD, pair_data.REPLY, pair_data.STATISTICS, pair_data.PROPERTIES]
            if not skip_seq_id_check:
                main_check_list.append(pair_data.SEQUENCE)
            if all(k in org_dict for k in main_check_list):
                if all(k in org_dict[pair_data.PROPERTIES] for k in (pair_data.DISABLED, pair_data.PINNED, pair_data.KEYWORD_TYPE, pair_data.REPLY_TYPE, pair_data.REPLY_ATTACH_TEXT, pair_data.LINKED_WORDS)):
                    if all(k in org_dict[pair_data.STATISTICS] for k in (pair_data.CREATED_TIME, pair_data.CREATOR, pair_data.DISABLED_TIME, pair_data.DISABLER, pair_data.LAST_CALL, pair_data.CALLED_COUNT)):
                        pass
                    else:
                        raise ValueError('Incomplete statistics field.')
                else:
                    raise ValueError('Incomplete properties field.')
            else:
                raise ValueError('Incomplete pair data.')

            if pair_data.KEYWORD_UPPER_INDEX not in org_dict:
                org_dict[pair_data.KEYWORD_UPPER_INDEX] = group_dict_manager.get_upper_index(org_dict[pair_data.KEYWORD].lower())

            if pair_data.REPLY_UPPER_INDEX not in org_dict:
                org_dict[pair_data.REPLY_UPPER_INDEX] = group_dict_manager.get_upper_index(org_dict[pair_data.REPLY].lower())
        else:
            raise ValueError('Dictionary is none.')

        return super(pair_data, self).__init__(org_dict)

    @property
    def seq_id(self):
        return self[pair_data.SEQUENCE]

    @property
    def affiliated_group(self):
        return self[pair_data.AFFILIATED_GROUP]

    @property
    def keyword(self):
        return self[pair_data.KEYWORD]

    @property
    def keyword_upper_index(self):
        return self[pair_data.KEYWORD_UPPER_INDEX]

    @property
    def keyword_true(self):
        return "".join([c.upper() if i in self[pair_data.KEYWORD_UPPER_INDEX] else c for i, c in enumerate(self[pair_data.KEYWORD])])

    @property
    def reply(self):
        return self[pair_data.REPLY]

    @property
    def reply_upper_index(self):
        return self[pair_data.REPLY_UPPER_INDEX]

    @property
    def reply_true(self):
        return "".join([c.upper() if i in self[pair_data.REPLY_UPPER_INDEX] else c for i, c in enumerate(self[pair_data.REPLY])])

    @property
    def reply_attach_text(self):
        return self[pair_data.PROPERTIES][pair_data.REPLY_ATTACH_TEXT]

    @property
    def disabled(self):
        return self[pair_data.PROPERTIES][pair_data.DISABLED]

    @property
    def pinned(self):
        return self[pair_data.PROPERTIES][pair_data.PINNED]

    @property
    def keyword_type(self):
        return self[pair_data.PROPERTIES][pair_data.KEYWORD_TYPE]

    @property
    def reply_type(self):
        return self[pair_data.PROPERTIES][pair_data.REPLY_TYPE]

    @property
    def linked_words(self):
        """Always not none, length will be 0 if nothing inside(empty array)."""
        return self[pair_data.PROPERTIES][pair_data.LINKED_WORDS]

    @property
    def created_time(self):
        return self[pair_data.STATISTICS][pair_data.CREATED_TIME]

    @property
    def creator(self):
        return self[pair_data.STATISTICS][pair_data.CREATOR]

    @property
    def disabled_time(self):
        return self[pair_data.STATISTICS][pair_data.DISABLED_TIME]

    @property
    def disabler(self):
        return self[pair_data.STATISTICS][pair_data.DISABLER]

    @property
    def last_call(self):
        return self[pair_data.STATISTICS][pair_data.LAST_CALL]

    @property
    def call_count(self):
        return self[pair_data.STATISTICS][pair_data.CALLED_COUNT]
    
    def basic_text(self, display_status=False):
        kw = group_dict_manager._keyword_repr(self, False)
        rep = group_dict_manager._reply_repr(self, False)
        rep_att = u'(無)' if self.reply_attach_text is None else self.reply_attach_text
        linked = u'、'.join(self.linked_words) if len(self.linked_words) > 0 else None
        affil_group = self.affiliated_group
        if affil_group == PUBLIC_GROUP_ID:
            affil_group = u'公用'
        
        if display_status:
            status = u''
            if self.pinned:
                status += u' (置頂)'
            if self.disabled:
                status += u' (失效)'
        else:
            status = u''

        text = u'#{}{}'.format(self.seq_id, status)
        text += u'\n關鍵字內容: {}{}'.format(u'\n' if u'\n' in kw else u'', kw)
        text += u'\n回覆內容: {}{}'.format(u'\n' if u'\n' in rep else u'', rep)
        if self.reply_type == word_type.PICTURE or self.reply_type == word_type.STICKER:
            text += u'\n附加回覆: {}'.format(rep_att)
        if linked is not None:
            text += u'\n相關關鍵字: {}'.format(linked)
        text += u'\n隸屬群組: {}'.format(affil_group)

        return text

    def detailed_text(self, include_basic=True, line_api_wrapper=None, kwd_mgr=None):
        def format_line_profile_with_time(action_str, uid, timestamp):
            text = u''

            if line_api_wrapper is not None:
                profile = line_api_wrapper.profile(uid)
                if profile is None:
                    name = error.main.line_account_data_not_found()
                else:
                    name = profile.display_name

                text += u'{}者LINE名稱: {}'.format(action_str, name)

            text += u'\n{}者LINE UUID: {}'.format(action_str, line_api_wrapper.acquire_uid(uid))

            if timestamp is not None:
                text += u'\n{}時間: {}'.format(action_str, timestamp + timedelta(hours=8))

            return text

        word_ranking = u''
        if kwd_mgr is not None:
            rank_result = kwd_mgr.rank_of_used_count(self.call_count)
            if isinstance(rank_result, (int, long)):
                word_ranking = u' (第{}名)'.format(rank_result)

        detailed = u''
        if include_basic:
            detailed += self.basic_text() + u'\n'

        detailed += u'[ {} ] [ {} ]\n'.format(u'置頂' if self.pinned else u'-', u'失效' if self.disabled else u'-')
        detailed += u'呼叫次數: {}{}\n'.format(self.call_count, word_ranking)
        if self.last_call is not None:
            detailed += u'最後呼叫: {}\n'.format(self.last_call + timedelta(hours=8))
        detailed += format_line_profile_with_time(u'製作', self.creator, self.created_time)

        if self.disabled:
            detailed += u'\n'
            detailed += format_line_profile_with_time(u'刪除', self.disabler, self.disabled_time)

        return detailed

    def clone(self, new_group_id):
        new = dict(self)

        new[pair_data.AFFILIATED_GROUP] = new_group_id
        new[pair_data.PROPERTIES][pair_data.DISABLED] = False
        new[pair_data.STATISTICS][pair_data.DISABLED_TIME] = None
        new[pair_data.STATISTICS][pair_data.DISABLER] = None
        new[pair_data.STATISTICS][pair_data.LAST_CALL] = None
        new[pair_data.STATISTICS][pair_data.CALLED_COUNT] = 0

        return new

class PairCreatorRankingResult(list):
    def __init__(self, org_list):
        super(PairCreatorRankingResult, self).__init__([PairCreatorRankingData(data_dict) for data_dict in org_list])

class PairCreatorRankingData(dict_like_mapping):
    """
    {
        creator_uid: STRING,
        created_count: INTEGER,
        used_count: INTEGER,
        used_count_avg: FLOAT
    }
    """
    COLLECTION_NAME = 'PairCreatorRanking'

    UID_REF = 'uref'
    PAIR_COUNT = 'p_c'
    PAIR_USED_COUNT = 'p_uc'
    CREATED_PAIR_SEQ = 'p_seq'
    AVG_USED_COUNT = 'avg'
    ACTIVITY_POINT = 'pt'

    def __init__(self, org_dict):
        if org_dict is not None:
            if all(k in org_dict for k in (PairCreatorRankingData.PAIR_COUNT, PairCreatorRankingData.PAIR_USED_COUNT, PairCreatorRankingData.UID_REF, 
                                           PairCreatorRankingData.AVG_USED_COUNT, PairCreatorRankingData.CREATED_PAIR_SEQ, PairCreatorRankingData.ACTIVITY_POINT)):
                pass
            else:
                raise ValueError('Incomplete result dictionary of creator ranking.')
        else:
            raise ValueError('dictionary to create PairCreatorRankingResult is None.')

        super(PairCreatorRankingData, self).__init__(org_dict)

    @property
    def creator_uid_ref(self):
        return self[PairCreatorRankingData.UID_REF]
    
    @property
    def created_pair_count(self):
        return self[PairCreatorRankingData.PAIR_COUNT]
    
    @property
    def created_pair_used_count(self):
        return self[PairCreatorRankingData.PAIR_USED_COUNT]
    
    @property
    def created_pair_avg_used_count(self):
        return self[PairCreatorRankingData.AVG_USED_COUNT]
    
    @property
    def created_pair(self):
        return self[PairCreatorRankingData.CREATED_PAIR_SEQ]
    
    @property
    def activity_point(self):
        return self[PairCreatorRankingData.ACTIVITY_POINT]

class KeywordDictionaryStatistics(dict_like_mapping):
    PAIR_COUNT = 'pair_ct'
    PAIR_COUNT_DISABLED = 'pair_ct_d'
    PAIR_COUNT_BY_KEYWORD_TYPE = 'pair_ct_kw'
    PAIR_COUNT_BY_REPLY_TYPE = 'pair_ct_rep'

    USED_COUNT = 'used_ct'

    CREATED_IN_DAYS = 'ct_d'

    def __init__(self):
        init_dict = {
            KeywordDictionaryStatistics.PAIR_COUNT: 0,
            KeywordDictionaryStatistics.PAIR_COUNT_DISABLED: 0,
            KeywordDictionaryStatistics.USED_COUNT: 0,
            KeywordDictionaryStatistics.PAIR_COUNT_BY_KEYWORD_TYPE: None,
            KeywordDictionaryStatistics.PAIR_COUNT_BY_REPLY_TYPE: None,
            KeywordDictionaryStatistics.CREATED_IN_DAYS: CreatedInDaysData.init_by_field()
        }

        super(KeywordDictionaryStatistics, self).__init__(init_dict)

    @property
    def pair_count(self):
        return self[KeywordDictionaryStatistics.PAIR_COUNT]

    @pair_count.setter
    def pair_count(self, value):
        self[KeywordDictionaryStatistics.PAIR_COUNT] = value

    @property
    def pair_count_disabled(self):
        return self[KeywordDictionaryStatistics.PAIR_COUNT_DISABLED]

    @pair_count_disabled.setter
    def pair_count_disabled(self, value):
        self[KeywordDictionaryStatistics.PAIR_COUNT_DISABLED] = value

    @property
    def usable_rate(self):
        try:
            return 1.0 - self[KeywordDictionaryStatistics.PAIR_COUNT_DISABLED] / float(self[KeywordDictionaryStatistics.PAIR_COUNT])
        except ZeroDivisionError:
            return 0.0

    @property
    def used_count(self):
        return self[KeywordDictionaryStatistics.USED_COUNT]

    @used_count.setter
    def used_count(self, value):
        self[KeywordDictionaryStatistics.USED_COUNT] = value

    @property
    def avg(self):
        try:
            return self[KeywordDictionaryStatistics.USED_COUNT] / float(self[KeywordDictionaryStatistics.PAIR_COUNT])
        except ZeroDivisionError:
            return 0.0

    @property
    def keyword_type_count(self):
        return self[KeywordDictionaryStatistics.PAIR_COUNT_BY_KEYWORD_TYPE]

    @keyword_type_count.setter
    def keyword_type_count(self, value):
        self[KeywordDictionaryStatistics.PAIR_COUNT_BY_KEYWORD_TYPE] = PairTypeCountData(value)

    @property
    def reply_type_count(self):
        return self[KeywordDictionaryStatistics.PAIR_COUNT_BY_REPLY_TYPE]

    @reply_type_count.setter
    def reply_type_count(self, value):
        self[KeywordDictionaryStatistics.PAIR_COUNT_BY_REPLY_TYPE] = PairTypeCountData(value)

    @property
    def created_in_days(self):
        return self[KeywordDictionaryStatistics.CREATED_IN_DAYS]

    @created_in_days.setter
    def created_in_days(self, value):
        self[KeywordDictionaryStatistics.CREATED_IN_DAYS] = CreatedInDaysData(value)

class PairTypeCountData(dict_like_mapping):
    def __init__(self, org_dict):
        return super(PairTypeCountData, self).__init__(org_dict)

    def get_value(self, enum_type):
        return self[str(int(enum_type))]

    def get_values(self):
        return [self[key] for key in sorted(self)]

class CreatedInDaysData(dict_like_mapping):
    IN_1DAY = 'd1'
    IN_3DAYS = 'd3'
    IN_7DAYS = 'd7'
    IN_15DAYS = 'd15'

    @staticmethod
    def init_by_field(in_1=0, in_3=0, in_7=0, in_15=0):
        init_dict = {
            CreatedInDaysData.IN_1DAY: in_1,
            CreatedInDaysData.IN_3DAYS: in_3,
            CreatedInDaysData.IN_7DAYS: in_7,
            CreatedInDaysData.IN_15DAYS: in_15
        }

        return CreatedInDaysData(init_dict)
    
    def __init__(self, org_dict):
        if not all(k in org_dict for k in (CreatedInDaysData.IN_1DAY, CreatedInDaysData.IN_3DAYS, CreatedInDaysData.IN_7DAYS, CreatedInDaysData.IN_15DAYS)):
            raise ValueError(u'Incomplete data. {}'.format(org_dict))

        super(CreatedInDaysData, self).__init__(org_dict)

    @property
    def in_1day(self):
        return self[CreatedInDaysData.IN_1DAY]
    
    @property
    def in_3days(self):
        return self[CreatedInDaysData.IN_3DAYS]
    
    @property
    def in_7days(self):
        return self[CreatedInDaysData.IN_7DAYS]
    
    @property
    def in_15days(self):
        return self[CreatedInDaysData.IN_15DAYS]

    def get_string(self):
        return u'1天內 {} | 3天內 {} | 7天內 {} | 15天內 {}'.format(
            self[CreatedInDaysData.IN_1DAY], self[CreatedInDaysData.IN_3DAYS], self[CreatedInDaysData.IN_7DAYS], self[CreatedInDaysData.IN_15DAYS])
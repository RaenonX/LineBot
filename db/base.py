# -*- coding: utf-8 -*-

import pymongo

from collections import MutableMapping

SYSTEM_DATABASE_NAME = 'sys'

class db_base(pymongo.collection.Collection):
    COLLECTION_NAME = '_id'
    SEQUENCE = '_seq'
    NOT_EXIST_SEQ_ID = -1

    def __init__(self, mongo_client, db_name, collection_name, has_seq, index_col_list=None, codec_options=None, read_preference=None, write_concern=None, read_concern=None, **kwargs):
        self._has_seq = has_seq
        self._db_name = db_name
        self._collection_name = collection_name

        self._db = mongo_client.get_database(self._db_name)
        super(db_base, self).__init__(self._db, collection_name, False, codec_options, read_preference, write_concern, read_concern, **kwargs)

        if index_col_list is None:
            index_col_list = []
        else:
            index_col_list = list(index_col_list)

        if not isinstance(index_col_list, (list, tuple)):
            raise ValueError('Column to make index must be list or tuple.')
        
        if collection_name not in self._db.collection_names() and has_seq:
            self._db.counter.insert({ db_base.COLLECTION_NAME: collection_name, db_base.SEQUENCE: 0 })

        if has_seq:
            index_col_list.append(db_base.SEQUENCE)
            
        if len(index_col_list) > 0:
            self.create_index([(column, pymongo.DESCENDING) for column in index_col_list], unique=True)

    def create_index(self, keys, **kwargs):
        print 'MongoDB CREATE_INDEX @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).create_index(keys, **kwargs)

    def insert(self, doc_or_docs, manipulate=True, check_keys=True, continue_on_error=False, **kwargs):
        print 'MongoDB INSERT @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).insert(doc_or_docs, manipulate, check_keys, continue_on_error, **kwargs)

    def insert_one(self, document, bypass_document_validation=False):
        print 'MongoDB INSERT_ONE @{}.{}'.format(self._db_name, self._collection_name)

        inserted_seq_id = db_base.NOT_EXIST_SEQ_ID

        if self._has_seq:
            if db_base.SEQUENCE in document:
                raise ValueError('Remove _seq field to add sequence id.')

            document[db_base.SEQUENCE] = self._next_seq()
            inserted_seq_id = document[db_base.SEQUENCE]

        result = super(db_base, self).insert_one(document, bypass_document_validation)
        
        return ExtendedInsertOneResult(result.inserted_id, result.acknowledged, inserted_seq_id)

    def insert_many(self, documents, ordered=True, bypass_document_validation=False):
        print 'MongoDB INSERT_MANY @{}.{}'.format(self._db_name, self._collection_name)

        inserted_seq_ids = []

        if any(db_base.SEQUENCE in document for document in documents):
            raise ValueError('Remove _seq field in data to add sequence id.')

        if self._has_seq:
            seq_ids = self._next_seq_array(len(documents))
            for document, seq_id in zip(documents, seq_ids):
                document[db_base.SEQUENCE] = seq_id
        else:
            seq_ids = [db_base.NOT_EXIST_SEQ_ID for i in range(len(documents))]

        result = super(db_base, self).insert_many(documents, ordered, bypass_document_validation)
        
        return ExtendedInsertManyResult(result.inserted_ids, result.acknowledged, seq_ids)

    def find(self, *args, **kwargs):
        print 'MongoDB FIND @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).find(*args, **kwargs)

    def find_one(self, filter=None, *args, **kwargs):
        print 'MongoDB FIND_ONE @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).find_one(filter, *args, **kwargs)

    def find_one_and_replace(self, filter, replacement, projection = None, sort = None, upsert = False, return_document = pymongo.ReturnDocument.BEFORE, **kwargs):
        print 'MongoDB FIND_ONE_AND_REPLACE @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).find_one_and_replace(filter, replacement, projection, sort, upsert, return_document, **kwargs)

    def find_one_and_update(self, filter, update, projection=None, sort=None, upsert = False, return_document = pymongo.ReturnDocument.BEFORE, **kwargs):
        print 'MongoDB FIND_ONE_AND_UPDATE @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).find_one_and_update(filter, update, projection, sort, upsert, return_document, **kwargs)

    def update_one(self, filter, update, upsert = False, bypass_document_validation = False, collation = None):
        print 'MongoDB UPDATE_ONE @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).update_one(filter, update, upsert, bypass_document_validation, collation)
    
    def update_many(self, filter, update, upsert = False, array_filters = None, bypass_document_validation = False, collation = None, session = None):
        print 'MongoDB UPDATE_MANY @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).update_many(filter, update, upsert, array_filters, bypass_document_validation, collation, session)

    def delete_one(self, filter, collation = None):
        print 'MongoDB DELETE_ONE @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).delete_one(filter, collation)

    def delete_many(self, filter, collation = None):
        print 'MongoDB DELETE_MANY @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).delete_many(filter, collation)

    def aggregate(self, pipeline, **kwargs):
        print 'MongoDB AGGREGATE @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).aggregate(pipeline, **kwargs)

    def count(self, filter = None, **kwargs):
        print 'MongoDB COUNT @{}.{}'.format(self._db_name, self._collection_name)

        return super(db_base, self).count(filter, **kwargs)


    def drop(self):
        print 'MongoDB DROP @{}.{}'.format(self._db_name, self._collection_name)
        self._db.counter.delete_many({ '_id': self._collection_name })
        return super(db_base, self).drop()

    def cursor_limit(self, cursor, limit=None, limit_default=None):
        """Return splitted cursor."""
        if (isinstance(limit, (int, long)) ^ (limit is None)) and (isinstance(limit_default, (int, long)) ^ (limit_default is None)):
            if limit is not None:
                return cursor.limit(limit)
            elif limit_default is not None:
                return cursor.limit(limit_default)
            else:
                return cursor
        else:
            raise ValueError('Either limit default and limit must be integer or None to present "not set".')


    def _next_seq(self):
        ret = self._next_seq_array(1)
        return ret[0]

    def _next_seq_array(self, length=1):
        print 'MongoDB (Update Sequence Number of {}.{})'.format(self._db_name, self._collection_name)
        ret = self._db.counter.find_one_and_update({ db_base.COLLECTION_NAME: self.name }, { '$inc': { db_base.SEQUENCE: length }}, None, None, True, pymongo.ReturnDocument.BEFORE)
        if ret is not None:
            new_seq_begin = ret[db_base.SEQUENCE] + 1
        else:
            new_seq_begin = length

        return [i for i in range(new_seq_begin, new_seq_begin + length)]

class dict_like_mapping(MutableMapping):
    def __init__(self, org_dict):
        if org_dict is None:
            self._dict = {}
        else:
            self._dict = dict(org_dict)

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return str(self._dict)

class ExtendedInsertOneResult(pymongo.results.InsertOneResult):
    def __init__(self, inserted_id, acknowledged, seq_id=None):
        if seq_id is None:
            self._seq_id = db_base.NOT_EXIST_SEQ_ID
        else:
            self._seq_id = seq_id

        super(ExtendedInsertOneResult, self).__init__(inserted_id, acknowledged)

    @property
    def inserted_seq_id(self):
        return self._seq_id

class ExtendedInsertManyResult(pymongo.results.InsertManyResult):
    def __init__(self, inserted_ids, acknowledged, inserted_seq_ids=None):
        if inserted_seq_ids is None:
            self._seq_ids = [db_base.NOT_EXIST_SEQ_ID for i in range(len(inserted_ids))]
        else:
            self._seq_ids = inserted_seq_ids
            
        return super(ExtendedInsertManyResult, self).__init__(inserted_ids, acknowledged)

    @property
    def inserted_seq_ids(self):
        return self._seq_ids

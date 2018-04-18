# -*- coding: utf-8 -*-
from __future__ import division

MONGO_URI = 'MONGO'

MONGO_ATLAS_API_KEY = 'MONGO_ATLAS_API_KEY'

PROJ_GROUP_ID = 'PROJ_GROUP_ID'
CLUSTER_NAME = 'CLUSTER_NAME'

import pymongo

import time
import requests

import tool
import json

import db

mc = pymongo.MongoClient(MONGO_URI)

uid_ref = db.user_id_ref_manager(mc)

col = mc.get_database("DB").get_collection("COL")

def a():
    print("Backing up original...")

    pipeline = [ {"$match": {}}, 
                 {"$out": "COL_backup"},
    ]
    col.aggregate(pipeline)
    print("Backup completed.")
    
    print("Getting distincted uids...")
    uids = col.distinct(db.sc_gen_data.USER_ID)
    print("Got distincted uids.")

    print("Generating reference id of uids...")
    ref = { uid: uid_ref.get_ref_id_or_record(uid) for uid in uids }
    print("Reference id of uids generated.")

    print("Updating user ids...")
    for uid, ref_id in ref.items():
        print("Replacing...{} to REF #{}".format(uid, ref_id))
        col.update_many({ db.sc_gen_data.USER_ID: uid }, { "$set": { db.sc_gen_data.USER_ID: ref_id } })

def b():
     mc.get_database("DB").get_collection("COL_backup").rename("COL")

if __name__ == "__main__":
    _start = time.time()

    a()

    print("Executed in {:.5f} secs".format(time.time() - _start))

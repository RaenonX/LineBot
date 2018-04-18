# -*- coding: utf-8 -*-
MONGO_URI = 'MONGO_URI'

import pymongo
import bson

mongo = pymongo.MongoClient(MONGO_URI)

def a():
    with open("D:/UserData/Desktop/data_to_review.csv", mode="w") as f:
        for i, data in enumerate(mongo.word_dict.word_dict.find({ "$or": [{"prop.kw_type": {"$not": {"$in": [0, 1]}}}, 
                                                                          {"prop.rep_type": {"$not": {"$in": [0, 1]}}},
                                                                          {"kw": {"$regex": ".*://.*"}},
                                                                          {"rep": {"$regex": ".*://.*"}}], 
                                                                 "prop.dis": False,
                                                                 "_seq": { "$gt": 3724} })):
            print("Writing...{}".format(i))
            f.write(u"{},{},{}".format(data["_seq"], data["kw"].replace("\n", "\\n"), data["rep"].replace("\n", "\\n")).encode("utf-8"))
            f.write("\n")

def b():
    for i, data in enumerate(mongo.word_dict.word_dict.find()):
        print("Writing...{}".format(i))
        mongo.word_dict.word_dict.update({ "_id": data["_id"] }, { "$set": { "kw_l": data["kw"].lower(), "rep_l": data["rep"].lower() } })

def c():
    print([i for i, c in enumerate("SSsS") if c.isupper()])

def d():
    def upper_index(str):
        return [i for i, c in enumerate(unicode(str)) if c.isupper()]

    print("Backing up original...")
    pipeline = [ {"$match": {}}, 
                 {"$out": "word_dict_backup_201803252309_org"},
    ]
    mongo.word_dict.word_dict.aggregate(pipeline)
    
    count = 0
    with open("data_fixed_final.csv", mode="r") as f:
        line = f.readline()
        while line:
            count += 1
            seq, kw, rep = line.split(",", 2)

            print("Fixing...{} (Seq ID #{})".format(count, int(seq)))
            update_result = mongo.word_dict.word_dict.update_one({ "_seq": int(seq) }, { "$set": { "kw": kw.replace("\\n", "\n"), "rep": rep.replace("\\n", "\n") }})

            if update_result.matched_count != 1:
                print("matched count: {}".format(update_result.matched_count))
                print("modified count: {}".format(update_result.modified_count))
                print("seq: {} | kw: {} | rep: {}".format(seq, kw, rep))
                input()

            line = f.readline()

    print("Backing up recovered...")
    pipeline = [ {"$match": {}}, 
                 {"$out": "word_dict_backup_201803252309_rcv"},
    ]
    mongo.word_dict.word_dict.aggregate(pipeline)

    for i, data in enumerate(mongo.word_dict.word_dict.find()):
        print("Writing...{}".format(i))
        mongo.word_dict.word_dict.update({ "_id": data["_id"] }, { "$set": { "kw_i": upper_index(data["kw"]), 
                                                                             "rep_i": upper_index(data["rep"]),
                                                                             "kw": data["kw"].replace("\\n", "\n").lower(),
                                                                             "rep": data["rep"].replace("\\n", "\n").lower() } })

    print("Backing up repaired...")
    pipeline = [ {"$match": {}}, 
                 {"$out": "word_dict_backup_201803252309_rpr"},
    ]
    mongo.word_dict.word_dict.aggregate(pipeline)

    return mongo.word_dict.word_dict.update({}, {"$unset": {"kw_l":1, "rep_l":1}}, multi=True)



if __name__ == "__main__":
    a()
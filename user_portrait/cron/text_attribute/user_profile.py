# -*- coding: UTF-8 -*-
'''
acquire the profile information from user_profile
input: uid_list
output: {uid:{attr:value}}
'''
import sys
import json
reload(sys)
sys.path.append('../../')
from global_utils import es_user_profile as es

fields_dict = {'uname':"nick_name", 'gender':"sex", 'location':"user_location", \
               'verified':"isreal", 'fansnum':"fansnum", 'statusnum':"statusnum", \
               'friendsnum':"friendsnum", 'photo_url':"photo_url"}

index_name = 'weibo_user'
index_type = 'user'

def get_profile_information(uid_list):
    result_dict = dict()
    search_result = es.mget(index=index_name, doc_type=index_type, body={'ids':uid_list}, _source=True)['docs']
    print 'search_result:', search_result
    for item in search_result:
        user_dict = {}
        for field in fields_dict:
            user_dict[field] = item['_source'][fields_dict[field]]

        result_dict[item['_id']] = user_dict
    print 'result_dict:', result_dict

if __name__=="__main__":
    test_uid = ['2635896591', '2234766704']
    get_profile_information(test_uid)



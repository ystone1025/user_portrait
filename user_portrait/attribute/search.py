# -*- coding: UTF-8 -*-
'''
search attribute : attention, follower, mention, location, activity
'''
import IP
import sys
import csv
import time
import json
import redis
sys.path.append('../../')
from user_portrait.time_utils import ts2datetime, datetime2ts
from user_portrait.global_utils import R_CLUSTER_FLOW2 as r_cluster
from user_portrait.global_utils import R_DICT
from user_portrait.global_utils import es_user_portrait
from user_portrait.search_user_profile import search_uid2uname

#search:'retweet_'+uid return attention {r_uid1:count1, r_uid2:count2...}
#redis:{'retweet_'+uid:{ruid:count}}
#return results: {ruid:[uname,count]}
def search_attention(uid):
    stat_results = dict()
    results = dict()
    for db_num in R_DICT:
        r = R_DICT[db_num]
        ruid_results = r.hgetall('retweet_'+str(uid))
        if ruid_results:
            for ruid in ruid_results:
                try:
                    stat_results[ruid] += ruid_results[ruid]
                except:
                    stat_results[ruid] = ruid_results[ruid]
    # print 'results:', stat_results
    for ruid in stat_results:
        # search uid
        '''
        uname = search_uid2uname(ruid)
        if not uname:
        '''
        uname = '未知'
        
        count = stat_results[ruid]
        results[ruid] = [uname, count]
    if results:    
        return results
    else:
        return None

#search:'be_retweet_' + str(uid) return followers {br_uid1:count1, br_uid2:count2}
#redis:{'be_retweet_'+uid:{br_uid:count}}
#return results:{br_uid:[uname, count]}
def search_follower(uid):
    results = dict()
    stat_results = dict()
    for db_num in R_DICT:
        r = R_DICT[db_num]
        br_uid_results = r.hgetall('be_retweet_'+str(uid))
        #print 'br_uid_results:', br_uid_results
        if br_uid_results:
            for br_uid in br_uid_results:
                try:
                    stat_results[br_uid] += br_uid_results[br_uid]
                except:
                    stat_results[br_uid] = br_uid_results[br_uid]
    # print 'stat_results:', stat_results
    for br_uid in stat_results:
        # search uid
        '''
        uname = search_uid2uname(br_uid)
        if not uname:
        '''
        uname = '未知'
        
        count = stat_results[br_uid]
        results[br_uid] = [uname, count]
    if results:
        return results
    else:
        return None

#search:now_ts , uid return 7day at uid list  {uid1:count1, uid2:count2}
#{'at_'+Date:{str(uid):'{at_uid:count}'}}
#return results:{at_uid:[uname,count]}
def search_mention(now_ts, uid):
    date = ts2datetime(now_ts)
    ts = datetime2ts(date)
    #print 'at date-ts:', ts
    stat_results = dict()
    results = dict()
    for i in range(1,8):
        ts = ts - 24 * 3600
        result_string = r_cluster.hget('at_' + str(ts), str(uid))
        if not result_string:
            continue
        result_dict = json.loads(result_string)
        for at_uid in result_dict:
            try:
                stat_results[at_uid] += result_dict[at_uid]
            except:
                stat_results[at_uid] = result_dict[at_uid]
    
    for at_uid in stat_results:
        # search uid
        '''
        uname = search_uid2uname(at_uid)
        if not uname:
        '''    
        uname = '未知'
        count = stat_results[at_uid]
        results[at_uid] = [uname, count]
    if results:
        return results
    else:
        return None

#search:now_ts, uid return 7day loaction list {location1:count1, location2:count2}
#{'ip_'+str(Date_ts):{str(uid):'{city:count}'}
# return results: {city:{ip1:count1,ip2:count2}}
def search_location(now_ts, uid):
    date = ts2datetime(now_ts)
    #print 'date:', date
    ts = datetime2ts(date)
    #print 'date-ts:', ts
    stat_results = dict()
    results = dict()
    for i in range(1, 8):
        ts = ts - 24 * 3600
        #print 'for-ts:', ts
        result_string = r_cluster.hget('ip_' + str(ts), str(uid))
        if not result_string:
            continue
        result_dict = json.loads(result_string)
        for ip in result_dict:
            try:
                stat_results[ip] += result_dict[ip]
            except:
                stat_results[ip] = result_dict[ip]
    for ip in stat_results:
        city = ip2city(ip)
        if city:
            try:
                results[city][ip] = stat_results[ip]
            except:
                results[city] = {ip: stat_results[ip]}
                
    print 'location results:', results
    return results

#search: now_ts, uid return 7day activity trend list {time_segment:weibo_count}
# redis:{'activity_'+Date:{str(uid): '{time_segment: weibo_count}'}}
# return :{time_segment:count}
def search_activity(now_ts, uid):
    date = ts2datetime(now_ts)
    #print 'date:', date
    ts = datetime2ts(date)
    #print 'date-ts:', ts
    results = dict()
    for i in range(1, 8):
        ts = ts - 24 * 3600
        #print 'for-ts:', ts
        result_string = r_cluster.hget('activity_' + str(ts), str(uid))
        #print 'activity:', result_string
        if not result_string:
            continue
        result_dict = json.loads(result_string)
        for time_segment in result_dict:
            try:
                results[time_segment] += result_dict[time_segment]
            except:
                results[time_segment] = result_dict[time_segment]
                
    return results

# ip to city
def ip2city(ip):
    try:
        city = IP.find(str(ip))
        if city:
            city = city.encode('utf-8')
        else:
            return None
    except Exception,e:
        return None
    return city

#use to search user_portrait to show the attribute saved in es_user_portrait
def search_attribute_portrait(uid):
    results = dict()
    index_name = 'user_portrait'
    index_type = 'user'
    try:
        results = es_user_portrait.get(index=index_name, doc_type=index_type, id=uid)['_source']
    except:
        results = None
    return results

#use to search user_portrait by lots of condition 
def search_portrait(condition_num, query, sort, size):
    user_result = []
    index_name = 'user_portrait'
    index_type = 'user'
    if condition_num > 0:
        try:
            result = es_user_portrait.search(index=index_name, doc_type=index_type, \
                    body={'query':{'bool':{'must':query}}, 'sort':sort, 'size':size})['hits']['hits']
        except Exception,e:
            raise e
    else:
        result = es_user_portrait.search(index=index_name, doc_type=index_type, \
                body={'query':{'match_all':{}}, 'sort':[{'statusnum':{'order':'desc'}}],\
                     'size':100})['hits']['hits']
    if result:
        #print 'result:', result
        for item in result:
            user_dict = item['_source']
            user_result.append([user_dict['uid'], user_dict['uname'], user_dict['fansnum'], user_dict['statusnum'], user_dict['friendsnum']])

    return user_result


if __name__=='__main__':
    uid = '1798289842'
    now_ts = 1377964800 + 3600 * 24 * 4
    
    results1 = search_attention(uid)
    print 'attention:', results1
    results2 = search_follower(uid)
    print 'follow:', results2
    results3 = search_mention(now_ts, uid)
    print 'at_user:', results3 
    results4 = search_location(now_ts, uid)
    print 'location:', results4
    results5 = search_activity(now_ts, uid)
    print 'activity:', results5

    

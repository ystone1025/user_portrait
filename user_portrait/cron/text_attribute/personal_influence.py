# -*-coding:utf-8 -*-
import sys
import json
import redis
from elasticsearch import Elasticsearch
from influence_appendix import aggregation, proportion
reload(sys)
sys.path.append('./../../')
from global_utils import ES_CLUSTER_FLOW1 as es_cluster
from global_utils import es_user_profile as es_profile
from global_utils import es_user_portrait as es_user_portrait
from influence_conclusion import retweeted_threshould, comment_threshould, influence_tag
user_portrait = "user_portrait"
es = Elasticsearch("219.224.135.93:9206", timeout=60)
index_name = "bci_20130907"
index_flow_text = "flow_text_2013-09-01"


def get_text(top_list):

# input: [[mid1, no.1], [mid2, no.2], ['mid3', no.3]]
# output: [[text1, no.1], [text2, no.2], [text3, no.3]]

    if int(top_list[0][0]) != 0: # no one
        mid_list = ["0", "0", "0"]
        for i in range(len(top_list)):
            mid_list[i] = top_list[i][0]
        search_result = es.mget(index=index_flow_text, doc_type="text", body={"ids":mid_list}, fields="text")["docs"]
        for i in range(len(top_list)):
            if search_result[i]["found"]:
                top_list[i][0] = search_result[i]["fields"]["text"][0]
            else:
                top_list[i][0] = ""

    return top_list



# top retweeted or commentted weibo context
# date: 20130901
# uid
# return context and number 
def influenced_detail(uid, date):

    detail_text = {}
    try:
        user_info = es_cluster.get(index=index_name, doc_type="bci", id=uid)["_source"]
    except:
        return json.dumps({})
    origin_retweetd = json.loads(user_info["origin_weibo_retweeted_top"])
    origin_comment = json.loads(user_info['origin_weibo_comment_top'])
    retweeted_retweeted = json.loads(user_info["retweeted_weibo_retweeted_top"])
    retweeted_comment = json.loads(user_info["retweeted_weibo_comment_top"])

    detail_text["origin_retweeted"] = get_text(origin_retweetd)
    detail_text["origin_comment"] = get_text(origin_comment)
    detail_text["retweeted_retweeted"] = get_text(retweeted_retweeted)
    detail_text["retweeted_comment"] = get_text(retweeted_comment)

    return json.dumps(detail_text)



def influenced_people(uid, mid, influence_style, default_number=20):
# uid 
# which weibo----mid, retweeted weibo ---seek for root_mid
# influence_style: retweeted(0) or comment(1)
    results = {}
    query_body = {
        "query":{
            "filtered":{
                "filter":{
                    "bool":{
                        "must":[
                            {"term": {"root_mid": mid}}
                        ]
                    }
                }
            }
        },
        "size": 100000
    }

    if int(influence_style) == 0: # origin weibo, all retweeted people
        query_body["query"]["filtered"]["filter"]["bool"]["must"].extend([{"term": {"directed_uid": uid}}, {"term": {"message_type": 3}}])
    else: # commented people
        query_body["query"]["filtered"]["filter"]["bool"]["must"].extend([{"term": {"directed_uid": uid}}, {"term": {"message_type": 2}}])
    search_results = es.search(index=index_flow_text, doc_type="text", body=query_body, fields=["uid"], timeout=30)["hits"]["hits"]
    print search_results
    if len(search_results) == 0:
        return json.dumps([[],[]])
    results = []
    for item in search_results:
        results.append(item["fields"]["uid"][0])

    portrait_results = es_user_portrait.mget(index="user_portrait", doc_type="user", body={"ids": results}, fields=["importance","uid"])["docs"]
    in_portrait = {}
    out_portrait = []
    print portrait_results
    for item in portrait_results:
        if item["found"]:
            in_portrait[item["fields"]["uid"][0]] = item["fields"]["importance"][0]
        else:
            out_portrait.append(item['_id'])
    in_portrait = sorted(in_portrait.items(), key=lambda x:x[1], reverse=True)


    return json.dumps([in_portrait[:default_number], out_portrait[:default_number]])

def influenced_user_detail(query_body, origin_retweeted_mid, retweeted_retweeted_mid, message_type):
    #详细影响到的人 
    origin_retweeted_uid = [] # influenced user uid_list
    retweeted_retweeted_uid = []
    origin_comment_uid = []
    retweeted_comment_uid = []
    if origin_retweeted_mid: # 所有转发该条原创微博的用户
        for iter_mid in origin_retweeted_mid:
            query_body["query"]["filtered"]["filter"]["bool"]["should"].append({"term": {"root_mid": iter_mid}})
        query_body["query"]["filtered"]["filter"]["bool"]["must"] = [{"message_type": message_type}, {"root_uid": uid}]
        origin_retweeted_result = es.search(index=index_flow_text, doc_type="text", body=query_body)["hits"]["hits"]
        print origin_retweeted_result
        if origin_retweeted_result:
            for item in origin_retweeted_result:
                origin_retweeted_uid.append(item["fields"]["uid"][0])
    if retweeted_retweeted_mid: # 所有评论该条原创微博的用户
        for iter_mid in retweeted_retweeted_mid:
            query_body["query"]["filtered"]["filter"]["bool"]["should"].append({"term": {"root_mid": iter_mid}})
        query_body["query"]["filtered"]["filter"]["bool"]["must"].extend([{"term":{"message_type": message_type}},{"term": {"directed_uid": uid}}])
        retweeted_retweeted_result = es.search(index=index_flow_text, doc_type="text", body=query_body)["hits"]["hits"]
        print retweeted_retweeted_result
        if retweeted_retweeted_result:
            for item in retweeted_retweeted_result:
                retweeted_retweeted_uid.append(item["fields"]["uid"][0])
    retweeted_uid_list = [] # all retweeted user list
    retweeted_results = {} # statistics of all retweeted uid information
    retweeted_domain = {}
    retweeted_topic = {}
    retweeted_geo = {}
    average_influence = 0
    total_influence = 0
    count = 0
    retweeted_uid_list.extend(origin_retweeted_uid)
    retweeted_uid_list.extend(retweeted_retweeted_uid)
    if retweeted_uid_list:
        user_portrait_result = es_user_portrait.mget(index=user_portrait, doc_type="user", body={"ids": retweeted_uid_list}, fields=["domain", "topici_string", "activity_geo", "influence"])["docs"]
        for item in user_portrait_result:
            if item["found"]:
                count += 1
                temp_domain = item["fields"]["domain"][0].split('&')
                temp_topic = item["fields"]["topic_string"][0].split('&')
                temp_geo = item["fields"]["activity_geo"][0].split('&')
                total_influence += item["fields"]["influence"][0]
                retweeted_domain = aggregation(temp_domain, retweeted_domain)
                retweeted_topic = aggregation(temp_topic, retweeted_topic)
                retweeted_geo = aggregation(temp_geo, retweeted_geo)
        retweeted_domain = proportion(retweeted_domain)
        retweeted_topic = proportion(retweeted_topic)
        retweeted_geo = proportion(retweeted_geo)
        try:
            average_influence = total_influence/count
        except:
            average_influence = 0
    retweeted_results["domian"] = retweeted_domain
    retweeted_results["topic"] = retweeted_topic
    retweeted_results["geo"] = retweeted_geo
    retweeted_results["influence"] = average_influence

    return retweeted_results

def statistics_influence_people(uid):
    # output: different retweeted and comment, uids' domain distribution, topic distribution, registeration geo distribution
    results = {} # retwweted weibo people and comment weibo people
    results["retweeted"] = {}
    results["comment"] = {}
    try:
        bci_result = es_user_portrait.get(index=index_name, doc_type="bci", id=uid)["_source"]
    except:
        bci_result = []
        return json.dumps(results)
    #print bci_result
    origin_retweeted_mid = [] # origin weibo mid
    retweeted_retweeted_mid = [] # retweeted weibo mid
    origin_comment_mid = []
    retweeted_comment_mid = []
    origin_retweeted = json.loads(bci_result["origin_weibo_retweeted_detail"])
    retweeted_retweeted = json.loads(bci_result["retweeted_weibo_retweeted_detail"])
    origin_comment = json.loads(bci_result["origin_weibo_comment_detail"])
    retweeted_comment = json.loads(bci_result["retweeted_weibo_comment_detail"])
    if origin_retweeted:
        origin_retweeted_mid = origin_retweeted.keys()
    if retweeted_retweeted:
        retweeted_retweeted_mid = retweeted_retweeted.keys()
    if origin_comment:
        origin_comment_mid = origin_comment.keys()
    if retweeted_comment:
        retweeted_comment_mid = retweeted_comment.keys()

    query_body = {
        "query":{
            "filtered":{
                "filter":{
                    "bool":{
                        "should":[
                        ],
                        "must": [
                        ]
                    }
                }
            }
        },
        "size":100000
    }

    retweeted_results = influenced_user_detail(query_body, origin_retweeted_mid, retweeted_retweeted_mid, 3)
    comment_results = influenced_user_detail(query_body, origin_comment_mid, retweeted_comment_mid, 2)
    results["retweeted"] = retweeted_results
    results["comment"] = comment_results

    print results

    return json.dumps(results)


def tag_vector(uid):
    try:
        bci_result = es_cluster.get(index=index_name, doc_type="bci", id=uid)["_source"]
    except:
        tag = influence_tag["0"]
        return tag

    origin_retweeted = json.loads(bci_result["origin_weibo_retweeted_detail"])
    retweeted_retweeted = json.loads(bci_result["retweeted_weibo_retweeted_detail"])
    origin_comment = json.loads(bci_result["origin_weibo_comment_detail"])
    retweeted_comment = json.loads(bci_result["retweeted_weibo_comment_detail"])
    sum_retweeted = sum(origin_retweeted.values()) + sum(origin_comment.values())
    sum_comment = sum(retweeted_retweeted.values()) + sum(retweeted_comment.values())

    if sum_retweeted >= retweeted_threshould:
        if sum_comment >= comment_threshould:
            tag = influence_tag['3']
        else:
            tag = influence_tag['1']
    else:
        if sum_comment >= comment_threshould:
            tag = influence_tag['2']
        else:
            tag = influence_tag['4']

    return tag

if __name__ == "__main__":
    #print influenced_detail("3396850362", "20130901")
    #print get_text([["3617510756389302",10],["3617510748726939", 5], ["617510752637061", 3]])
    #print influenced_people("2758565493","3616273092968593",0)
    #statistics_influence_people("2282311537")
    print tag_vector("33711188092")
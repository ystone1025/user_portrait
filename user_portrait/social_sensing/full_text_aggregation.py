# -*- coding:utf-8 -*-


import sys
import time
import json
import numpy as np
from elasticsearch import Elasticsearch
from  mappings_social_sensing import mappings_sensing_task
reload(sys)
sys.path.append("./../")
from global_utils import es_flow_text as es_text
from global_utils import es_user_profile as es_profile
from global_utils import es_user_portrait 
from global_utils import R_SOCIAL_SENSING as r
from time_utils import ts2datetime, datetime2ts
from global_utils import flow_text_index_name_pre, flow_text_index_type, profile_index_name, profile_index_type, \
                         portrait_index_name, portrait_index_type
from parameter import SOCIAL_SENSOR_TIME_INTERVAL as time_interval
from parameter import SOCIAL_SENSOR_FORWARD_RANGE as forward_time_range
from parameter import DETAIL_SOCIAL_SENSING as index_sensing_task
from parameter import INDEX_MANAGE_SOCIAL_SENSING as index_manage_social_task
from parameter import DOC_TYPE_MANAGE_SOCIAL_SENSING as task_doc_type
from parameter import FORWARD_N as forward_n
from parameter import INITIAL_EXIST_COUNT as initial_count
from parameter import IMPORTANT_USER_NUMBER, IMPORTANT_USER_THRESHOULD, signal_brust, signal_track, signal_count_varition, signal_sentiment_varition, signal_nothing, signal_nothing_variation, \
                      unfinish_signal, finish_signal


# aggragate weibo keywords of timestamp ts1 and ts2
def aggregation_range(ts1, ts2): 
    query_body = {
        "query":{
            "filtered":{
                "filter":{
                    "range":{
                        "timestamp":{
                            "gte": ts1,
                            "lt": ts2
                        }
                    }
                }
            }
        },
        "aggs":{
            "all_interests":{
                "terms": {"field": "keywords_string",
                          "size": 100
                }
            }
        }
    }

    return query_body

# aggregate sentiment with a specified keyword or keywords----list
# 在给定关键词时，聚合某段时间内相关微博的关键词、情绪
def aggregation_sentiment(ts1, ts2, keyword_list, aggregation_word, size=10):
    query_body = {
        "query":{
            "filtered":{
                "filter":{
                    "bool":{
                        "must":[{
                            "range":{
                                "timestamp":{
                                    "gte": ts1,
                                    "lt": ts2
                                }
                            }},
                            {"terms":{
                                "keywords_string": keyword_list
                            }
                        }]
                    }
                }
            }
        },
        "aggs":{
            "all_sentiment":{
                "terms":{"field": aggregation_word, "size": size}
            }
        }
    }

    return query_body


#聚合一段时间内特定社会传感器的微博的关键词/情绪
def aggregation_sensor_keywords(ts1, ts2, uid_list, aggregation_word, size=10):
    query_body = {
        "query":{
            "filtered":{
                "filter":{
                    "bool":{
                        "must":[{
                            "range":{
                                "timestamp":{
                                    "gte": ts1,
                                    "lt": ts2
                                }
                            }}
                        ],
                        "should":[
                        ]
                    }
                }
            }
        },
        "aggs":{
            "all_keywords":{
                "terms":{ "field": aggregation_word, "size": size}
            }
        }
    }

    if len(uid_list) == 0:
        pass
    elif len(uid_list) == 1:
        query_body["query"]["filtered"]["filter"]["bool"]["must"].append({"term": {"uid": uid_list[0]}})
    else:
        for iter_uid in uid_list:
            query_body["query"]["filtered"]["filter"]["bool"]["should"].append({"term": {"uid": iter_uid}})

    return query_body


def temporal_keywords(ts1, ts2):
    keywords_set = set()
    date = ts2datetime(time.time())
    date = "2013-09-07"
    index_date = flow_text_index_name_pre + date
    #search_results = es_text.search(index=index_date, doc_type=flow_text_index_type, body=aggregation_range(ts1, ts2))['aggregations']['all_interests']['buckets']
    search_results = es_text.search(index=index_date, doc_type=flow_text_index_type, body=aggregation_sentiment(ts1, ts2, ["舟曲", "泥石流"], "keywords_string", 20))['aggregations']['all_sentiment']['buckets']

    # print keywords
    for item in search_results:
        print item["key"].encode("utf-8", "ignore"), item["doc_count"], "\n"
        #keywords_set.add(item["key"].encode("utf-8", "ignore"))

    return keywords_set



# 事件检测中用于查询给定关键词，在某段时间内的原创微博列表
# 基于全文索引的方式查询text字段
def query_mid_list(ts, keywords_list, time_segment):
    # 第一步，聚合前六个小时相关微博mid, 首先获得原创微博
    #ts = time.time()
    #ts = 1377964800+3600
    query_body = {
        "query": {
            "bool": {
                "must": [
                    {"range": {
                        "timestamp": {
                            "gte": ts - time_segment,
                            "lt": ts
                        }
                     }}
                ]
            }
        },
        "sort": {"sentiment": {"order": "desc"}},
        "size": 10000
    }
    if keywords_list:
        query_body['query']['bool']['should'] = []
        for word in keywords_list:
            query_body['query']['bool']['should'].append({'wildcard':{"text": "*"+word+"*"}})

    datetime = ts2datetime(ts)
    # test
    #datetime = "2013-09-07"
    index_name = flow_text_index_name_pre + datetime
    exist_es = es_text.indices.exists(index_name)
    if exist_es:
        search_results = es_text.search(index=index_name, doc_type=flow_text_index_type, body=query_body, fields=["root_mid"])["hits"]["hits"]
    else:
        search_results = []
    origin_mid_list = [] # all related weibo mid list
    if search_results:
        for item in search_results:
            if item.get("fields", ""):
                origin_mid_list.append(item["fields"]["root_mid"][0])
            else:
                origin_mid_list.append(item["_id"])

    datetime_1 = ts2datetime(ts-time_segment)
    index_name_1 = flow_text_index_name_pre + datetime_1
    exist_bool = es_text.indices.exists(index_name_1)
    if datetime != datetime_1 and exist_bool:
        search_results_1 = es_text.search(index=index_name_1, doc_type=flow_text_index_type, body=query_body, fields=['root_mid'])["hits"]["hits"]
        if search_results_1:
            for item in search_results_1:
                if item.get("fields", ""):
                    origin_mid_list.append(item["fields"]["root_mid"][0]) 
                else:
                    origin_mid_list.append(item["_id"])


    return origin_mid_list


# 给定所有原创微博list，搜索在time-time-interval时间内的热门微博root-mid
# 可以复用
def query_hot_weibo(ts, origin_mid_list, time_segment, keywords_list, aggregation_field="root_mid", size=100):
    query_all_body = {
        "query": {
            "bool": {
                "must": [
                    {"range": {
                        "timestamp":{
                            "gte": ts - time_segment,
                            "lt": ts
                        }
                    }}
                ],
                "should": [
                ]
            }
        },
        "aggs":{
            "all_count":{
                "terms":{"fields": aggregation_field, "size": size}
            }
        }
    }

    if keywords_list:
        for word in keywords_list:
            query_body['query']['bool']['should'].append({'wildcard':{"text": "*"+word+"*"}})

    datetime = ts2datetime(ts)
    # test
    #datetime = "2013-09-07"
    hot_mid_dict = dict()
    index_name = flow_text_index_name_pre + datetime
    exist_es = es_text.indices.exists(index_name)
    if origin_mid_list and exist_es:
        query_all_body["query"]["bool"]["should"].append({"terms": {"root_mid": origin_mid_list}})
        query_all_body["query"]["bool"]["should"].append({"terms": {"mid": origin_mid_list}})
        results = es_text.search(index=index_name, doc_type=flow_text_index_type, body=query_all_body)['aggregations']['all_count']['buckets']
        if results:
            for item in results:
                hot_mid_dict[item['key']] = item['doc_count']

        datetime_1 = ts2datetime(ts-time_segment)
        index_name_1 = flow_text_index_name_pre + datetime_1
        exist_es_1 = es_text.indices.exists(index_name_1)
        if datetime_1 != datetime and exist_es_1:
            query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"root_mid": origin_mid_list}})
            query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"mid": origin_mid_list}})
            results_1 = es_text.search(index=index_name, doc_type=flow_text_index_type, body=query_all_body)['aggregations']['all_count']['buckets']
            if results_1:
                for item in results:
                    hot_mid_dict[item['key']] = item['doc_count']

    return hot_mid_dict

# 给定原创微博list，搜索之前time_segment时间段内的微博总数，即转发和评论总数
def query_related_weibo(ts, origin_mid_list, time_segment, keywords_list):
    query_all_body = {
        "query": {
            "filtered": {
                "filter": {
                    "bool": {
                        "must": [
                            {"range": {
                                "timestamp":{
                                    "gte": ts - time_segment,
                                    "lt": ts
                                }
                            }}],
                        "should": [
                            {"terms":{
                                "keywords_string": keywords_list
                                }
                            }
                        ]
                    }
                }
            }
        },
        "aggs":{
            "all_count":{
                "terms":{"field": "message_type"}
            }
        }
    }

    datetime = ts2datetime(ts)
    # test
    #datetime = "2013-09-07"
    index_name = flow_text_index_name_pre + datetime
    exist_es = es_text.indices.exists(index_name)
    return_results = {"origin": 0, "retweeted": 0, "comment": 0}
    if origin_mid_list and exist_es:
        query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"root_mid": origin_mid_list}})
        query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"mid": origin_mid_list}})
        results = es_text.search(index=index_name, doc_type=flow_text_index_type, body=query_all_body)['aggregations']['all_count']['buckets']
        if results:
            for item in results:
                if int(item['key']) == 1:
                    return_results['origin'] = item['doc_count']
                elif int(item['key']) == 3:
                    return_results['retweeted'] = item['doc_count']
                elif int(item['key']) == 2:
                    return_results['comment'] = item['doc_count']
                else:
                    pass

    datetime_1 = ts2datetime(ts-time_segment)
    index_name_1 = flow_text_index_name_pre + datetime_1
    exist_bool = es_text.indices.exists(index_name_1)
    if datetime != datetime_1 and exist_bool:
        repost_count_1 = 0
        if origin_mid_list:
            query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"root_mid": origin_mid_list}})
            query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"mid": origin_mid_list}})
            results_1 = es_text.search(index=index_name_1, doc_type=flow_text_index_type, body=query_all_body)['aggregations']['all_count']['buckets']
            if results_1:
                for item in results_1:
                    if int(item['key']) == 1:
                        return_results['origin'] += item['doc_count']
                    elif int(item['key']) == 3:
                        return_results['retweeted'] += item['doc_count']
                    elif int(item['key']) == 2:
                        return_results['comment'] += item['doc_count']
                    else:
                        pass

    return_results['total_count'] = sum(return_results.values())
    print "return_results: ", return_results
    return return_results



# 给定微博mid的前提下，聚合相关微博的情绪分布
def aggregation_sentiment_related_weibo(ts, origin_mid_list, time_segment, keywords_list):
    query_all_body = {
        "query": {
            "filtered": {
                "filter": {
                    "bool": {
                        "must": [
                            {"range": {
                                "timestamp":{
                                    "gte": ts - time_segment,
                                    "lt": ts
                                }
                            }}
                        ],
                        "should": [
                            {"terms":{
                                "keywords_string": keywords_list
                                }
                            }
                        ]
                    }
                }
            }
        },
        "aggs":{
            "all_sentiments":{
                "terms":{ "field": "sentiment"}
            }
        }
    }

    datetime = ts2datetime(ts)
    results =dict()
    results['0'] = 0
    results['1'] = 0
    results['2'] = 0
    results['3'] = 0
    # test
    #datetime = "2013-09-07"
    index_name = flow_text_index_name_pre + datetime
    exist_es = es_text.indices.exists(index_name)
    if origin_mid_list and exist_es:
        query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"root_mid": origin_mid_list}})
        query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"mid": origin_mid_list}})
        search_results = es_text.search(index=index_name, doc_type=flow_text_index_type, body=query_all_body)['aggregations']['all_sentiments']['buckets']
        if search_results:
            for item in search_results:
                key = item['key']
                count = item['doc_count']
                results[key] = count
        print results
    print "total_sentiments: ", sum(results.values())

    datetime_1 = ts2datetime(ts-time_segment)
    index_name_1 = flow_text_index_name_pre + datetime_1
    exist_bool = es_text.indices.exists(index_name_1)
    if datetime != datetime_1 and exist_bool:
        repost_count_1 = 0
        if origin_mid_list:
            query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"root_mid": origin_mid_list}})
            query_all_body["query"]["filtered"]["filter"]["bool"]["should"].append({"terms": {"mid": origin_mid_list}})
            search_results = es_text.search(index=index_name_1, doc_type=flow_text_index_type, body=query_all_body)['aggregations']['all_sentiments']['buckets']
            if search_results:
                for item in search_results:
                    key = item['key']
                    count = item['doc_count']
                    results[key] += count

    return results

# 获得前6个小时内的各时间间隔内原创微博数、转发微博数、评论微博数，计算相应的均值和方差
# ts是当前的时间点，应往前推N个时间间隔
# 从social_sensing_task中读取
def get_forward_numerical_info(task_name, ts, keywords_list):
    results = []
    ts_series = []
    for i in range(1, forward_n+1):
        ts_series.append(ts-i*time_interval)

    # check if detail es of task exists
    # es.doctype = task_name_keywords_list
    #keywords_list = [item.encode("utf-8", "ignore") for item in keywords_list]
    #task_name = task_name.encode("utf-8", "ignore")
    #print type(task_name),type( "_".join(keywords_list))
    #doctype = task_name + "_" + "_".join(keywords_list)
    doctype = task_name
    index_exist = es_user_portrait.exists(index_sensing_task, doctype)
    if not index_exist:
        print "new create task detail index"
        mappings_sensing_task(task_name)

    if ts_series:
        search_results = es_user_portrait.mget(index=index_sensing_task, doc_type=task_name, body={"ids":ts_series})['docs']
        found_count = 0
        average_origin = []
        average_retweeted = []
        average_commet = []
        average_total = []
        average_negetive = []
        for item in search_results:
            if item['found']:
                temp = item['_source']
                sentiment_dict = json.loads(temp['sentiment_distribution'])
                #average_origin.append(int(temp['origin_weibo_number']))
                #average_retweeted.append(int(temp['retweeted_weibo_number']))
                #average_comment.append(int(temp['comment_weibo_number']))
                average_total.append(int(temp['weibo_total_number']))
                average_negetive.append(int(sentiment_dict["2"])+int(sentiment_dict['3']))
                found_count += 1
            """
            else:
                average_origin.append(0)
                average_retweeted.append(0)
                average_commet.append(0)
                average_total.append(0)
                average_negetive.append(0)
            """

        if found_count > initial_count:
            number_mean = np.mean(average_total)
            number_std = np.std(average_total)
            sentiment_mean = np.mean(average_negetive)
            sentiment_std = np.mean(average_negetive)
            results = [1, number_mean, number_std, sentiment_mean, sentiment_std]
        else:
            results = [0]

    return results



# event detection
# 给定某个关键词，首先聚合出前6个小时内的平均微博量，再计算当前时间片段内的微博量
# 以两个的比值大小决定是不是有事件爆发
# keywords_list---关键词列表, ts--当前时间, time_segment---时间区间长度
def burst_detection(keywords_list, ts):
    # 前一段时间内原创微博列表
    n_range = forward_time_range/time_interval
    forward_origin_weibo_list = query_mid_list(ts-time_interval, keywords_list, forward_time_range)
    forward_total_count = query_related_weibo(ts-time_interval, forward_origin_weibo_list, forward_time_range, keywords_list)['total_count']
    #print "forward origin weibo: ", len(forward_origin_weibo_list)
    #print "forward total count: ", forward_total_count
    forward_average_count = forward_total_count/n_range
    #print "forward average count: ", forward_average_count


    current_mid_list = query_mid_list(ts, keywords_list, time_interval)
    #print "current weibo list :", len(current_mid_list)
    all_mid_list = []
    all_mid_list.extend(current_mid_list)
    all_mid_list.extend(forward_origin_weibo_list)
    current_total_count = query_related_weibo(ts, all_mid_list, time_interval, keywords_list)["total_count"]
    # 额外计算了前6个小时原创微博数的量值，需要修正
    current_total_count -= len(forward_origin_weibo_list)
    #print "now total count :", current_total_count
    try:
        ratio = float(current_total_count)/forward_average_count
    except:
        ratio = 0
    return current_total_count, forward_average_count, ratio






# 特定关键词的社会事件监测，task_detail是已经json.loads的
def specific_keywords_burst_dection(task_detail):
    task_name = task_detail[0]
    keywords_list = task_detail[2]
    stop_time = task_detail[3]
    forward_warning_status = task_detail[4]
    ts = int(task_detail[5])
    forward_result = get_forward_numerical_info(task_name, ts, keywords_list)
    # 之前时间阶段内的原创微博list
    forward_origin_weibo_list = query_mid_list(ts-time_interval, keywords_list, forward_time_range)
    # 当前阶段内原创微博list
    current_mid_list = query_mid_list(ts, keywords_list, time_interval)
    all_mid_list = []
    all_mid_list.extend(current_mid_list)
    all_mid_list.extend(forward_origin_weibo_list)
    print "all mid list: ", len(all_mid_list)
    # 查询当前的原创微博和之前12个小时的原创微博在当前时间内的转发和评论数, 聚合按照message_type
    statistics_count = query_related_weibo(ts, all_mid_list, time_interval, keywords_list)
    current_total_count = statistics_count['total_count']
    # 当前阶段内所有微博总数
    print "current all weibo: ", statistics_count
    current_origin_count = statistics_count['origin']
    current_retweeted_count = statistics_count['retweeted']
    current_comment_count = statistics_count['comment']

    # 聚合当前时间内积极、中性、悲伤、愤怒情绪分布
    # sentiment_dict = {"0": "neutral", "1":"positive", "2":"sad", "3": "anger"}
    sentiment_count = {"0": 0, "1": 0, "2": 0, "3": 0}
    datetime = ts2datetime(ts)
    datetime_1 = ts2datetime(ts-time_interval)
    # test
    #datetime = "2013-09-07"
    index_name = flow_text_index_name_pre + datetime
    exist_es = es_text.indices.exists(index_name)
    if exist_es:
        search_results = aggregation_sentiment_related_weibo(ts, all_mid_list, time_interval, keywords_list)

        sentiment_count = search_results
        print "sentiment_count: ", sentiment_count
    negetive_count = sentiment_count['2'] + sentiment_count['3']

    # 聚合当前时间内重要的人
    important_uid_list = []
    if exist_es:
        #search_results = es_text.search(index=index_name, doc_type=flow_text_index_type, body=aggregation_sensor_keywords(ts-time_interval, ts, [], "root_uid", size=IMPORTANT_USER_NUMBER))['aggregations']['all_keywords']['buckets']
        search_results = query_hot_weibo(ts, all_mid_list, time_interval, keywords_list, aggregation_field="root_uid", size=100)
        important_uid_list = search_results.keys()
        if datetime != datetime_1:
            index_name_1 = flow_text_index_name_pre + datetime_1
            if es_text.indices.exists(index_name_1):
                #search_results_1 = es_text.search(index=index_name_1, doc_type=flow_text_index_type, body=aggregation_sensor_keywords(ts-time_interval, ts, [], "root_uid", size=IMPORTANT_USER_NUMBER))['aggregations']['all_keywords']['buckets']
                search_results_1 = query_hot_weibo(ts, all_mid_list, time_interval, keywords_list, aggregation_field="root_uid", size=100)
                if search_results_1:
                    for item in search_results_1:
                        important_uid_list.append(item['key'])
    # 根据获得uid_list，从人物库中匹配重要人物
    if important_uid_list:
        important_results = es_user_portrait.mget(index=portrait_index_name, doc_type=portrait_index_type, body={"ids": important_uid_list})['docs']
    else:
        important_results = {}
    filter_important_list = [] # uid_list
    if important_results:
        for item in important_results:
            if item['found']:
                if item['_source']['importance'] > IMPORTANT_USER_THRESHOULD:
                        filter_important_list.append(item['_id'])
    print filter_important_list

    burst_reason = signal_nothing_variation
    warning_status = signal_nothing
    finish = unfinish_signal # "0"
    if forward_result[0]:
        # 根据移动平均判断是否有时间发生
        mean_count = forward_result[1]
        std_count = forward_result[2]
        mean_sentiment = forward_result[3]
        std_sentiment = forward_result[4]
        if current_total_count > mean_count+1.96*std_count: # 异常点发生
            print "====================================================="
            if forward_warning_status == signal_brust: # 已有事件发生，改为事件追踪
                warning_status = signal_track
            else:
                warning_status = signal_brust
            burst_reason = signal_count_varition # 数量异常
        if negetive_count > mean_sentiment+1.96*std_sentiment:
            warning_status = signal_brust
            burst_reason += signal_sentiment_varition # 负面情感异常, "12"表示两者均异常
            if forward_warning_status == signal_brust: # 已有事件发生，改为事件追踪
                warning_status = signal_track

        if int(stop_time) <= ts: # 检查任务是否已经完成
            finish = finish_signal 


    results = dict()
    results['origin_weibo_number'] = current_origin_count
    results['retweeted_weibo_number'] = current_retweeted_count
    results['comment_weibo_number'] = current_comment_count
    results['weibo_total_number'] = current_total_count
    results['sentiment_distribution'] = json.dumps(sentiment_count)
    results['important_users'] = json.dumps(filter_important_list)
    results['burst_reason'] = burst_reason
    results['timestamp'] = ts
    # es存储当前时段的信息
    doctype = task_name
    #es_user_portrait.index(index=index_sensing_task, doc_type=doctype, id=ts, body=results)

    # 更新manage social sensing的es信息
    temporal_result = es_user_portrait.get(index=index_manage_social_task, doc_type=task_doc_type, id=task_name)['_source']
    temporal_result['warning_status'] = warning_status
    temporal_result['burst_reason'] = burst_reason
    temporal_result['finish'] = finish
    history_status = json.loads(temporal_result['history_status'])
    history_status.append([ts, '_'.join(keywords_list), warning_status])
    temporal_result['history_status'] = json.dumps(history_status)
    #es_user_portrait.index(index=index_manage_social_task, doc_type=task_doc_type, id=task_name, body=temporal_result)

    return "1"




if __name__ == "__main__":

    #temporal_keywords(1378557829, 1378557829+10000)
    """
    ts2 = datetime2ts("2013-09-08")
    ts1 = datetime2ts("2013-09-01")
    ts = ts1
    while ts < ts2:
        current_total_count, forward_average_count, ratio = burst_detection(["洪水", "洪灾"], ts)
        if current_total_count > 100 and ratio > 3:
            index_date = flow_text_index_name_pre + ts2datetime(ts)
            search_results = es_text.search(index=index_date, doc_type=flow_text_index_type, body=aggregation_sentiment(ts-time_interval, ts, ["洪水", "洪灾"], "keywords_string", 20))['aggregations']['all_sentiment']['buckets']
            print search_results
        ts += time_interval
    """
    #now_ts = time.time()
    #print get_forward_numerical_info("test", now_ts)
    query_hot_weibo(ts, origin_mid_list, 1800, ['政府'], size=100)

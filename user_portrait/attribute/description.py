# -*- coding:utf-8 -*-
import time
import sys
from influence_appendix import level

reload(sys)
sys.path.append('./../')
from global_utils import es_user_portrait as es
from time_utils import datetime2ts, ts2datetime
from parameter import INFLUENCE_CONCLUSION as conclusion_dict
from parameter import INFLUENCE_LENTH as N
from parameter import PRE_ACTIVENESS as pre_activeness
from parameter import INFLUENCE_LEVEL as influence_level

def active_geo_description(result):
    active_city = {}
    active_ip = {}

    for city,value in result.items():
        count = 0
        for ip, ip_value in value.items():
            count += ip_value
            active_ip[ip] = ip_value
        active_city[city] = count

    city_count = len(active_city)
    ip_count = len(active_ip)

    active_city = sorted(active_city.iteritems(), key=lambda asd:asd[1], reverse=True)
    city = active_city[0][0]

    if city_count == 1 and ip_count <= 4:
        description_text = '为该用户的主要活动地，且较为固定在同一个地方登陆微博'
        city_list = city.split('\t')
        city = city_list[len(city_list)-1]
        description = [city, description_text]
    elif city_count >1 and ip_count <= 4:
        description_text1 = '多为该用户的主要活动地，且经常出差，较为固定在'
        description_text2 = '个城市登陆微博'
        city_list = city.split('\t')
        city = city_list[len(city_list)-1]
        description = [city, description_text1, city_count, description_text2]
    elif city_count == 1 and ip_count > 4:
        description_text = '为该用户的主要活动地，且经常在该城市不同的地方登陆微博'
        city_list = city.split('\t')
        city = city_list[len(city_list)-1]
        description = [city, description_text]
    else:
        description_text = '多为该用户的主要活动地，且经常出差，在不同的城市登陆微博'
        city_list = city.split('\t')
        city = city_list[len(city_list)-1]
        description = [city, description_text]
    return description


def active_time_description(result):
    count = 0
    for v in result.values():
        count += v
    average = count / 6.0
    active_time_order = sorted(result.iteritems(), key=lambda asd:asd[1], reverse=True)
    active_time = {0:'0-4', 14400:'4-8',28800:'8-12',43200:'12-16',57600:'16-20',72000:'20-24'}
    v_list = []
    for k,v in result.items():
        if v > average:
            v_list.append(active_time[k])
    definition = ','.join(v_list)
    timestamp = active_time_order[0][0]
    segment = str(int(timestamp)/4/3600)

    pd = {'0':'夜猫子','1':'早起刷微博','2':'工作时间刷微博','3':'午休时间刷微博','4':'上班时间刷微博','5':'下班途中刷微博','6':'晚间休息刷微博'}
 
    description = '用户属于%s类型，活跃时间主要集中在%s' % (pd[segment], definition)

    return description, pd[segment]


def hashtag_description(result):
    order_hashtag = sorted(result.iteritems(), key=lambda asd:asd[1], reverse=True)
    count_hashtag = len(result)

    count = 0 
    if result:
        for v in result.values():
            count += v
        average = count / len(result)

        v_list = []
        like = order_hashtag[0][0]
        for k,v in result.items():
            if v >= average:
                v_list.append(k)
        definition = ','.join(v_list)

    if count_hashtag == 0:
        description = u'该用户不喜欢参与话题讨论，讨论数为0'
    elif count_hashtag >3:
        description = u'该用户热衷于参与话题讨论,热衷的话题是%s' % definition
    else:
        description = u'该用户不太热衷于参与话题讨论, 参与的话题是%s' % definition

    return description


# version: 2015-12-22
# conclusion of a user based on history influence info
def conclusion_on_influence(uid):
    # test
    index_name = "this_is_a_copy_user_portrait"
    index_type = "manage"
    try:
        influ_result = es.get(index=index_name, doc_type=index_type, id=uid)['_source']
    except:
        influ_result = {}
        result = conclusion_dict['0']
        return result

    # generate time series---keys
    now_ts = time.time()
    now_ts = datetime2ts('2013-09-12')
    influence_set = set()
    activeness_set = set()
    for i in range(N):
        ts = ts2datetime(now_ts - i*3600*24)
        activeness_set.add(pre_activeness+ts)
        influence_set.add(ts.replace('-', ""))

    # 区分影响力和活跃度的keys
    keys_set = set(influ_result.keys())
    influence_keys = keys_set & activeness_set
    activeness_keys = keys_set & influence_set

    if influence_keys:
        influence_value = []
        for key in influence_keys:
            influence_value.append(influ_result[key])
        mean, std_var = level(influence_value)
        try:
            variate = std_var/(mean*1.0)
        except:
            variate = 0
        if mean < influence_level[0]:
            result = conclusion_dict['1']
        elif mean >= influence_level[0] and mean < influence_level[1]:
            result = conclusion_dict['2']
        elif mean >= influence_level[1] and mean < influence_level[2]:
            if variate < 0.15:
                result = conclusion_dict["3"]
            else:
                result = conclusion_dict["4"]
        elif mean >= influence_level[2] and mean < influence_level[3]:
            if variate < 0.15:
                result = conclusion_dict["5"]
            else:
                result = conclusion_dict["6"]
        elif mean >= influence_level[3] and mean < influence_level[4]:
            result = conclusion_dict["7"]
        else:
            result = conclusion_dict["8"]
    else:
        result = conclusion_dict['0']

    return result

if __name__ == "__main__":
    """
    c = {'beijing':{'219.224.135.1': 5}}
    b = {0:2, 14400:1,28800:3, 43200:5, 57600:2, 72000:3}
    a = {'花千骨':4}
    k = active_time_description(b)
    m = active_geo_description(c)
    n = hashtag_description(a)
    print m
    print k
    print n
    """
    print conclusion_on_influence('2050856634')





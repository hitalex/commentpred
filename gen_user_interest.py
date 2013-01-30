#encoding=utf8

"""
根据LDA模型和用户的关注数据，产生用户的兴趣向量。
同时抽取用户在训练时间段内的创建的topic数和发表的评论数。
为了保证能到得到尽可能多的用户的兴趣数据，在这里将浏览所有的历史数据。
"""
import sys
import codecs
import logging

from gensim import models, corpora

from logconfig import congifLogger
from prepare import load_user_list
from utils import is_between

# 除了训练集中的数据以外，都可已作为用户兴趣的内容
from prepare import TRAIN_START_DATE, TRAIN_END_DATE
from prepare import TEST_START_DATE, TEST_END_DATE

# config logging
log = logging.getLogger('Main.interest')
congifLogger("gen_user_interest.log", 5)

def save_interest_info(interest_path, interest_info,model, dictionary):
    """ 将用户的兴趣向量和行为信息写入到文件
    """
    # 写入感兴趣的文本
    f = codecs.open(interest_path, 'w', 'utf-8')
    for uid in interest_info:
        text = interest_info[uid][1]
        document = text.split(' ')
        doc_bow = dictionary.doc2bow(document)
        doc_lda = model.__getitem__(doc_bow, eps = 0)
        #print doc_lda
        probs = [topicvalue for topicid, topicvalue in doc_lda]
        str_probs = [str(prob) for prob in probs]
        # 将每行用户中最后的文本替换为topic的概率分布
        f.write(uid + '[=]' + ','.join(str_probs) + '\n')
        
    f.close()
    
def save_behavior(behavior_path, behavior)
    # 写入行为信息
    f = codecs.open(behavior_path, 'w', 'utf-8')
    for uid in behavior:
        f.write(uid + '[=]' + behavior[uid][0] + '[=]' + behavior[uid][1] + '\n')
    f.close()
    
def get_interested_topic(uid_list, comment_path):
    """ 从comment info中获取用户感兴趣的topic list列表（即评论的某个topic的id列表）以及自己的topic内容
    """
    user_set = set(uid_list)
    # user id ==> (interested topic set, content)
    interest_info = dict()
    # user id ==> (num_topics, num_comments)
    behavior = dict()
    f = codecs.open(comment_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[3]
        pubdate = datetime.strptime(seg_list[4], "%Y-%m-%d %H:%M:%S")
        if uid in user_set and pubdate < TEST_START_DATE:
            topic_id = seg_list[2]
            content = seg_list[6]
            if not uid in interest_info:
                interest_info[uid] = (set(), '')
            interest_info[uid][0].add(topic_id)
            interest_info[uid][1] += (' ' + content)
        if uid in user_set:
            # 如果某个用户在训练时间内没有发表帖子或者评论，其设置为0
            if not uid in behavior:
                behavior[uid] = (0, 0) # ==> (num_topics, num_comments)
            # 只统计在训练时间段的评论数，而不管所属帖子的发表时间
            if is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE):
                behavior[uid][0] += 1
            
    f.close()
    # 检查是否为所有的用户都找到了兴趣信息
    for uid in uid_list:
        if not uid in interest_info:
            log.error('Interest info not found for user: %s' % uid)
    return interest_info, behavior

def gen_interest_text(uid_list, interest_info, behavior, topic_path):
    """ 根据用户感兴趣的topic list，从TopicInfo中找到用户感兴趣的文本
    """
    user_set = set(uid_list)
    # 建立topic id到user id的反向映射关系
    topic2uid = dict()
    for uid in interest_info:
        topic_set = interest_info[uid][0]
        for tid in topic_set:
            if not tid in topic2uid:
                topic2uid[tid] = []
            topic2uid[tid] = topic2uid[tid].append(uid)

    f = codecs.open(topic_path, 'w', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        topic_id = seg_list[0]
        uid = seg_list[2]
        pubdate = datetime.strptime(seg_list[3], "%Y-%m-%d %H:%M:%S")
        content = seg_list[4]
        # 统计发表的topic数
        if uid in user_set:
            if not uid in behavior:
                behavior[uid] = (0, 0)
            if is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE):
                behavior[uid][1] += 1
        # 保证topic的发布时间不在测试阶段
        if pubdate > TEST_START_DATE:
            continue
        # 添加用户感兴趣的topic的内容
        if topic_id in topic2uid:
            uid_list = topic2uid[topic_id]
            for uid in uid_list:
                interest_info[uid][1] += (' ' + content)
        
    f.close()
    
    return interest_info
    
if __name__ == '__main__':
    goup_id = 'ustv'
    path = 'tables/' + group_id + '/all-users-' + group_id
    user_list = load_user_list(path)
    total_user = len(user_list)
    log.info('Number of users loaded: %d' % total_user)
    
    model_path = 'ldamodels/' + group_id + '/title-comment-' + group_id + '.ldamodel'
    dict_path = 'ldamodels/' + group_id + '/dict-title-comment-' + group_id + '.dict'
    log.info('Loading LDA model...')
    ldamodel = models.ldamodel.LdaModel.load(model_path) # load model
    log.info('Loading dict...')
    dictionary = corpora.dictionary.Dictionary.load(dict_path) # load dict
    
    topic_path = 'tables/' + group_id + '/TopicInfo-raw-all-' + group_id
    comment_path = 'tables/' + group_id + '/CommentInfo-raw-all-' + group_id
    
    interest_path = 'tables/' + group_id + '/user-interest-' + group_id
    behavior_path = 'tables/' + group_id + '/behavior-' + group_id

    # 考虑到需要存储的内容较多，所以一次处理一定数目的用户
    start = 0
    count = 100 # 一次处理100个用户
    while start < total_user:
        if start + count < total_user:
            puid_list = uid_list[start:(start + count)]
        else:
            puid_list = uid_list[start:]
            
        log.info('Processing uid range: [%d, %d)' % (start, start+count))
        #print (start, start+count)
        interest_info, behavior = gen_user_interest(puid_list, comment_path)
        interest_info, behavior = gen_interest_text(puid_list, interest_info, behavior, topic_path)
        # save to file
        save_intrest_info(interest_path, interest_info, ldamodel, dictionary)
        save_behavior(behavior_path, behavior)
        
        start += count

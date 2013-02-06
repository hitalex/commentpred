#encoding=utf8

"""
根据LDA模型和用户的关注数据，产生用户的兴趣向量。
同时抽取用户在训练时间段内的创建的topic数和发表的评论数。
为了保证能到得到尽可能多的用户的兴趣数据，在这里将浏览所有的历史数据。
"""
import sys
import codecs
import logging
from datetime import datetime
import os

from gensim import models, corpora

from logconfig import congifLogger
from prepare import load_user_list
from utils import is_between
from prepare_corpus import seg_chinese, remove_url

# 除了训练集中的数据以外，都可已作为用户兴趣的内容
from prepare import TRAIN_START_DATE, TRAIN_END_DATE
from prepare import TEST_START_DATE, TEST_END_DATE

# config logging
log = logging.getLogger('Main.interest')
congifLogger("gen_user_interest.log", 5)

def save_interest_info(interest_path, interest_info, model, dictionary):
    """ 将用户的兴趣向量和行为信息写入到文件
    """
    # 写入感兴趣的文本
    f = codecs.open(interest_path, 'a', 'utf-8')
    for uid in interest_info:
        text = interest_info[uid][1]
        # 如果该用户没有任何兴趣文本，则表示其没有发表topic或者参与评论
        text = remove_url(text)
        text = seg_chinese(text)
        document = text.split(' ')
        doc_bow = dictionary.doc2bow(document)
        doc_lda = model.__getitem__(doc_bow, eps = 0)
        #print doc_lda
        probs = [topicvalue for topicid, topicvalue in doc_lda]
        str_probs = [str(prob) for prob in probs]
        # 将每行用户中最后的文本替换为topic的概率分布
        f.write(uid + '[=]' + ','.join(str_probs) + '\n')
        if ','.join(str_probs) == '0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1':
            log.info('Equal topic distribution: uid is: %s; text is: %s' % (uid, text))
        
    f.close()
    
def get_interested_topic(uid_list, comment_path):
    """ 从comment info中获取用户感兴趣的topic list列表（即评论的某个topic的id列表）以及自己的topic内容
    """
    user_set = set(uid_list)
    # user id ==> (interested topic set, content)
    interest_info = dict()
    # 初始化interest
    # 注意：有可能interest_info并不包含所有的uid，不过都为其设置了初始值
    for uid in uid_list:
        interest_info[uid] = [set(), '']
        
    f = codecs.open(comment_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[3]
        pubdate = datetime.strptime(seg_list[4], "%Y-%m-%d %H:%M:%S")
        # 这里并不限制评论发表的时间
        if uid in interest_info:
            topic_id = seg_list[2]
            content = seg_list[6]
            interest_info[uid][0].add(topic_id)
            interest_info[uid][1] += (' ' + content)
            
    f.close()

    return interest_info

def gen_interest_text(uid_list, interest_info, topic_path):
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
            topic2uid[tid].append(uid)

    f = codecs.open(topic_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        topic_id = seg_list[0]
        uid = seg_list[2]
        pubdate = datetime.strptime(seg_list[3], "%Y-%m-%d %H:%M:%S")
        title = seg_list[4]
        content = seg_list[5]
        # 为了得到尽可能多的用户兴趣文本，这里并不限制帖子发表的时间
        # 添加用户感兴趣的topic的内容
        if topic_id in topic2uid:
            uid_list = topic2uid[topic_id]
            for uid in uid_list:
                interest_info[uid][1] += (' ' + title + ' ' + content)
        
    f.close()

def filter_user(interest_info):
    """ 注意：之后可能会根据interest的信息，过滤倒一些用户
    """
    pass
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = sys.argv[1]
    log.info('Prepare user interest for group: %s' % group_id)
    
    print 'Loading users...'
    path = 'social/' + group_id + '/all-users-' + group_id
    uid_list = load_user_list(path)
    total_user = len(uid_list)
    log.info('Number of users loaded: %d' % total_user)
    print 'Number of users loaded: %d' % total_user
    
    print 'Loading model and dict...'
    model_path = 'ldamodels/' + group_id + '/title-comment-' + group_id + '.ldamodel'
    dict_path = 'ldamodels/' + group_id + '/dict-title-comment-' + group_id + '.dict'
    log.info('Loading LDA model...')
    ldamodel = models.ldamodel.LdaModel.load(model_path) # load model
    log.info('Loading dict...')
    dictionary = corpora.dictionary.Dictionary.load(dict_path) # load dict
    
    print 'Gen user interest...'
    topic_path = 'tables/' + group_id + '/TopicInfo-raw-all-' + group_id
    comment_path = 'tables/' + group_id + '/CommentInfo-raw-all-' + group_id
    
    interest_path = 'tables/' + group_id + '/user-interest-' + group_id
    filtered_user_path = 'social/' + group_id + '/filtered-user-interest-' + group_id
    
    # 如果user-interest文件存在，则删除文件
    if os.path.exists(interest_path):
        os.remove(interest_path)

    # 考虑到需要存储的内容较多，所以一次处理一定数目的用户
    start = 0
    count = 1000 # 一次处理100个用户
    ff = open(filtered_user_path, 'w')
    user_count = 0
    while start < total_user:
        if start + count < total_user:
            puid_list = uid_list[start:(start + count)]
        else:
            puid_list = uid_list[start:]
            
        print 'Processing uid: [%d, %d)' % (start, start+count)
        log.info('Processing uid range: [%d, %d)' % (start, start+count))
        #print (start, start+count)
        interest_info = get_interested_topic(puid_list, comment_path)
        gen_interest_text(puid_list, interest_info, topic_path)
        # filter out users who contributed very few
        #filter_user(interest_info)
        # save to file
        save_interest_info(interest_path, interest_info, ldamodel, dictionary)
        # save the users that is not filtered
        for uid in interest_info:
            ff.write(uid + '\n')
            user_count += 1
            
        start += count
    
    print 'Number of new user count after interest filter: %d' % user_count
    ff.close()

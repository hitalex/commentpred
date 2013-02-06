# coding=utf8

"""
统计用户的行为信息，并过滤一部分行为频率很低的用户
此脚本与gen_user_interest.py相对应
"""

import sys
import codecs
import logging
from datetime import datetime
import os

from logconfig import congifLogger
from prepare import load_user_list
from utils import is_between

# 除了训练集中的数据以外，都可已作为用户兴趣的内容
from prepare import TRAIN_START_DATE, TRAIN_END_DATE
from prepare import TEST_START_DATE, TEST_END_DATE

# config logging
log = logging.getLogger('Main.behavior')
congifLogger("gen_user_behavior.log", 5)

    
def save_behavior(behavior_path, behavior):
    # 写入行为信息
    f = codecs.open(behavior_path, 'a', 'utf-8')
    for uid in behavior:
        f.write(uid + '[=]' + str(behavior[uid][0]) + '[=]' + str(behavior[uid][1]) + '\n')
    f.close()
    
def get_interested_topic(uid_list, comment_path):
    """ 从comment info中获取用户感兴趣的topic list列表（即评论的某个topic的id列表 ），
    并统计用户的评论次数
    """
    user_set = set(uid_list)
    # user id ==> (num_comments, num_topics)
    behavior = dict()
    # 初始化behavior
    # 注意：有可能interest_info和behavior并不包含所有的uid，不过都为其设置了初始值
    for uid in uid_list:
        behavior[uid] = [0, 0]
        
    f = codecs.open(comment_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[3]
        pubdate = datetime.strptime(seg_list[4], "%Y-%m-%d %H:%M:%S")
        
        if uid in behavior and is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE):
            # 如果某个用户在训练时间内没有发表帖子或者评论，其设置为0
            behavior[uid][0] += 1 # 参与评论数加1
            
    f.close()

    return behavior

def gen_interest_text(uid_list, behavior, topic_path):
    """ 根据用户感兴趣的topic list，从TopicInfo中找到用户感兴趣的文本
    """
    f = codecs.open(topic_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        topic_id = seg_list[0]
        uid = seg_list[2]
        pubdate = datetime.strptime(seg_list[3], "%Y-%m-%d %H:%M:%S")
        # 统计发表的topic数
        if uid in behavior and is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE):
            behavior[uid][1] += 1
        
    f.close()

def filter_user(behavior):
    """ 过滤掉某些活动非常少的用户
    具体的过滤规则如下：如果既没有发表过topic，而且发表评论的次数少于3次
    注意：目前暂不考虑user interest的相关的过滤规则
    """
    filtered_user_list = []
    for uid in behavior:
        num_comments = behavior[uid][0]
        num_topics = behavior[uid][1]
        if num_topics == 0 and num_comments < 2:
            filtered_user_list.append(uid)
            
    log.info('Number of filtered users: %d' % len(filtered_user_list))
    log.info('Remove the filtered user keys in interest_info and behavior...')
    for uid in filtered_user_list:
        behavior.pop(uid, None)
        
    log.info('Remove keys done.')
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = sys.argv[1]
    log.info('Prepare user behavior for group: %s' % group_id)
    
    print 'Loading users...'
    path = 'social/' + group_id + '/all-users-' + group_id
    uid_list = load_user_list(path)
    total_user = len(uid_list)
    log.info('Number of users loaded: %d' % total_user)
    print 'Number of users loaded: %d' % total_user
    
    print 'Gen user interest...'
    topic_path = 'tables/' + group_id + '/TopicInfo-raw-all-' + group_id
    comment_path = 'tables/' + group_id + '/CommentInfo-raw-all-' + group_id
    
    behavior_path = 'tables/' + group_id + '/behavior-' + group_id
    filtered_user_path = 'social/' + group_id + '/filtered-user-behavior-' + group_id
    
    # 如果user-interest或者behavior文件存在，则删除文件
    if os.path.exists(behavior_path):
        os.remove(behavior_path)

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
        behavior = get_interested_topic(puid_list, comment_path)
        gen_interest_text(puid_list, behavior, topic_path)
        # filter out users who contributed very few comments
        filter_user(behavior)
        # save to file
        save_behavior(behavior_path, behavior)
        # save the users that is not filtered
        for uid in behavior:
            ff.write(uid + '\n')
            user_count += 1
            
        start += count
    
    print 'Number of new user count after behavior filtered: %d' % user_count
    ff.close()

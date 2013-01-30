#encoding=utf8

"""
功能：找到user behavior feature，包括用户在训练时期内发表的topic数和comment数目
这个脚本负责：指定的group，浏览TopicInfo和CommentInfo
Note: Do one thing, do it well.
"""
from datetime import datetime
import logging
import os

from logconfig import congifLogger
from utils import is_between
from prepare import TRAIN_START_DATE, TRAIN_END_DATE
from prepare import TEST_START_DATE, TEST_END_DATE
from prepare import load_user_list

# config logging
log = logging.getLogger('Main.behavior')
congifLogger("behavior.log", 5)

def load_topic():
    """ 读入所有的topic信息
    Note：这里按照有title信息的格式来
    """
    log.info('Loading topic info...')
    # map topic_id --> dict()
    topic_dict = dict()
    f = open(TOPIC_ALL_FILE_PATH, 'r')
    ft = open(TOPIC_FILE_PATH, 'w') # 存储本group的topic
    row = ''
    for line in f:
        line = line.strip()
        if line != '[*ROWEND*]':
            row += line
            continue
        seg_list = row.split('[=]')
        if len(seg_list) == 6: # 没有title信息
            log.info('Title empty for topic: %s' % seg_list[0])
            seg_list.insert(4, '') # 将title信息置为空
        print 'Processing topic id: %s, group id: %s' % (seg_list[0], seg_list[1])
        pubdate = datetime.strptime(seg_list[3], "%Y-%m-%d %H:%M:%S")
        if seg_list[1] != GROUP_ID:
            row = ''
            continue
        # 记录下该topic信息
        topic = dict()
        topic['topic_id'] = seg_list[0]
        topic['group_id'] = seg_list[1]
        topic['user_id'] = seg_list[2]
        topic['pubdate'] = pubdate
        topic['title'] = seg_list[4]
        topic['content'] = seg_list[5]
        topic['comment_list'] = seg_list[6]
        
        topic_dict[topic['topic_id']] = topic
        
        ft.write(row + '\n[*ROWEND*]\n')
        row = ''
        #print "Loaded topic: " + topic[topic_id]
        
    log.info('Number of topics loaded: %d' % len(topic_dict))
    f.close()
    ft.close()
    
    return topic_dict
    
def get_behavior_statics(uid_list, topic_dict):
    """ 获取用户的行为信息
    """
    print '获取用户的行为信息...'
    behavior = dict()
    for uid in uid_list:
        behavior[uid] = [0, 0, ''] # [num_topics, num_comments, related-content]
        
    # 浏览所有的topic
    print '浏览所有的topic信息...'
    for topic_id in topic_dict:
        topic = topic_dict[topic_id]
        if topic['user_id'] in behavior:
            uid = topic['user_id']
            behavior[uid][0] += 1
            behavior[uid][2] += (topic['title'] + ' ' + topic['content'])
            
    print '浏览所有的留言信息...'
    f = open(COMMENT_ALL_FILE_PATH, 'r')
    # 保证本group的comment信息只抽取一遍
    if os.path.exists(COMMENT_FILE_PATH):
        fc = None
    else:
        fc = open(COMMENT_FILE_PATH, 'w') # 存储本group的comment
    row = ''
    for line in f:
        line = line.strip()
        if line != '[*ROWEND*]':
            row += line
            continue
        seg_list = row.split('[=]')
        #print 'Processing comment id: %s, group id: %s, topic id: %s' % (seg_list[0], seg_list[1], seg_list[2])
        pubdate = datetime.strptime(seg_list[4], "%Y-%m-%d %H:%M:%S")
        topic_id = seg_list[2] # 保证评论所在的topic被收录
        if seg_list[1] != GROUP_ID or (not topic_id in topic_dict):
            row = ''
            continue
        
        if fc != None and (is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE) or is_between(pubdate, TEST_START_DATE, TEST_END_DATE)):
            fc.write(row + '\n[*ROWEND*]\n')
        
        if is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE):
            uid = seg_list[3]
            if uid in behavior:
                behavior[uid][1] += 1
                # 如果用户评论了某个帖子，则认为用户对这个帖子有兴趣
                # 在这里，将帖子的标题和内容，都加入用户的感兴趣的内容中
                topic_id = seg_list[2]
                topic = topic_dict[topic_id]
                # 这里并没有包括引用的评论的内容
                behavior[uid][2] += (topic['title'] + ' ' + topic['content'] + ' ' + seg_list[6])
                
        row = ''
    
    f.close()
    if not fc is None:
        fc.close()
    
    return behavior
    
def save_behavior_statics(behavior, topic_count, comment_count):
    """ 保存所有的用户行为信息
    """
    # 在这里使用的是每次将行为信息添加到文件最后
    f = open(BEHAVIOR_FILE_PATH, 'a')
    for uid in behavior:
        f.write(uid + '[=]')
        f.write(str(behavior[uid][0]) + '[=]')
        f.write(str(behavior[uid][1]) + '[=]')
        f.write(behavior[uid][2] + '\n[*ROWEND*]\n')
        
        topic_count += behavior[uid][0]
        comment_count += behavior[uid][1]
        
    f.close()
    
    return (topic_count, comment_count)

def main():
    log.info('Loading user ids...')
    uid_list = load_user_list('tables/users.txt') # load users
    log.info('Loading user id, done.')
    
    # 导入所有group的topic
    topic_dict = load_topic()
    start = 0
    count = 100 # 一次处理100个用户
    total_users = len(uid_list)
    # 考虑到需要存储的内容较多，所以一次处理一定数目的用户
    topic_count = 0
    comment_count = 0
    while start < total_users:
        if start + count < total_users:
            puid_list = uid_list[start:(start + count)]
        else:
            puid_list = uid_list[start:]
            
        #print (start, start+count)
        behavior = get_behavior_statics(puid_list, topic_dict)
        # save to file
        topic_count, comment_count = save_behavior_statics(behavior, topic_count, comment_count)
        log.info('Processing uid range: [%d, %d)' % (start, start+count))
        
        start += count
    
    log.info('Total number of topics used: %d' % topic_count)
    log.info('Total number of comments used: %d' % comment_count)
    log.info('Thank God. It\'s done.')

if __name__ == '__main__':
    main()

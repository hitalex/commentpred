# encoding=utf-8

"""
准备所有的训练集和测试集：在每条topic后增加评论这条topic的所有用户
"""
import sys
import logging
from datetime import datetime
import codecs

from logconfig import congifLogger
from utils import is_between
from prepare import load_topic_user, load_comment_user
from prepare import TRAIN_START_DATE, TRAIN_END_DATE
from prepare import TEST_START_DATE, TEST_END_DATE

# config logging
log = logging.getLogger('Main.prepare_train_test')
congifLogger("prepare_train_test.log", 5)

# 抽取评论，截止某个日期
COMMENT_END_DATE = datetime(2013, 3, 1)

# Note: 这里需要将所有的topic和comment信息都导入到内存中

def main(argv):
    if len(argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = argv[1]
    log.info('Prepare training set and test set for group: %s' % group_id)
    
    path = 'tables/' + group_id + '/TopicInfo-raw-all-' + group_id
    topic_dict, topic_user_set = load_topic_user(path, TRAIN_START_DATE, TEST_END_DATE) # 取出所有topic
    print 'Number of topics loaded: %d (From %s to %s)' % (len(topic_dict), str(TRAIN_START_DATE), str(TEST_END_DATE))
    log.info('Number of topics loaded: %d (From %s to %s)' % (len(topic_dict), str(TRAIN_START_DATE), str(TEST_END_DATE)))
    
    path = 'tables/' + group_id + '/CommentInfo-raw-all-' + group_id
    comment_dict, comment_user_set = load_comment_user(path, topic_dict, TRAIN_START_DATE, COMMENT_END_DATE)
    print 'Number of comments loaded: %d (From %s to %s))' % (len(comment_dict), str(TRAIN_START_DATE), str(COMMENT_END_DATE))
    log.info('Number of comments loaded: %d (From %s to %s))' % (len(comment_dict), str(TRAIN_START_DATE), str(COMMENT_END_DATE)))
    
    print 'Finding comment users for topics...'
    # 在comment info中找到对于某个topic的评论id和评论用户
    for topic_id in topic_dict:
        topic = topic_dict[topic_id]
        topic['comment_set'] = set()
        topic['comment_user_set'] = set()
        
    for comment_id in comment_dict:
        comment = comment_dict[comment_id]
        topic_id = comment['topic_id']
        user_id = comment['user_id']
        if topic_id in topic_dict:
            topic = topic_dict[topic_id]
            topic['comment_set'].add(comment_id)
            topic['comment_user_set'].add(user_id)
    
    path = 'tables/' + group_id + '/train-topic-' + group_id
    train_topic_file = codecs.open(path, 'w', 'utf-8')
    path = 'tables/' + group_id + '/test-topic-' + group_id
    test_topic_file = codecs.open(path, 'w', 'utf-8')
    
    print 'Generating training and test dataset...'
    # 作为训练集和测试集的topic, comment数目
    train_topic_count = 0
    train_comment_count = 0
    test_topic_count = 0
    test_comment_count = 0
    user_set = set() # 保存所有出现在训练集和测试集中的用户id
    for topic_id, topic in topic_dict.iteritems():
        topic_creator = topic['user_id']
        pubdate = topic['pubdate']
        comment_user_set = topic['comment_user_set']
        log.info('Comment user number for topic %s is: %d' % (topic_id, len(comment_user_set)))
        if is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE):
            train_topic_count += 1
            train_comment_count += len(topic['comment_user_set'])
            f = train_topic_file
        elif is_between(pubdate, TEST_START_DATE, TEST_END_DATE):
            # 保证训练集中的评论用户数至少为5
            if len(topic['comment_user_set']) < 5:
                continue
            test_topic_count += 1
            test_comment_count += len(topic['comment_user_set'])
            f = test_topic_file
            
        user_set.add(topic_creator) # add topic creator
        user_set = user_set | topic['comment_user_set'] # add comment user set
        
        row = topic['topic_id'] + '[=]' + topic['group_id'] + '[=]' + \
            topic['user_id'] + '[=]' + str(topic['pubdate']) + '[=]' + \
            topic['title'] + '[=]' + topic['content'] + '[=]' + \
            ','.join(topic['comment_set']) + '[=]' + ','.join(topic['comment_user_set'])
        row += '\n'
        f.write(row)
        
    train_topic_file.close()
    test_topic_file.close()
    # write all user ids to file
    path = 'social/' + group_id + '/all-users-' + group_id
    print 'Writing user list to file: %s' % path
    f = codecs.open(path, 'w', 'utf-8')
    for uid in user_set:
        f.write(uid + '\n')
    f.close()
    print 'Total users in train and test set: %d' % len(user_set)
    
    print 'For training, number of topics: %d, number of commenting users: %d' % (train_topic_count, train_comment_count)
    print 'For test, number of topics: %d, number of commenting users: %d' % (test_topic_count, test_comment_count)
    print 'Done'

if __name__ == '__main__':
    main(sys.argv)

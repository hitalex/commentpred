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
from prepare import load_topic, load_comment

# 训练集和测试集的起止时间
TRAIN_START_DATE = datetime(2012, 10, 1)
TRAIN_END_DATE = datetime(2012, 12, 1)

TEST_START_DATE = datetime(2012, 12, 1)
TEST_END_DATE = datetime(2013, 1, 1)

# config logging
log = logging.getLogger('Main.prepare_train_test')
congifLogger("prepare_train_test.log", 5)

# 抽取评论，截止某个日期
COMMENT_END_DATE = datetime(2013, 3, 1)

def main(argv):
    if len(argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = argv[1]
    log.info('Prepare training set and test set for group: %s' % group_id)
    
    path = 'tables/' + group_id + '/TopicInfo-' + group_id + '-raw-part'
    topic_dict = load_topic(path, TRAIN_START_DATE, TEST_END_DATE) # 取出所有topic
    log.info('Number of topics loaded: %d' % len(topic_dict))
    
    path = 'tables/' + group_id + '/CommentInfo-' + group_id + '-raw-part'
    comment_dict = load_comment(path, topic_dict, TRAIN_START_DATE, COMMENT_END_DATE)
    log.info('Number of comments loaded: %d' % len(comment_dict))
    
    path = 'tables/' + group_id + '/train_topic.txt'
    train_topic_file = codecs.open(path, 'w', 'utf-8')
    path = 'tables/' + group_id + '/test_topic.txt'
    test_topic_file = codecs.open(path, 'w', 'utf-8')
    
    # 作为训练集和测试集的topic, comment数目
    train_topic_count = 0
    train_comment_count = 0
    test_topic_count = 0
    test_comment_count = 0
    for topic_id, topic in topic_dict.iteritems():
        pubdate = topic['pubdate']
        comment_list = topic['comment_list'].split(',')
        if is_between(pubdate, TRAIN_START_DATE, TRAIN_END_DATE):
            train_topic_count += 1
            train_comment_count += len(comment_list)
            f = train_topic_file
        elif is_between(pubdate, TEST_START_DATE, TEST_END_DATE):
            test_topic_count += 1
            test_comment_count += len(comment_list)
            f = test_topic_file
        uid_list = []
        for cid in comment_list:
            if cid in comment_dict:
                uid_list.append(comment_dict[cid]['user_id'])
        row = topic['topic_id'] + '[=]' + topic['group_id'] + '[=]' + \
            topic['user_id'] + '[=]' + str(topic['pubdate']) + '[=]' + \
            topic['title'] + '[=]' + topic['content'] + '[=]' + \
            topic['comment_list'] + '[=]' + ','.join(uid_list)
        row += '\n'
        f.write(row)
        
    train_topic_file.close()
    test_topic_file.close()
    log.info('For training, number of topics: %d, number of comments: %d' % (train_topic_count, train_comment_count))
    log.info('For test, number of topics: %d, number of comments: %d' % (test_topic_count, test_comment_count))

if __name__ == '__main__':
    main(sys.argv)

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
    
    path = 'tables/' + group_id + '/TopicInfo-' + group_id + '-raw-part'
    topic_dict, topic_user_set = load_topic_user(path, TRAIN_START_DATE, TEST_END_DATE) # 取出所有topic
    log.info('Number of topics loaded: %d' % len(topic_dict))
    
    path = 'tables/' + group_id + '/CommentInfo-' + group_id + '-raw-part'
    comment_dict, comment_user_set = load_comment_user(path, topic_dict, TRAIN_START_DATE, COMMENT_END_DATE)
    log.info('Number of comments loaded: %d' % len(comment_dict))
    
    # 找到所有出现的用户，并输出到文件
    # 这里说的“所有用户”包括所有出现在训练和测试集中用户，作为candidate set
    user_set = topic_user_set | comment_user_set
    now = datetime.now()
    path = 'social/' + group_id + '/all-users-' + str(now)
    print 'Writing user list to file...'
    f = codecs.open(path, 'w', 'utf-8')
    for uid in user_set:
        f.write(uid + '\n')
    f.close()
    log.info('Total users in train and test set: %d' % len(user_set))
    
    path = 'tables/' + group_id + '/train_topic'
    train_topic_file = codecs.open(path, 'w', 'utf-8')
    path = 'tables/' + group_id + '/test_topic'
    test_topic_file = codecs.open(path, 'w', 'utf-8')
    
    print 'Generating training and test dataset...'
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
    print 'Done'

if __name__ == '__main__':
    main(sys.argv)

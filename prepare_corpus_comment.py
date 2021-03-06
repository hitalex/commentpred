# encoding=utf-8

"""
此脚本需要完成的任务是：准备topic model需要的所有训练文本
这里的训练文本包括：所有topic的title、content内容以及每个topic下的comment,时间范围是所有的讨论贴
主要方法：
依次调入不同的topicinfo和对应的comment info，分别进行处理
需要注意的是：在这里将topic内容以及所属的comment作为一个document来处理。
"""

import sys
import logging
import codecs
from datetime import datetime
import re

from logconfig import congifLogger
from prepare_corpus import remove_url, seg_chinese
from patterns import REURL

# config logging
log = logging.getLogger('Main.prepare_corpus_comment')
congifLogger("prepare_corpus_comment.log", 5)

def load_topic_text(path):
    f = codecs.open(path, 'r', 'utf-8')
    topic_dict = dict()
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        topic_id = seg_list[0]
        title = remove_url(seg_list[3])
        content = remove_url(seg_list[5])
        text = seg_chinese(title) + ' ' + seg_chinese(content)
        topic_dict[topic_id] = text
        
    f.close()
    return topic_dict
    
def load_comment_text(path, topic_dict):
    f = codecs.open(path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        topic_id = seg_list[2]
        content = remove_url(seg_list[6])
        if topic_id in topic_dict:
            topic_dict[topic_id] += (' ' + seg_chinese(content))

    f.close()
    
def load_group_info(path, topic_dict):
    """ 将小组的介绍作为一个文档
    """
    f = codecs.open(path, 'r', 'utf-8')
    row = f.readline()
    desc = (row.split('[=]'))[3]
    desc = remove_url(desc)
    
    topic_dict['0'] = seg_chinese(desc)
    
    f.close()
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = sys.argv[1]
    log.info('Prepare corpus with comment for group: %s' % group_id)
    
    outf = codecs.open('tables/' + group_id + '/corpus-topic-comment', 'w', 'utf-8')
    
    """
    num = 9
    topic_base_path = 'tables/' + group_id + 'ustv/sep/TopicInfo-ustv-raw-'
    comment_base_path = 'tables/ustv/sep/CommentInfo-ustv-raw-'
    
    for index in range(0, num):
        topic_path = topic_base_path + str(index)
        comment_path = comment_base_path + str(index)
        log.info('Loading topic info: %s' % topic_path)
        topic_dict = load_topic_text(topic_path)
        log.info('Number of topics: %d' % len(topic_dict))
        
        log.info('Loading comment info: %s' % comment_path)
        text_dict = load_comment_text(comment_path, topic_dict)
        
        for topic_id in text_dict:
            text = text_dict[topic_id]
            outf.write(text + '\n')
    """
    topic_path = 'tables/' + group_id + '/TopicInfo-raw-all-' + group_id
    comment_path = 'tables/' + group_id + '/CommentInfo-raw-all-' + group_id
    group_info_path = 'tables/' + group_id + '/GroupInfo-' + group_id
    
    print 'Loading topic dict ...'
    topic_dict = load_topic_text(topic_path)
    log.info('Number of topics: %d' % len(topic_dict))
    
    print 'Loading topic comments...'
    load_comment_text(comment_path, topic_dict)
    
    print 'Loading group info...'
    load_group_info(group_info_path, topic_dict)
    
    print 'Saving whole document...'
    for topic_id in topic_dict:
        text = topic_dict[topic_id]
        outf.write(text + '\n')
        
    outf.close()
    log.info('Done')

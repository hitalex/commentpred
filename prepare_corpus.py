# encoding=utf-8

"""
此脚本需要完成的任务是：准备topic model需要的所有训练文本
这里的训练文本包括：所有topic的title、content内容(并不包括comment),时间范围是所有的讨论贴
"""

import sys
import logging
import codecs
from datetime import datetime
import re

import jieba

from logconfig import congifLogger
from prepare import TRAIN_START_DATE, TRAIN_END_DATE
from prepare import TEST_START_DATE, TEST_END_DATE
from prepare import VERY_EARLY_TIME, VERY_LATE_TIME
from patterns import REURL

# config logging
log = logging.getLogger('Main.prepare_corpus')
congifLogger("prepare_corpus.log", 5)


def remove_url(text):
    while True:
        obj = REURL.search(text)
        if obj is None:
            break
        text = text.replace(obj.group(0), '')
        
    return text
    
def seg_chinese(text):
    seg_list = jieba.cut(text)
    return ' '.join(seg_list)

def main(argv):
    if len(argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = argv[1]
    log.info('Prepare corpus for group: %s' % group_id)
    
    log.info('Loading user dict...')
    jieba.load_userdict('dataset/user_dict-' + group_id + '.txt')
    log.info('Done')
    
    #now = datetime.now()
    corpus_path = 'tables/' + group_id + '/corpus-title-only'
    group_info_path = 'tables/' + group_id + '/GroupInfo-' + group_id
    topic_path = 'tables/' + group_id + '/TopicInfo-' + group_id + '-raw-all-new'
    comment_path = 'tables/' + group_id + '/CommentInfo-' + group_id + '-raw-all-new'
    
    corpusf = codecs.open(corpus_path, 'w', 'utf-8')
    # 加入小组的简介
    f = codecs.open(group_info_path, 'r', 'utf-8')
    row = f.read()
    row = row.strip()
    seg_list = row.split('[=]')
    desc = seg_list[3]
    corpusf.write(desc + '\n')
    
    # 加入topic相关信息
    log.info('Loading topic info from %s' % topic_path)
    count = 0 # 被载入的topic数量
    f = codecs.open(topic_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if len(seg_list) != 6:
            log.warning('Bad topic: %s' % line)
            continue
        title = seg_list[3]
        content = seg_list[5]
        seg_list = jieba.cut(title)
        title = remove_url(title)
        corpusf.write(' '.join(seg_list) + ' ') # title
        # 去除url和图片链接
        content = remove_url(content)
        seg_list = jieba.cut(content)
        corpusf.write(' '.join(seg_list) + '\n') # content
        count += 1
    log.info('Number of topics loaded: %d' % count)
    
    """
    log.info('Loading comment info from %s' % comment_path)
    f = codecs.open(comment_path, 'r', 'utf-8')
    count = 0
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if len(seg_list) != 7:
            log.warning('Bad comments: %s' % line)
            continue
        content = seg_list[6]
        seg_list = jieba.cut(content)
        corpusf.write(' '.join(seg_list) + ' ') # comment.content
        count += 1
        # 100 comments in one line
        if count % 100 == 0:
            corpusf.write('\n')
    f.close()
    log.info('Number of comments loaded: %d' % count)
    """
    corpusf.close()

if __name__ == '__main__':
    main(sys.argv)

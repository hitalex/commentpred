# encoding=utf-8

"""
此脚本需要完成的任务是：准备topic model需要的所有训练文本
这里的训练文本包括：所有topic的title、content和comment内容；时间范围是训练集的范围
"""

import sys
import logging
import codecs

from logconfig import congifLogger

from prepare import TRAIN_START_DATE, TRAIN_END_DATE
from prepare import TEST_START_DATE, TEST_END_DATE
from prepare import VERY_EARLY_TIME, VERY_LATE_TIME

# config logging
log = logging.getLogger('Main.prepare_corpus')
congifLogger("prepare_corpus.log", 5)

def main(argv):
    if len(argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = argv[1]
    log.info('Prepare corpus for group: %s' % group_id)
    
    corpus_path = 'tables/' + group_id + '/corpus.txt'
    group_info_path = 'tables/' + group_id + '/GroupInfo-' + group_id + '.txt'
    topic_path = 'tables/' + group_id + '/TopicInfo-' + group_id + '.txt'
    comment_path = 'tables/' + group_id + '/CommentInfo-' + group_id + '.txt'
    
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
        corpusf.write(seg_list[3] + ' ') # title
        corpusf.write(seg_list[5] + '\n') # content
        count += 1
    log.info('Number of topics loaded: %d' % count)
    
    log.info('Loading comment info from %s' % comment_path)
    f = codecs.open(comment_path, 'r', 'utf-8')
    count = 0
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if len(seg_list) != 7:
            log.warning('Bad comments: %s' % line)
            continue
        corpusf.write(seg_list[6] + ' ') # comment.content
        count += 1
        # 100 comments in one line
        if count % 100 == 0:
            corpusf.write('\n')
    f.close()
    log.info('Number of comments loaded: %d' % count)
    
    corpusf.close()

if __name__ == '__main__':
    main(sys.argv)

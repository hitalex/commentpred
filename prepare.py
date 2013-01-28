#encoding=utf-8

"""
这里包含了一些准备数据集需要用到的函数和变量
"""

from datetime import datetime
import codecs
import logging

from utils import is_between
from logconfig import congifLogger

# config logging
log = logging.getLogger('Main.prepare')
congifLogger("prepare.log", 5)

# 设置最早和最晚的年限
VERY_EARLY_TIME = datetime(1900, 1, 1)
VERY_LATE_TIME = datetime(2050, 1, 1)

def load_topic(filepath, start_date = VERY_EARLY_TIME, end_date = VERY_LATE_TIME):
    """ 根据时间范围，导入所有的topic
    注意：topic可能有commentlist或者没有
    """
    print 'Loading topic from %s' % filepath
    f = codecs.open(filepath, 'r', 'utf-8')
    # map topic_id --> dict()
    topic_dict = dict()
    count = 0
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if len(seg_list) != 7:
            log.info('Bad formatted topic: %s' % line)
            count += 1
            continue
        #print 'Processing topic id: %s, group id: %s' % (seg_list[0], seg_list[1])
        pubdate = datetime.strptime(seg_list[3], "%Y-%m-%d %H:%M:%S")
        if not is_between(pubdate, start_date, end_date):
            continue
        # 记录下该topic信息
        topic = dict()
        topic['topic_id'] = seg_list[0]
        topic['group_id'] = seg_list[1]
        topic['user_id'] = seg_list[2]
        topic['pubdate'] = pubdate
        topic['title'] = seg_list[4]
        topic['content'] = seg_list[5]
        # 去掉最后的逗号
        if len(seg_list) == 7: # 如果包含comment_list
            s = seg_list[6]
            if s != ''  and s[-1] == ',':
                seg_list[6] = s[0:-1]
            topic['comment_list'] = seg_list[6]
        else:
            topic['comment_list'] = ''
        
        topic_dict[topic['topic_id']] = topic
        #print "Loaded topic: " + topic[topic_id]
        
    log.info('Number of bad formatted topic: %d' % count)
        
    f.close()
    
    return topic_dict
    
def load_comment(filepath, topic_dict, start_date = VERY_EARLY_TIME, end_date = VERY_LATE_TIME):
    """ 根据时间范围，导入所有的评论id，tpic id和内容
    注意：在这里仍然需要topic_dict，因为只有在topic_dict中的comment才会被收集
    """
    print 'Loading comment from %s' % filepath
    f = codecs.open(filepath, 'r', 'utf-8')
    comment_dict = dict()
    count = 0
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if len(seg_list) != 7:
            log.info('Bad formatted comment: %s' % line)
            count += 1
            continue
        #print 'Processing comment id: %s, group id: %s, topic id: %s' % (seg_list[0], seg_list[1], seg_list[2])
        pubdate = datetime.strptime(seg_list[4], "%Y-%m-%d %H:%M:%S")
        topic_id = seg_list[2]
        if topic_id in topic_dict and is_between(pubdate, start_date, end_date):
            pass
        else:
            continue
            
        comment = dict()
        comment['comment_id'] = seg_list[0]
        comment['group_id'] = seg_list[1]
        comment['topic_id'] = seg_list[2]
        comment['user_id'] = seg_list[3]
        pubdate = datetime.strptime(seg_list[4], "%Y-%m-%d %H:%M:%S")
        comment['pubdate'] = pubdate
        comment['ref_comment_id'] = seg_list[5]
        comment['content'] = seg_list[6]
        
        comment_dict[comment['comment_id']] = comment
        
    log.info('Number of bad formatted comment: %d' % count)
    return comment_dict

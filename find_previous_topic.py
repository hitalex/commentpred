#coding:utf8

"""
此脚本找到之前已经抓取的topic list，并重新保存topic和comment信息
"""

import codecs

topics_all = set()
topics_remain = set()

def get_topic_set(path):
    f = codecs.open(path, 'r', 'utf-8')
    tset = set()
    for tid in f:
        tid = tid.strip()
        if tid != "":
            tset.add(tid)
            
    return tset
    
topics_all = get_topic_set('tables/ustv/TopicList-ustv-all.txt')
topics_remain = get_topic_set('tables/ustv/TopicList-ustv-remain.txt')

topic_list = topics_all - topics_remain
print 'Previous topics: %d' % len(topic_list)

def write_topic_info(tablename, source_file_path, dest_file_path):
    global topic_list
    
    sf = codecs.open(source_file_path, 'r', 'utf-8')
    df = codecs.open(dest_file_path, 'w', 'utf-8')
    
    # 存在重复的存储
    tlist = set(topic_list)
    count = 0
    for line in sf:
        line = line.strip()
        row = line.split('[=]')
        if row[0] in tlist:
            tlist.remove(row[0])
            df.write(line + '\n')
            count += 1
    print 'Topics loaded: %d' % count
    print 'Topics not loaded: %d' % len(tlist)
    
def write_comment_info(tablename, source_file_path, dest_file_path):
    global topic_list
    
    sf = codecs.open(source_file_path, 'r', 'utf-8')
    df = codecs.open(dest_file_path, 'w', 'utf-8')
    
    cid_set = set()
    count = 0
    for line in sf:
        line = line.strip()
        row = line.split('[=]')
        if row[2] in topic_list and (not row[0] in cid_set):
            cid_set.add(row[0])
            df.write(line + '\n')
            count += 1
    print 'Comments loaded: %d' % len(cid_set)

#write_topic_info('TopicInfo', 'tables/ustv/TopicInfo-ustv-title.txt', 'tables/ustv/TopicInfo-raw-part-new.txt')
#write_comment_info('CommentInfo', 'tables/ustv/CommentInfo-raw-part.txt', 'tables/ustv/CommentInfo-raw-part-new.txt')

def write_comment_info2(topic_dict, source_file_path, dest_file_path):
    sf = codecs.open(source_file_path, 'r', 'utf-8')
    df = codecs.open(dest_file_path, 'w', 'utf-8')
    
    for line in sf:
        line = line.strip()
        row = line.split('[=]')
        if row[2] in topic_dict:
            df.write(line + '\n')
            
from prepare import load_topic
topic_dict = load_topic('tables/ustv/TopicInfo-raw-part-with-title.txt')
write_comment_info2(topic_dict, 'tables/ustv/CommentInfo-ustv-raw-part.txt', 'tables/ustv/CommentInfo-ustv-raw-part-new.txt')

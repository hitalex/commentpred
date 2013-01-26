#coding:utf8

"""
从一个文件读入所有topic的title，然后添加入另外一个没有title的topic info中
"""

import codecs

# 读入title
path = 'tables/ustv/TopicInfo-ustv-raw-part.txt'
f = codecs.open(path, 'r', 'utf-8')
# topic_id ==> title
topic_title = dict()
# 读入title信息
for line in f:
    line = line.strip()
    seg_list = line.split('[=]')
    topic_id = seg_list[0]
    title = seg_list[4]
    topic_title[topic_id] = title
f.close()

path = 'tables/ustv/TopicInfo-raw-part-without-title.txt'
fwithout = codecs.open(path, 'r', 'utf-8')
path = 'tables/ustv/TopicInfo-raw-part-with-title.txt'
fnew = codecs.open(path, 'w', 'utf-8')
# 写入新文件
for line in fwithout:
    line = line.strip()
    seg_list = line.split('[=]')
    if len(seg_list) != 6:
        print 'Bad topic format: %s' % line
        continue
    topic_id = seg_list[0]
    if topic_id in topic_title:
        title = topic_title[topic_id]
        seg_list.insert(4, title)
        # 去掉comment list最后的逗号
        clist = seg_list[-1]
        if clist !='' and clist[-1] == ',':
            seg_list[-1] = clist[0:-1]
        fnew.write('[=]'.join(seg_list) + '\n')
        
fwithout.close()
fnew.close()

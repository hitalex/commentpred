#coding:utf8

"""
此脚本用户将目前已经抓取的topic id读入，然后从所有的topic list中除去，
生成还未抓取的新的topic list
"""

import datetime

from prepare import load_topic, load_comment

current_topic_dict = load_topic('tables/ustv/TopicInfo-ustv.txt')

f = open('tables/ustv/TopicList-ustv-all.txt', 'r')
fn = open('tables/ustv/TopicList-ustv-remain.txt', 'w')
for line in f:
    line = line.strip()
    if not line in current_topic_dict:
        fn.write(line + '\n')
        
f.close()
fn.close()

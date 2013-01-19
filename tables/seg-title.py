#coding:utf8

"""
为TopicInfo-all.txt中的title进行中文分词
"""

import codecs
import pdb

import jieba

def seg_chinese(chinese_str):
    """中文分词
    Note: 目前采用jieba分词. jieba项目主页：https://github.com/fxsjy/jieba
    """
    seg_list = jieba.cut(chinese_str)
    return " ".join(seg_list)
    
fs = codecs.open('TopicInfo-all.txt', 'r', 'utf-8')
fd = codecs.open('TopicInfo-all-seg.txt', 'w', 'utf-8')

row = ''
for line in fs:
    line = line.strip()
    if line != '[*ROWEND*]':
        row += line
        continue
    seg_list = row.split('[=]')
    title = seg_chinese(seg_list[4])
    seg_list[4] = title
    row = "[=]".join(seg_list)
    fd.write(row + '\n[*ROWEND*]\n')
    row = ''
    
fs.close()
fd.close()

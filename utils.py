#encoding=utf8

import jieba

def seg_chinese(chinese_str):
    """中文分词
    Note: 目前采用jieba分词. jieba项目主页：https://github.com/fxsjy/jieba
    """
    seg_list = jieba.cut(chinese_str)
    return " ".join(seg_list)

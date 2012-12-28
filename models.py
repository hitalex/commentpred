# -*- coding: utf-8 -*-

#! /usr/bin/env python
import sys
# 更改python的默认编码为utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

import re
from datetime import datetime
from lxml import etree # use XPath from lxml

# for debug
import pdb

"""
在这里，我将定义会用到的类和数据结构，包括小组、topic和评论。它们之间的关系为：
一个小组包括一些topic，每个评论包括一些评论
注意：
所有的文本全部用UTF-8来编码
"""

class Comment(object):
    """评论的类
    """
    def __init__(self, cid, user_id, pubdate, content, quote_id, topic_id, group_id):
        self.cid = cid              # 评论id
        self.user_id = user_id      # 发评论的人的id
        self.pubdate = pubdate      # 发布时间
        self.content = content      # 评论内容，不包括引用评论的内容
        self.quote_id = quote_id    # 引用他人评论的id
        
        self.topic_id = topic_id    # 所在topic的id
        self.group_id = group_id    # 所在小组的id
        
        
        
class Topic(object):
    """小组中的某个话题
    """
    def __init__(self, topic_id, group_id, first_page, nonfirst_page):
        self.topic_id = topic_id    # 该topic的id
        self.user_id = ""           # 发布topic的人的id
        self.user_name = ""         # 用户的昵称
        self.pubdate = ""           # 该topic发布的时间
        self.title = ""             # 该topic的标题
        self.content = ""           # topic的内容
        self.comment_list = []      # 所有评论的id列表
        
        self.group_id = group_id    # 所在小组的id
        
        self.first_page = first_page        # 测试用，首页
        self.nonfirst_page = nonfirst_page  # 测试用，非首页
        
        # 用户匹配用户id
        self.pattern = re.compile("^http://www.douban.com/people/([0-9, a-z, A-Z, _, \-]+)/$")
        
        # 抽取信息
        self.extract_info()
        
    def extract_info(self):
        """ 从网页中抽取信息，填写类中的字段
        @param strformat 字符串格式的数据
        """
        # 抽取topic首页的内容
        self.extract_first_page()
        # 抽取topic非首页的内容
        self.extract_nonfirst_page()
        
    def extract_first_page(self):
        # 抽取topic首页的内容
        url = "http://www.douban.com/group/topic/" + self.topic_id + "/"
        print "Reading webpage: " + url
        #self.first_page = self.first_page.replace("<br/>", "")
        #self.first_page = self.first_page.replace("<br>", "")

        page = etree.HTML(self.first_page.decode('utf-8'))
        content = page.xpath(u"/html/body/div[@id='wrapper']/div[@id='content']")[0]
        # 找到标题：如果标题太长，那么标题会被截断，原标题则会在帖子内容中显示
        # 如果标题不被截断，则原标题不会在帖子内容中显示
        tmp = page.xpath(u"//table[@class='infobox']//td[class='tablecc']")
        if len(tmp) == 0:
            # 标题没有被截断
            self.title = content.xpath("h1")[0].text.strip()
        else:
            self.title = tmp[0].text.strip().replace(u"<strong>标题：</strong>", "")
        
        self.title = unicode(self.title.replace(u"<strong>标题：</strong>", ""))
        
        lz = page.xpath(u"//div[@class='topic-doc']/h3/span[@class='from']/a")[0]
        self.user_name = lz.text.strip()
        url = lz.attrib['href']
        #print url
        match_obj = self.pattern.match(url)
        assert(match_obj is not None)
        self.user_id = match_obj.group(1)
        strtime = content.xpath(u"//div[@class='topic-doc']/h3/span[@class='color-green']")[0].text
        self.pubdate = datetime.strptime(strtime, "%Y-%m-%d %H:%M:%S")
        
        # 帖子内容
        pnode = page.xpath(u"//div[@class='topic-content']/p")[0]
        self.content = etree.tostring(pnode, method='text', encoding='utf-8').strip()
        
        comments_li = page.xpath(u"//li[@class='clearfix comment-item']")
        print "Number of comments: ", str(len(comments_li))
        for cli in comments_li:
            comment = self.extract_comment(cli)
            self.comment_list.append(comment)
        
    def extract_comment(self, cli):
        # 从comment节点中抽取出Comment结构，并返回Comment对象
        #pdb.set_trace()
        cid = cli.attrib['data-cid']
        img = cli.xpath("div[@class='user-face']//img[@class='pil']")[0]
        user_name = img.attrib['alt']
        
        nodea = cli.xpath("div[@class='user-face']/a")[0]
        user_id = self.extract_user_id(nodea.attrib['href'])
        pnode = cli.xpath("div[@class='reply-doc content']/p")[0]
        content = unicode(etree.tostring(pnode, method='text', encoding='utf-8')).strip()
        # 发布时间
        strtime = cli.xpath("div[@class='reply-doc content']//span[@class='pubtime']")[0].text
        pubdate = datetime.strptime(strtime, "%Y-%m-%d %H:%M:%S")
        
        # 判断是否有引用其他回复
        quote_id = ""
        quote_node = cli.xpath("div[@class='reply-doc content']/div[@class='reply-quote']")
        if (quote_node is not None) and (len(quote_node) > 0):
            quote_content_all = quote_node[0].xpath("span[@class='all']")[0].text.strip()
            url = quote_node[0].xpath("span[@class='pubdate']/a")[0].attrib['href']
            quote_user_id = self.extract_user_id(url)
            # 找到引用的回复的comment id
            quote_id = self.find_previous_comment(quote_content_all, quote_user_id)
            if quote_id == "":
                pdb.set_trace()
                
        comment = Comment(cid, user_id, pubdate, content, quote_id, self.topic_id, self.group_id)
        #print "Comment content: ", comment.content
        return comment
        
    def extract_user_id(self, url):
        # 从用户链接中抽取出用户id
        match_obj = self.pattern.match(url)
        if match_obj is None:
            pdb.set_trace()
        return match_obj.group(1)
        
    def find_previous_comment(self, content, user_id):
        # 根据引用的内容和user id，找到引用的评论的id
        # 比较内容时，不考虑其中的换行符
        content = content.replace("\n", "")
        for comment in self.comment_list:
            tmp = comment.content.replace("\n", "")
            if content == tmp and user_id == comment.user_id:
                return comment.cid
                
        # not found, but should be found
        return ""
    def extract_nonfirst_page(self):
        # 抽取topic非首页的内容
        # 如果第一页的评论数不足100，则不可能有第二页评论
        if len(self.comment_list) < 100:
            return 
            
        
        return ""
        
        
class Group(object):
    """小组类
    """
    def __init__(self, group_id, user_id, pubdate, desc, topic_list):
        self.group_id = group_id    # 小组的id
        self.user_id = user_id      # 创建小组的user id
        self.pubdate = pubdate      # 小组创建的时间
        self.desc = desc            # 小组的介绍
        self.topic_list = topic_list    # 小组中的topic id列表
        
if __name__ == "__main__":
    #f = open("./testpage/求掀你的英语怎样从烂到无底洞到变强人的！！！.html")
    f = open(u"./testpage/标题：【手机行业】你不得不知道的手机内幕(非专业....html", "r")
    strfile = f.read()
    f.close()
    topic = Topic('31195872', 'insidestory', strfile, u"")
    
    """
    print "Topic id: ", topic.topic_id
    print "Group id: ", topic.group_id
    print "Title: ", topic.title
    print "User id: ", topic.user_id
    print "User name: ", topic.user_name
    print "Time: ", topic.pubdate
    print "topic content: ", topic.content
    """

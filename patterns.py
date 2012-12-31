#coding:utf8

# 这里存放所有用于匹配的正则表达式

import re

# 用户的主页链接, group(1)为用户id
REPeople = re.compile("^http://www.douban.com/people/([0-9, a-z, A-Z, _, \-, \.]+)/$")

# 小组首页链接, group(1)为小组id
REGroup = re.compile("^http://www.douban.com/group/([0-9, a-z, A-Z, _, \-, \.]+)/$")

# Topic页面链接, group(1)为topic id
RETopic = re.compile("^http://www.douban.com/group/topic/([0-9]+)/$")

# 小组讨论列表的链接, group(1)为小组id，group(2)为start
REDiscussion = re.compile("^http://www.douban.com/group/([0-9,a-z,A-Z,\-,_,\.]+)/discussion\?start=([0-9]+)$")

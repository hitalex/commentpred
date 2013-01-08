#coding:utf8

"""
根据已经抓取到的Group id，抓取每个group的topic列表
"""

from urlparse import urljoin,urlparse
from collections import deque
from threading import Lock
import traceback
import logging
import time
import pdb
import codecs # for file encodings

from bs4 import BeautifulSoup 
from lxml import etree # use XPath from lxml

from webPage import WebPage
from threadPool import ThreadPool
from patterns import *
from models import Group
from database import Database

import stacktracer

def congifLogger(logFile, logLevel):
    '''配置logging的日志文件以及日志的记录等级'''
    logger = logging.getLogger('Main')
    LEVELS={
        1:logging.CRITICAL, 
        2:logging.ERROR,
        3:logging.WARNING,
        4:logging.INFO,
        5:logging.DEBUG,#数字越大记录越详细
        }
    formatter = logging.Formatter(
        '%(asctime)s %(threadName)s %(levelname)s %(message)s')
    try:
        fileHandler = logging.FileHandler(logFile)
    except IOError, e:
        return False
    else:
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)
        logger.setLevel(LEVELS.get(logLevel))
        return True

log = logging.getLogger('Main.TopicCrawler')


class TopicCrawler(object):

    def __init__(self, groupIDList, threadNum):
        
        #线程池,指定线程数
        self.threadPool = ThreadPool(threadNum)  
        # 写数据库的线程
        self.DBThread = ThreadPool(1)
        
        # 已经访问的页面: Group id ==> True or False
        self.visitedHref = set()
        #待访问的小组讨论页面
        self.unvisitedHref = deque()
        # 访问失败的页面链接
        self.failedHref = set()
        
        self.lock = Lock() #线程锁
        
        self.groupIDList = groupIDList
        # 当前正在处理的小组id
        self.currentGroupID = ""
        
        # 抓取结束有两种可能：1）抓取到的topic数目已经最大；2）已经将所有的topic全部抓取
        # 只保存topic id
        self.topicList = list()
        # map group id ==> group info and stick topic list
        self.groupDict = dict()

        self.isCrawling = False
        
        self.database =  Database("DoubanGroup.db")
        
        # 每个Group抓取的最大topic个数
        #self.MAX_TOPICS_NUM = 50
        self.MAX_TOPICS_NUM = float('inf')
        # 每一页中显示的最多的topic数量，似乎每页中不一定显示25个topic
        #self.MAX_TOPICS_PER_PAGE = 25

    def start(self):
        print '\nStart Crawling topic list...\n'
        self.isCrawling = True
        self.threadPool.startThreads() 
        
        # 逐次处理每个小组
        for group_id in self.groupIDList:
            self.currentGroupID = group_id
            url = "http://www.douban.com/group/" + group_id + "/"
            print "Add start url:", url
            self.unvisitedHref.append(url)
            url = "http://www.douban.com/group/" + group_id + "/discussion?start=0"
            print "Add start urls:", url
            self.unvisitedHref.append(url)
            #分配任务,线程池并发下载当前深度的所有页面（该操作不阻塞）
            self._assignInitTask()
            #等待当前线程池完成所有任务,当池内的所有任务完成时，才进行下一个小组的抓取
            #self.threadPool.taskJoin()可代替以下操作，可无法Ctrl-C Interupt
            while self.threadPool.getTaskLeft() > 0:
                #print "Task left: ", self.threadPool.getTaskLeft()
                time.sleep(3)
            # 存储抓取的结果
            print "Stroring crawling topic list for: " + group_id
            self._saveTopicList()
            # 写入数据库
            self.database.saveGrouInfo(self.groupDict[self.currentGroupID], self.topicList)
            
            print "Processing done with group: " + group_id
            log.info("Topic list crawling done with group %s.", group_id)
        self.stop()
        assert(self.threadPool.getTaskLeft() == 0)
        print "Main Crawling procedure finished!"

    def stop(self):
        self.isCrawling = False
        self.threadPool.stopThreads()
        
    def _saveTopicList(self):
        """将抽取的结果存储在文件中
        Note: 这次是将存储过程放在主线程，将会阻塞抓取过程
        """
        group_id = self.currentGroupID
        this_group = self.groupDict[group_id]
        print "For group %s: number of Stick post: %d, number of regurlar post: %d, total topics is: %d." % \
            (group_id, len(this_group.stick_topic_list), len(self.topicList), len(this_group.stick_topic_list)+len(self.topicList))

        f = open("data/"+group_id+".txt", "w")
        for tid in this_group.stick_topic_list:
            f.write(tid + "\n")
            
        f.write("\n")
        for tid in self.topicList:
            f.write(tid + "\n")
            
        f.close()
        
        # 将访问失败的网页存储起来
        f = open("data/" + group_id + "_failed.txt", "w")
        for href in self.failedHref:
            f.write(href + "\n")
        f.close()
        
        self.topicList = list()
        self.failedHref = set()
        
        
    def getAlreadyVisitedNum(self):
        #visitedGroups保存已经分配给taskQueue的链接，有可能链接还在处理中。
        #因此真实的已访问链接数为visitedGroups数减去待访问的链接数
        if len(self.visitedHref) == 0:
            return 0
        else:
            return len(self.visitedHref) - self.threadPool.getTaskLeft()

    def _assignInitTask(self):
        """取出一个线程，并为这个线程分配任务，即抓取网页
        """ 
        while len(self.unvisitedHref) > 0:
            # 从未访问的列表中抽出一个任务，并为其分配thread
            url = self.unvisitedHref.popleft()
            self.threadPool.putTask(self._taskHandler, url)
            # 添加已经访问过的小组id
            self.visitedHref.add(url)
            
    def _taskHandler(self, url):
        """ 根据指定的url，抓取网页，并进行相应的访问控制
        """

        print "Visiting : " + url
        webPage = WebPage(url)
        # 抓取页面内容
        flag = webPage.fetch()
        if flag:
            url, pageSource = webPage.getDatas()
            # 抽取小组主页的置顶贴
            match_obj = REGroup.match(url)
            if match_obj is not None:
                group_id = match_obj.group(1)
                # 添加置顶贴的topic列表
                self._addStickTopic(webPage)
                return True
            
            # 抽取普通讨论贴
            match_obj = REDiscussion.match(url)
            if match_obj is not None:
                group_id = match_obj.group(1)
                start = int(match_obj.group(2))
                
                self._addTopicLink(webPage, start)
                return True
                
            log.error("抓取小组讨论列表时，发现网址格式错误。Group ID: %s, URL: %s" % (self.currentGroupID, url))
            
        # if page reading fails
        self.failedHref.add(url)
        return False

    def _addStickTopic(self, webPage):
        """ 访问小组首页，添加置顶贴
        """
        #pdb.set_trace()
        
        group = Group(self.currentGroupID)
        group.parse(webPage)
        
        self.groupDict[self.currentGroupID] = group
        
        
    def _addTopicLink(self, webPage, start):
        '''将页面中所有的topic链接放入对应的topic列表，并同时加入
        下一步要访问的页面
        '''
        #对链接进行过滤:1.只获取http或https网页;2.保证每个链接只访问一次
        #pdb.set_trace()
        url, pageSource = webPage.getDatas()
        hrefs = self._getAllHrefsFromPage(url, pageSource)
        # 找到有效的链接
        topic_list = []
        for href in hrefs:
            # 只有满足小组topic链接格式的链接才会被处理
            match_obj = RETopic.match(href)
            if self._isHttpOrHttpsProtocol(href) and match_obj is not None:
                topic_list.append(match_obj.group(1))
            
        for topic in topic_list: 
            #print "Add group id:", self.currentGroupID, "with topic link: ", href
            self.topicList.append(topic)
                
        # 如果是首页，则需要添加所有的将来访问的页面
        if start == 0:
            print "Adding future visis for Group: " + self.currentGroupID
            self._addFutureVisit(pageSource)
            
    def _addFutureVisit(self, pageSource):
        """ 访问讨论列表的首页，并添加所有的将来要访问的链接
        """
        #pdb.set_trace()
        if not isinstance(pageSource, unicode):
            # 默认页面采用UTF-8编码
            page = etree.HTML(pageSource.decode('utf-8'))
        else:
            page = etree.HTML(pageSource)
            
        # 目前的做法基于以下观察：在每个列表页面，paginator部分总会显示总的页数
        # 得到总的页数后，便可以知道将来所有需要访问的页面
        paginator = page.xpath(u"//div[@class='paginator']/a")
        last_page = int(paginator[-1].text.strip())
        for i in range(1, last_page):
            # 控制加入topic列表的数量
            if i * 25 >= self.MAX_TOPICS_NUM:
                break
            url = "http://www.douban.com/group/" + self.currentGroupID + "/discussion?start=" + str(i * 25)
            # 向线程池中添加任务：一次性添加
            self.threadPool.putTask(self._taskHandler, url)
            # 添加已经访问过的小组id
            self.visitedHref.add(url)

    def _getAllHrefsFromPage(self, url, pageSource):
        '''解析html源码，获取页面所有链接。返回链接列表'''
        hrefs = []
        soup = BeautifulSoup(pageSource)
        results = soup.find_all('a',href=True)
        for a in results:
            #必须将链接encode为utf8, 因为中文文件链接如 http://aa.com/文件.pdf 
            #在bs4中不会被自动url编码，从而导致encodeException
            href = a.get('href').encode('utf8')
            if not href.startswith('http'):
                href = urljoin(url, href)#处理相对链接的问题
            hrefs.append(href)
        return hrefs

    def _isHttpOrHttpsProtocol(self, href):
        protocal = urlparse(href).scheme
        if protocal == 'http' or protocal == 'https':
            return True
        return False
        
if __name__ == "__main__":
    stacktracer.trace_start("trace.html",interval=5,auto=True) # Set auto flag to always update file!
    congifLogger("topicCrawler.log", 5)
    #tcrawler = TopicCrawler(['FLL', '294806', 'MML'], 5)
    tcrawler = TopicCrawler(['70612'], 5) # 我们都是学术女小组
    tcrawler.start()
    
    stacktracer.trace_stop()


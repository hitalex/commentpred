#coding:utf8

"""
根据已经抓取到的每个小组的topic列表，针对具体的每个topic抓取评论
主题框架于topic_crawler.py相似
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
from models import Topic

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

log = logging.getLogger('Main.CommentCrawler')


class CommentCrawler(object):
    
    def __init__(self, groupID, topicIDList, threadNum):
        
        #线程池,指定线程数
        self.threadPool = ThreadPool(threadNum)  
        
        # 已经访问的页面: Group id ==> True or False
        self.visitedHref = set()
        #待访问的小组讨论页面
        self.unvisitedHref = deque()
        
        self.lock = Lock() #线程锁
        
        # 依次为每个小组抽取topic评论
        self.groupID = groupID
        self.topicIDList = topicIDList # 等待抓取的topic列表
        
        # 存储结果
        # topic ID ==> Topic对象
        self.topicDict = dict()
        # 存放下一个处理的评论页数： topic ID ==> 1,2,3...
        self.nextPage = dict()
        # 已经抓取完毕的topic id集合
        self.finished = set()

        self.isCrawling = False
        
        # 一分钟内允许的最大访问次数
        self.MAX_VISITS_PER_MINUTE = 10
        # 当前周期内已经访问的网页数量
        self.currentPeriodVisits = 0
        # 将一分钟当作一个访问周期，记录当前周期的开始时间
        self.periodStart = time.time() # 使用当前时间初始化
        
        # 每个topic抓取的最多comments个数
        #self.MAX_COMMETS_NUM = 50
        self.MAX_COMMETS_NUM = float('inf')

    def start(self):
        print '\nStart Crawling comment list for group: ' + self.groupID + '...\n'
        self.isCrawling = True
        self.threadPool.startThreads() 
        self.periodStart = time.time() # 当前周期开始
        self.currentPeriodVisits = 0
        
        # 初始化添加任务
        for topic_id in self.topicIDList:
            url = "http://www.douban.com/group/topic/" + topic_id + "/"
            self.threadPool.putTask(self._taskHandler, url)
            self.nextPage[topic_id] = 1
        
        # 完全抛弃之前的抽取深度的概念，改为随时向thread pool推送任务
        while True:
            # 保证任何时候thread pool中的任务数为线程数的2倍
            while self.threadPool.getTaskLeft() < self.threadPool.threadNum * 2:
                # 获取未来需要访问的链接
                url = self._getFutureVisit()
                if url is not None: 
                    self.threadPool.putTask(self._taskHandler, url)
                else: # 已经不存在下一个链接
                    break
            # 每隔一秒检查thread pool的队列
            time.sleep(1)
            # 检查是否处理完毕
            if len(self.finished) == len(self.topicIDList):
                break
            elif len(self.finished) > len(self.topicIDList):
                assert(False)
                
        # 等待线程池中所有的任务都完成
        while self.threadPool.getTaskLeft() > 0:
            #print "Task left: ", self.threadPool.getTaskLeft()
            time.sleep(1)
        self.stop()
        assert(self.threadPool.getTaskLeft() == 0)
        print "Main Crawling procedure finished!"
        
        print "Start to save result..."
        self._saveCommentList()

    def stop(self):
        self.isCrawling = False
        self.threadPool.stopThreads()
        
    def _saveCommentList(self):
        """将抽取的结果存储在文件中，包括存储topic内容和评论内容
        Note: 这次是将存储过程放在主线程，将会阻塞抓取过程
        """
        for topic_id in self.topicDict:
            topic = self.topicDict[topic_id]
            path = "data/" + self.groupID + "/" + topic_id + ".txt"
            f = codecs.open(path, "w", "utf-8", errors='replace')
            f.write(topic.__repr__())
            f.close()
        
    def getAlreadyVisitedNum(self):
        #visitedGroups保存已经分配给taskQueue的链接，有可能链接还在处理中。
        #因此真实的已访问链接数为visitedGroups数减去待访问的链接数
        if len(self.visitedHref) == 0:
            return 0
        else:
            return len(self.visitedHref) - self.threadPool.getTaskLeft()

    def _getFutureVisit(self):
        """根据当前的访问情况，获取下一个要访问的网页
        """
        for topic_id in self.topicDict:
            if topic_id in self.finished:
                continue
            topic = self.topicDict[topic_id]
            if topic.max_comment_page < 0:
                # 还未处理该topic的首页
                continue
            elif topic.max_comment_page == 0:
                # 该topic只有首页有评论
                self.finished.add(topic_id)
            else:
                # 该topic有多页评论
                next_start = self.nextPage[topic_id] * 100
                url = "http://www.douban.com/group/topic/?start=" + str(next_start)
                if next_start >= topic.max_comment_page:
                    self.finished.add(topic_id)
                else:
                    self.nextPage[topic_id] = next_start + 1
                    
                return url
        
        return None
        
    def _taskHandler(self, url):
        """ 根据指定的url，抓取网页，并进行相应的访问控制
        """
        # 判断当前周期内访问的网页数目是否大于最大数目
        if self.currentPeriodVisits >= self.MAX_VISITS_PER_MINUTE - 2:
            timeNow = time.time()
            seconds = timeNow - self.periodStart
            if  seconds < 60: # 如果当前还没有过一分钟,则sleep
                print "Waiting..."
                remain = 60 - seconds
                time.sleep(int(remain + 1))

            self.lock.acquire()
            self.periodStart = time.time() # 重新设置开始时间
            self.currentPeriodVisits = 0
            self.lock.release()
        
        print "Visiting : " + url
        webPage = WebPage(url)
        
        # 抓取页面内容
        flag = webPage.fetch()
        self.lock.acquire() #锁住该变量,保证操作的原子性
        self.currentPeriodVisits += 1
        self.lock.release()
        
        if flag:
            match_obj = RETopic.match(url)
            match_obj2 = REComment.match(url)
            if match_obj is not None:
                topic_id = match_obj.group(1)
                topic = Topic(topic_id, self.groupID)
                topic.parse(webPage, True) # First page parsing
                self.topicDict[topic_id] = topic
            elif match_obj2 is not None:
                topic_id = match_obj2.group(1)
                start = int(match_obj2.group(2))
                # 抽取非第一页的评论数据
                topic = self.topicDict[topic_id]
                topic.parse(webPage, False) # non-firstpage parsing
            else:
                #pdb.set_trace()
                log.info('Topic链接格式错误：%s in Group: %s.' % (url, self.groupID))
            
            return True
        # if page reading fails
        return False
        
    def _saveTaskResults(self, webPage):
        """将topic链接信息写入数据库
        """
        pass
        

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
    LINE_FEED = "\n" # 采用windows的换行格式
    congifLogger("CommentCrawler.log", 5)
    #group_id_list = ['FLL', '294806', 'MML']
    group_id_list = ['FLL']
    for group_id in group_id_list:
        # 读取topic列表
        f = open('data/' + group_id + ".txt")
        topic_list = []
        for line in f:
            line = line.strip()
            if line is not "":
                topic_list.append(line)
                
        ccrawler = CommentCrawler(group_id, topic_list, 5)
        ccrawler.start()
    print "Done"

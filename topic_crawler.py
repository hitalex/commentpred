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
        # 这里的深度指topic列表的页面
        # 例如，http://www.douban.com/group/FLL/discussion?start=0 被认为是深度为0
        self.currentDepth = 0  
        
        #线程池,指定线程数
        self.threadPool = ThreadPool(threadNum)  
        
        # 已经访问的页面: Group id ==> True or False
        self.visitedHref = set()
        #待访问的小组讨论页面
        self.unvisitedHref = deque()
        
        self.lock = Lock() #线程锁
        
        self.groupIDList = groupIDList
        # 标记某个Group是否已经抓取结束
        self.finished = [False] * len(self.groupIDList)
        
        # 抓取结束有两种可能：1）抓取到的topic数目已经最大；2）已经将所有的topic全部抓取
        # 只保存topic id
        self.topicList = list()
        self.stickTopicList = list()
        for i in range(len(self.groupIDList)):
            self.topicList.append(list())
            # 置顶贴的list, 只保存topic id
            self.stickTopicList.append(list())
        #标记爬虫是否开始执行任务
        self.isCrawling = False
        
        # 添加尚未访问的小组首页
        for gid in groupIDList:
            # 小组首页用于抽取置顶贴
            url = "http://www.douban.com/group/" + gid + "/"
            print "Add start url:", url
            self.unvisitedHref.append(url)
            url = "http://www.douban.com/group/" + gid + "/discussion?start=0"
            print "Add start urls:", url
            self.unvisitedHref.append(url)
        
        # 一分钟内允许的最大访问次数
        self.MAX_VISITS_PER_MINUTE = 10
        # 当前周期内已经访问的网页数量
        self.currentPeriodVisits = 0
        # 将一分钟当作一个访问周期，记录当前周期的开始时间
        self.periodStart = time.time() # 使用当前时间初始化
        
        # 每个Group抓取的最大topic个数
        #self.MAX_TOPICS_NUM = 50
        self.MAX_TOPICS_NUM = float('inf')
        # 每一页中显示的最多的topic数量，似乎每页中不一定显示25个topic
        #self.MAX_TOPICS_PER_PAGE = 25

    def start(self):
        print '\nStart Crawling topic list...\n'
        self.isCrawling = True
        self.threadPool.startThreads() 
        self.periodStart = time.time() # 当前周期开始
        self.currentDepth = 0 
        
        while not self.isFinished():
            #分配任务,线程池并发下载当前深度的所有页面（该操作不阻塞）
            self._assignCurrentDepthTasks()
            #等待当前线程池完成所有任务,当池内的所有任务完成时，即代表爬完了一个网页深度
            #self.threadPool.taskJoin()可代替以下操作，可无法Ctrl-C Interupt
            while self.threadPool.getTaskLeft() > 0:
                #print "Task left: ", self.threadPool.getTaskLeft()
                time.sleep(3)
            print 'Depth %d Finish. Totally visited %d links. \n' % (
                self.currentDepth, len(self.visitedHref))
            log.info('Depth %d Finish. Total visited Links: %d\n' % (
                self.currentDepth, len(self.visitedHref)))
            self.currentDepth += 1
        self.stop()
        assert(self.threadPool.getTaskLeft() == 0)
        print "Main Crawling procedure finished!"

    def stop(self):
        self.isCrawling = False
        self.threadPool.stopThreads()

    def isFinished(self):
        """ 判断是否已经结束抓取
        """
        for flag in self.finished:
            if not flag:
                return False
        return True
        
    def getAlreadyVisitedNum(self):
        #visitedGroups保存已经分配给taskQueue的链接，有可能链接还在处理中。
        #因此真实的已访问链接数为visitedGroups数减去待访问的链接数
        if len(self.visitedHref) == 0:
            return 0
        else:
            return len(self.visitedHref) - self.threadPool.getTaskLeft()

    def _assignCurrentDepthTasks(self):
        """取出一个线程，并为这个线程分配任务，即抓取网页，并进行相应的访问控制
        """
        # 判断当前周期内访问的网页数目是否大于最大数目
        if self.currentPeriodVisits > self.MAX_VISITS_PER_MINUTE - 1:
            # 等待所有的网页处理完毕
            while self.threadPool.getTaskLeft() > 0:
                #print "Waiting period ends..."
                time.sleep(1)
            timeNow = time.time()
            seconds = timeNow - self.periodStart
            if  seconds < 60: # 如果当前还没有过一分钟,则sleep
                time.sleep(int(seconds + 3))
            self.periodStart = time.time() # 重新设置开始时间
            self.currentPeriodVisits = 0
        # 从未访问的列表中抽出，并为其分配thread
        while len(self.unvisitedHref) > 0:
            url = self.unvisitedHref.popleft()
            self.threadPool.putTask(self._taskHandler, url)
            # 添加已经访问过的小组id
            self.visitedHref.add(url)
            
    def _taskHandler(self, url):
        """ 根据指定的url，抓取网页
        """
        # 抽取小组主页的置顶贴
        match_obj = REGroup.match(url)
        if match_obj is not None:
            group_id = match_obj.group(1)
            # 添加置顶贴的topic列表
            self._addStickTopic(group_id)
            return True
        
        # 抽取普通讨论贴
        match_obj = REDiscussion.match(url)
        group_id = match_obj.group(1)
        index = self.groupIDList.index(group_id)
        if self.finished[index]:
            return 
        
        print "Visiting : " + url
        webPage = WebPage(url)
        # 抓取页面内容
        flag = webPage.fetch()
        if flag:
            self.lock.acquire() #锁住该变量,保证操作的原子性
            self.currentPeriodVisits += 1
            self.lock.release()
            
            #self._saveTaskResults(webPage)
            self._addTopicLink(webPage, group_id)
            return True
        else:
            index = self.groupIDList.index(group_id)
            self.lock.acquire()
            self.finished[index] = True
            self.lock.release()
            
        # if page reading fails
        return False

    def _addStickTopic(self, group_id):
        """ 访问小组首页，添加置顶贴
        """
        #pdb.set_trace()
        url = "http://www.douban.com/group/"+group_id+"/"
        print "抽取置顶贴 for :", url
        webPage = WebPage(url)
        flag = webPage.fetch()
        if flag:
            self.lock.acquire() #锁住该变量,保证操作的原子性
            self.currentPeriodVisits += 1
            self.lock.release()
            
            index = self.groupIDList.index(group_id)
            url, pageSource = webPage.getDatas()
            if not isinstance(pageSource, unicode):
                # 默认页面采用UTF-8编码
                page = etree.HTML(pageSource.decode('utf-8'))
            else:
                page = etree.HTML(pageSource)
            stickimg = page.xpath(u"//div[@id='wrapper']//div[@class='article']//img[@alt='[置顶]']")
            # 可能一个小组中没有置顶贴，此时stickmig为空
            for imgnode in stickimg:
                titlenode = imgnode.getparent().getparent()
                href = titlenode.xpath("a")[0].attrib['href']
                # 加入到topic列表中
                #print "Add stick post: ", href
                match_obj = RETopic.match(href)
                self.stickTopicList[index].append(match_obj.group(1))
        else:
            print "抽取置顶贴失败 for Group: ", group_id
        
    def _saveTaskResults(self, webPage):
        """将topic链接信息写入数据库
        """
        pass
        
        
    def _addTopicLink(self, webPage, group_id):
        '''将页面中所有的topic链接放入对应的topic列表，并同时加入
        下一步要访问的页面
        '''
        #对链接进行过滤:1.只获取http或https网页;2.保证每个链接只访问一次
        #pdb.set_trace()
        index = self.groupIDList.index(group_id)
        url, pageSource = webPage.getDatas()
        hrefs = self._getAllHrefsFromPage(url, pageSource)
        # 找到有效的链接
        gid_list = []
        for href in hrefs:
            # 只有满足小组topic链接格式的链接才会被处理
            match_obj = RETopic.match(href)
            if self._isHttpOrHttpsProtocol(href) and match_obj is not None:
                gid_list.append(match_obj.group(1))
            
        for gid in gid_list: 
            #print "Add group id:", group_id, "with topic link: ", href
            self.topicList[index].append(gid)
            # 判断加入的topic链接已经大约最大值
            if len(self.topicList[index]) >= self.MAX_TOPICS_NUM:
                self.lock.acquire()
                self.finished[index] = True
                self.lock.release()
                return 
                
        # 加入下一步要访问的页面
        if len(gid_list) == 0:
            # 如果当前页面不包含topic链接都说明已经没有更多的topic
            self.lock.acquire()
            self.finished[index] = True
            self.lock.release()
        else:
            match_obj = REDiscussion.match(url)
            start = int(match_obj.group(2))
            start += 25
            href = "http://www.douban.com/group/" + group_id + "/discussion?start=" + str(start)
            self.unvisitedHref.append(href)

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

    def _isHrefRepeated(self, group_id):
        if (group_id in self.visitedHref) or (group_id in self.unvisitedHref):
            return True
        return False
        
if __name__ == "__main__":
    congifLogger("topicCrawler.log", 4)
    tcrawler = TopicCrawler(['FLL', '294806', 'MML'], 5)
    tcrawler.start()
    
    # write to file
    for i in range(len(tcrawler.groupIDList)):
        group_id = tcrawler.groupIDList[i]
        tlist = (tcrawler.topicList)[i]
        sticklist = (tcrawler.stickTopicList)[i]
        print "Total topics in Group: " + group_id + " is : " + str(len(tlist)+len(sticklist))
        f = open("data/"+group_id+".txt", "w")
        for href in sticklist:
            f.write(href + "\n")
            
        f.write("\n")
        for href in tlist:
            f.write(href + "\n")
            
        f.close()

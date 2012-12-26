#coding:utf8

"""
crawler.py
~~~~~~~~~~~~~

主要模块，爬虫的具体实现。
"""

from urlparse import urljoin,urlparse
from collections import deque
import re
import traceback
from locale import getdefaultlocale
import logging
import time

from bs4 import BeautifulSoup 

from database import Database
from webPage import WebPage
from threadPool import ThreadPool

log = logging.getLogger('Main.crawler')


class Crawler(object):

    def __init__(self, args):
        #指定网页深度
        self.depth = args.depth  
        #标注初始爬虫深度，从1开始
        self.currentDepth = 1  
        #指定关键词,使用console的默认编码来解码
        self.keyword = args.keyword.decode(getdefaultlocale()[1]) 
        #数据库
        self.database =  Database(args.dbFile)
        #线程池,指定线程数
        self.threadPool = ThreadPool(args.threadNum)  
        #已访问的小组id
        self.visitedGroups = set()   
        #待访问的小组id
        self.unvisitedGroups = deque()

        #标记爬虫是否开始执行任务
        self.isCrawling = False
        # 生成RegularExpression对象
        self.pattern = re.compile("^http://www.douban.com/group/([0-9, a-z, A-Z]+)/$")
        # 添加尚未访问的小组首页
        match_obj = self.pattern.match(args.url)
        print args.url
        assert(match_obj != None)
        self.unvisitedGroups.append(match_obj.group(1))

    def start(self):
        print '\nStart Crawling\n'
        if not self._isDatabaseAvaliable():
            print 'Error: Unable to open database file.\n'
        else:
            self.isCrawling = True
            self.threadPool.startThreads() 
            while self.currentDepth < self.depth+1:
                #分配任务,线程池并发下载当前深度的所有页面（该操作不阻塞）
                self._assignCurrentDepthTasks ()
                #等待当前线程池完成所有任务,当池内的所有任务完成时，即代表爬完了一个网页深度
                #self.threadPool.taskJoin()可代替以下操作，可无法Ctrl-C Interupt
                while self.threadPool.getTaskLeft():
                    time.sleep(8)
                print 'Depth %d Finish. Totally visited %d links. \n' % (
                    self.currentDepth, len(self.visitedGroups))
                log.info('Depth %d Finish. Total visited Links: %d\n' % (
                    self.currentDepth, len(self.visitedGroups)))
                self.currentDepth += 1
            self.stop()

    def stop(self):
        self.isCrawling = False
        self.threadPool.stopThreads()
        self.database.close()

    def getAlreadyVisitedNum(self):
        #visitedGroups保存已经分配给taskQueue的链接，有可能链接还在处理中。
        #因此真实的已访问链接数为visitedGroups数减去待访问的链接数
        return len(self.visitedGroups) - self.threadPool.getTaskLeft()

    def _assignCurrentDepthTasks(self):
        """取出一个线程，并为这个线程分配任务，即抓取网页
        """
        # TODO unvisitedGroups may contain no elements
        # TODO Shold control how many pages you cat get in one minute
        while self.unvisitedGroups:
            group_id = self.unvisitedGroups.popleft()
            #向任务队列分配任务
            url = "http://www.douban.com/group/" + group_id + "/"
            self.threadPool.putTask(self._taskHandler, url)
            # 添加已经访问过的小组id
            self.visitedGroups.add(group_id)
            
    def _taskHandler(self, url):
        """ 根据指定的url，抓取网页
        """
        print "Visiting : " + url
        webPage = WebPage(url)
        # 抓取页面内容
        if webPage.fetch():
            #self._saveTaskResults(webPage)
            self._addUnvisitedGroups(webPage)
        """
        match_obj = self.pattern.match(url)
        if match_obj != None:
            # Get the Douban group name
            self.DoubanGroupSet.add(match_ojb.group(1))
        """

    def _saveTaskResults(self, webPage):
        """将小组信息写入数据库
        """
        url, pageSource = webPage.getDatas()
        dbgroup = _getDBGroupDesc(url, pageSource)
        try:
            self.database.saveData(dbgroup)
        except Exception, e:
            log.error(' URL: %s ' % url + traceback.format_exc())

    def _getDBGroupDesc(url, pageSource):
        """从url和网页内容中抓取到小组的信息，包括id，组长，创建时间等等
        返回一个字典介绍
        """
        dbgroup = dict()
        
        return dbgroup
        
    def _addUnvisitedGroups(self, webPage):
        '''添加未访问的链接，并过滤掉非小组主页的链接。将有效的url放进UnvisitedGroups列表'''
        #对链接进行过滤:1.只获取http或https网页;2.保证每个链接只访问一次
        url, pageSource = webPage.getDatas()
        hrefs = self._getAllHrefsFromPage(url, pageSource)
        for href in hrefs:
            print "URLs in page: ", href
            match_obj = self.pattern.match(url)
            # 只有满足小组主页链接格式的链接才会被处理
            if self._isHttpOrHttpsProtocol(href) and (match_obj != None):
                if not self._isHrefRepeated(href):
                    # 将小组id放入待访问的小组列表中去
                    self.unvisitedGroups.append(match_obj.group(1))

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

    def _isHrefRepeated(self, href):
        if (href in self.visitedGroups) or (href in self.unvisitedGroups):
            return True
        return False

    def _isDatabaseAvaliable(self):
        if self.database.isConn():
            return True
        return False

    def selfTesting(self, args):
        url = 'http://www.douban.com/group/insidestory/'
        print '\nVisiting http://www.douban.com/group/insidestory/'
        #测试网络,能否顺利获取百度源码
        pageSource = WebPage(url).fetch()
        if pageSource == None:
            print 'Please check your network and make sure it\'s connected.\n'
        #数据库测试
        elif not self._isDatabaseAvaliable():
            print 'Please make sure you have the permission to save data: %s\n' % args.dbFile
        #保存数据
        else:
            #self._saveTaskResults(url, pageSource)
            print 'Create logfile and database Successfully.'
            print 'Already save Baidu.com, Please check the database record.'
            print 'Seems No Problem!\n'

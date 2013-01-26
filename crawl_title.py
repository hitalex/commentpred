#coding:utf8

"""
此脚本读入所有的topic列表，抓取title值，并重新存入
"""

from urlparse import urljoin,urlparse
import logging
from lxml import etree # use XPath from lxml
import codecs
import pdb
import time

from bs4 import BeautifulSoup 

from threadPool import ThreadPool
from logconfig import congifLogger
from webPage import WebPage

import stacktracer

# config logging
log = logging.getLogger('Main.crawl_title')
congifLogger("crawl_title.log", 5)

failed_set = set()

def task_handler(topic_id, seg_list):
    f = codecs.open('tables/TopicInfo-title.txt', 'a','utf-8')
    url = 'http://www.douban.com/group/topic/' + topic_id + '/'
    print 'Visiting: ', url
    webPage = WebPage(url)
    flag = webPage.fetch()
    
    if flag:
        url, pageSource = webPage.getDatas() # pageSource已经为unicode格式
        page = etree.HTML(pageSource)
        content = page.xpath(u"/html/body/div[@id='wrapper']/div[@id='content']")[0]
        tmp = page.xpath(u"//table[@class='infobox']//td[@class='tablecc']")
        if len(tmp) == 0:
            # 标题没有被截断
            titlenode = content.xpath("h1")[0]
            title = titlenode.text.strip()
        else:
            titlenode = tmp[0]
            title = etree.tostring(titlenode, method='text', encoding='utf-8').strip()
            
        if isinstance(title, unicode):
            pass
        else:
            title = title.decode("utf-8")
        seg_list.insert(4, title)
        f.write('[=]'.join(seg_list) + '\n')
    else:
        failed_set.add(topic_id)
    
    f.close()
    
def main():
    threadPool = ThreadPool(5)
    threadPool.startThreads()
    
    f = codecs.open('tables/TopicInfo-all.txt', 'r', 'utf-8') # 读入unicode字符
    count = 0
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if seg_list[1] == 'ustv':
            threadPool.putTask(task_handler, seg_list[0], seg_list)
            count += 1
        
    f.close()
    while threadPool.getTaskLeft() > 0:
        time.sleep(10)
        print 'Waiting to finish. Task left: %d' % threadPool.getTaskLeft()
        
    log.info('Number of topics in ustv: %d' % count)

if __name__ == '__main__':
    stacktracer.trace_start("trace.html",interval=5,auto=True) # Set auto flag to always update file!
    main()
    stacktracer.trace_stop()
    log.info('抓取失败的topic id：')
    for tid in failed_set:
        log.info(tid)
    log.info('抽取title结束')

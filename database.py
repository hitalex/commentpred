#coding:utf8

"""
database.py
~~~~~~~~~~~~~

该模块提供爬虫所需的sqlite数据库的创建、连接、断开，以及数据的存储功能。
"""

import sqlite3

class Database(object):
    def __init__(self, dbFile):
        try:
            self.conn = sqlite3.connect(dbFile, isolation_level=None, check_same_thread = False) #让它自动commit，效率也有所提升. 多线程共用
            self.conn.execute('''CREATE TABLE IF NOT EXISTS
                            Webpage (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            url TEXT, 
                            pageSource TEXT,
                            keyword TEXT)''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS
                            Group (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            group_id TEXT,
                            user_id TEXT, 
                            pubdate TEXT,
                            description TEXT)''')
        except Exception, e:
            self.conn = None

    def isConn(self):
        if self.conn:
            return True
        else:
            return False

    def saveData(self, url, pageSource, keyword=''):
        if self.conn:
            sql='''INSERT INTO Webpage (url, pageSource, keyword) VALUES (?, ?, ?);'''
            self.conn.execute(sql, (url, pageSource, keyword) )
        else :
            raise sqlite3.OperationalError,'Database is not connected. Can not save Data!'
            
    def saveGrouInfo(self, dbgroup):
        """ 保存小组信息
        """
        if self.conn:
            sql='''INSERT INTO Group (group_id, user_id, pubdate, description) VALUES (?, ?, ?, ?);'''
            self.conn.execute(sql, (dbgroup.group_id, dbgroup.user_id, str(dbgroup.pubdate), dbgroup.desc) )
        else :
            raise sqlite3.OperationalError,'Database is not connected. Can not save Data!'

    def close(self):
        if self.conn:
            self.conn.close()
        else :
            raise sqlite3.OperationalError, 'Database is not connected.'

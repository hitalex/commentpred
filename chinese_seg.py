#encoding=utf8

"""
此脚本浏览数据库中的所有条目，并使用中文分词方法，将它们分隔，逗号隔开, 写入*文件*
"""
import logging
import sqlite3
import codecs

import jieba # 中文分词模块

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

log = logging.getLogger('Main.Chinse-seg')

original_conn = sqlite3.connect("DoubanGroup.db", isolation_level=None, check_same_thread = False) #让它自动commit，效率也有所提升. 多线程共用

fgroup = codecs.open("tables/GroupInfo.txt", "w", "utf-8", errors = "ignore")
ftopic = codecs.open("tables/TopicInfo.txt", "w", "utf-8", errors = "ignore")
fcomment = codecs.open("tables/CommentInfo.txt", "w", "utf-8", errors = "ignore")
                
def seg(chinese_str):
    """中文分词
    Note: 目前采用jieba分词. jieba项目主页：https://github.com/fxsjy/jieba
    """
    seg_list = jieba.cut(chinese_str)
    return " ".join(seg_list)
    
def task_handler(table_name, row):
    """ 处理数据表中的text
    @param table_name 数据表的名称
    @param row 查询结果的一行
    """
    row = list(row)
    del(row[0]) # 删除 id 列
    if table_name == "GroupInfo":
        text = seg(row[3])
        row[3] = text.replace('\n', ' ')
        f = fgroup
    elif table_name == "TopicInfo":
        text = seg(row[4])
        row[4] = text.replace('\n', ' ')
        f = ftopic
    elif table_name == "CommentInfo":
        text = seg(row[6])
        row[6] = text.replace('\n', ' ')
        f = fcomment
    else:
        print "Invalid table name: %s" % table_name
    
    # 写入文件，每行记录用\n隔开, 每列用[=]隔开
    for col in row[0:-1]:
        f.write(col + '[=]')
    f.write(row[-1] + "\n[*ROWEND*]\n")
    
def execute_sql(table_name, sql):
    log.info("Seg chinese for table: %s" % table_name)
    cur = original_conn.cursor()
    result = cur.execute(sql)
    count = 0
    while True:
        row = result.fetchone()
        count += 1
        if row is None:
            break
        task_handler(table_name, row)
        
    log.info("%d rows in talbe: %s" % (count, table_name))
    
def main():
    congifLogger("chinese-seg.log", 5)
    # 转换 GroupInfo
    sql = """SELECT * from GroupInfo;"""
    execute_sql('GroupInfo', sql)
    log.info("GroupInfo写入完成。")

    # 转换 TopicInfo
    sql = """SELECT * from TopicInfo;"""
    execute_sql('TopicInfo', sql)
    log.info("TopicInfo写入完成。")
    
    sql = """SELECT * from CommentInfo;"""
    execute_sql('CommentInfo', sql)
    log.info("CommentInfo写入完成。")
        
    
if __name__ == "__main__":
    main()
    fgroup.close()
    ftopic.close()
    fcomment.close()

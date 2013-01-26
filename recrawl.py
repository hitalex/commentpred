#encoding=utf-8

"""
此脚本用于重新从数据库中抽取出已经存在的topic info，因为原来文本并没有保存未分词的版本
"""

import sqlite3
import codecs

original_conn = sqlite3.connect("DoubanGroup.db", isolation_level=None, check_same_thread = False) #让它自动commit，效率也有所提升. 多线程共用

ftopic = codecs.open("tables/ustv/TopicInfo-db-raw-part.txt", "w", "utf-8", errors = "ignore")
fcomment = codecs.open("tables/ustv/CommentInfo-raw-part.txt", "w", "utf-8", errors = "ignore")

group_id = 'ustv'

topics_all = set()
topics_remain = set()

def get_topic_set(path):
    f = codecs.open(path, 'r', 'utf-8')
    tset = set()
    for tid in f:
        tid = tid.strip()
        if tid != "":
            tset.add(tid)
            
    return tset
    
topics_all = get_topic_set('tables/ustv/TopicList-ustv-all.txt')
topics_remain = get_topic_set('tables/ustv/TopicList-ustv-remain.txt')

topic_list = topics_all - topics_remain
print 'Previous topics: %d' % len(topic_list)

def task_handler(table_name, row):
    """ 处理数据表中的text
    @param table_name 数据表的名称
    @param row 查询结果的一行
    """
    global topic_list
    row = list(row)
    del(row[0]) # 删除 id 列
    if table_name == "GroupInfo":
        f = fgroup
    elif table_name == "TopicInfo":
        if row[1] == group_id and row[0] in topic_list:
            topic_list.remove(row[0])
            pass
        else:
            return
        f = ftopic
    elif table_name == "CommentInfo":
        if row[1] != group_id:
            return
        f = fcomment
    else:
        print "Invalid table name: %s" % table_name
    
    # 写入文件，每行记录用\n隔开, 每列用[=]隔开
    s = '[=]'.join(row) + '\n[*ROWEND*]\n'
    f.write(s)
    
def execute_sql(table_name, sql):
    print "Seg chinese for table: %s" % table_name
    cur = original_conn.cursor()
    result = cur.execute(sql)
    count = 0
    while True:
        row = result.fetchone()
        count += 1
        if row is None:
            break
        task_handler(table_name, row)
        
    print "%d rows in talbe: %s" % (count, table_name)
    
def main():
    sql = """SELECT * from TopicInfo;"""
    execute_sql('TopicInfo', sql)
    print "TopicInfo写入完成。"
    
    #sql = """SELECT * from CommentInfo;"""
    #execute_sql('CommentInfo', sql)
    #print "CommentInfo写入完成。"
    
    ftopic.close()
    fcomment.close()
    
    print 'Unfound topic: %d ' % len(topic_list)
    
if __name__ == '__main__':
    main()

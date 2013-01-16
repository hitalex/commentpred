#coding:utf8

from database import Database

# 这个脚本会从文件中读入topic id列表，写入数据库
#group_ids = ['ustv', '70612', 'insidestory', 'wokaoyan', 'Dear-momo', 'Appearance']

group_ids = ['test']

database = Database("test.db")

for gid in group_ids:
    path = "data/" + gid + ".txt"
    tid_list = u""
    f = open(path)
    for tid in f:
        tid = tid.strip()
        tid_list += (tid + ", ")
        
    #sql = '''UPDATE GroupInfo set topic_list = ? WHERE group_id = ?'''
    sql='''INSERT INTO GroupInfo (group_id, topic_list) VALUES (?,?);'''
    cur = database.conn.cursor()
    #cur.execute(sql, (tid_list, gid))
    cur.execute(sql, (gid, tid_list))

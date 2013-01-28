#encoding=utf8

"""
此脚本用于从数据库中抽取出2012年10月和11月发表的topic或者评论的活跃用户，
并找到他们所有的关注和被关注信息，存放与文件中

"""
from datetime import datetime
import time
import logging
from threading import Lock

from douban_client import DoubanClient
from douban_client.api.error import DoubanError

from logconfig import congifLogger

# config logging
log = logging.getLogger('Main.user')
congifLogger("user.log", 5)

# 训练集的起止时间
START_DATE = datetime(2012, 10, 1)
END_DATE = datetime(2012, 12, 1)

def inTraining(strtime):
    if isinstance(strtime, basestring):
        t = datetime.strptime(strtime, "%Y-%m-%d %H:%M:%S")
    elif isinstance(strtime, datetime):
        t = strtime
    else:
        log.error("inTraning接收到的参数既不是str，也不是datetime.")
        
    if t >= START_DATE and t <= END_DATE:
        return True
    else:
        return False
    
# Douban API
API_KEY = '0c0cb6f7df695ce1242624e79e3c16a3'
API_SECRET = 'b73d7a87176fbd16'
your_redirect_uri = 'http://alexkong.net'
code = 'd47ef98a926249bc'
SCOPE = 'douban_basic_common,shuo_basic_r,shuo_basic_w'

"""
API_KEY = '08bbd6fcb2c4e2ec1a3384f6184ea8c4'
API_SECRET = '6bed2335463af18c'
your_redirect_uri = 'http://alexkong.net'
SCOPE = 'douban_basic_common,shuo_basic_r,shuo_basic_w'

code = '0133410989b9f450'
"""

douban_client = DoubanClient(API_KEY, API_SECRET, your_redirect_uri, SCOPE)
douban_client.auth_with_code(code)

# 指定group
GROUP_ID = 'ustv'

# 查找topic中所有用户
user_info = dict() # 保存所有的uid
failed_set = set() # 抓取失败的uid

max_tasks_per_period = 40
current_period_tasks = 0
period_start_time = 0

def task_control():
    global max_tasks_per_period, current_period_tasks, period_start_time
    if current_period_tasks >= max_tasks_per_period - 1:
        now = time.time()
        seconds = now - period_start_time
        if seconds < 60:
            remain = 60 - seconds
            print "current thread Waiting for %s seconds" % (str(remain))
            time.sleep(int(remain + 1))
        period_start_time = time.time()
        current_period_tasks = 0
    
    current_period_tasks += 1

def find_followers(user_id, start, count):
    """ 找到所有的粉丝
    """
    global user_info, failed_set
    global file_followers, file_following
    
    task_control()
    
    try:
        plist = douban_client.user.followers(user_id, start, count)
    except DoubanError:
        failed_set.add(user_id)
        return
        
    uid_set = set()
    for p in plist:
        uid_set.add(p[u'uid'])
    if not user_id in user_info:
        log.error("User: %s not found" % user_id)
        
    user_info[user_id] = user_info[user_id].union(uid_set)
    
    if len(plist) >= count:
        find_followers(user_id, start+count, count)
    else:
        save_result(file_followers, user_id, user_info[user_id])
        log.info('Number of followers for %s: %d' % (user_id, len(user_info[user_id])))
        #user_info[user_id] = [] # release memory
    
def find_following(user_id, start, count):
    """ 找到所有的关注
    """
    global user_info, failed_set
    global file_followers, file_following
    
    task_control()
    try:
        plist = douban_client.user.following(user_id, start, count)
    except DoubanError:
        failed_set.add(user_id)
        return
        
    uid_set = set()
    for p in plist:
        uid_set.add(p[u'uid'])
    if not user_id in user_info:
        log.error("User: %s not found" % user_id)
        
    user_info[user_id] = user_info[user_id].union(uid_set)
    
    if len(plist) >= count:
        find_following(user_id, start+count, count)
    else:
        save_result(file_following, user_id, user_info[user_id])
        log.info('Number of followings for %s: %d' % (user_id, len(user_info[user_id])))
    
def save_result(f, user_id, uid_set):
    """ 将抓取结果存入文件
    """
    f.write(user_id + ' ')
    num = len(uid_set)
    if num == 0:
        print "No followers or followees: ", user_id
        pass
    else:
        for uid in uid_set:
            f.write(uid + ',')
        f.write('\n')

def extract_user():
    """ 抽取出所有的用户，并写入文件
    """
    GROUP_FILE_PATH = 'tables/GroupInfo.txt'
    TOPIC_FILE_PATH = 'tables/TopicInfo.txt'
    COMMENT_FILE_PATH = 'tables/CommentInfo.txt'
    
    # 先抽取所有的用户
    f = open(TOPIC_FILE_PATH, 'r')
    log.info("抽取Topic表中的用户...")
    row = ''
    count = 0
    valid_topics = set() # 处于合法时间内的topic列表
    for line in f:
        line = line.strip()
        if line != '[*ROWEND*]':
            row += line
            continue
        seg_list = row.split('[=]')
        topic_id = seg_list[0]
        group_id = seg_list[1]
        user_id = seg_list[2]
        strtime = seg_list[3]
        if group_id == GROUP_ID and inTraining(strtime):
            user_info[user_id] = []
            valid_topics.add(topic_id)
            count += 1
            pass
        row = ''
    f.close()
    log.info("Number of valid topics: %s" % count)
    
    f = open(COMMENT_FILE_PATH, 'r')
    log.info("抽取Comment表中的用户...")
    row = ''
    count = 0
    for line in f:
        line = line.strip()
        if line != '[*ROWEND*]':
            row += line
            continue
        seg_list = row.split('[=]')
        group_id = seg_list[1]
        topic_id = seg_list[2]
        user_id = seg_list[3]
        strtime = seg_list[4]
        if group_id == GROUP_ID and (topic_id in valid_topics) and inTraining(strtime):
            user_info[user_id] = []
            count += 1
            pass
        row = ''
    f.close()
    log.info("Number of valid comments: %s" % count)
    
    f = open(USERS_FILE_PATH, 'w')
    for user_id in user_info:
        f.write(user_id + '\n')
    f.close()
    
def load_user(user_list_path):
    """ 从文件内导入用户id
    """
    user_info = dict()
    f = open(user_list_path, 'r')
    for line in f:
        line = line.strip()
        if line != '':
            user_info[line] = set()
    f.close()
    log.info('User id loaded.')
    
    return user_info
    
def main():
    global max_tasks_per_period, current_period_tasks, period_start_time
    global file_followers, file_following
    global user_info, failed_set
    # 依次查找

    #extract_user()
    #log.info("Total users: %d" % len(user_info))
    #return 
    FOLLOWING_FILE_PATH = 'social/ustv/following-remain'
    failed_set = set()
    file_following = open(FOLLOWING_FILE_PATH, 'w')
    user_info = load_user('social/ustv/following-ustv-remain')
    log.info('Number of users in following: %d' % len(user_info))
    period_start_time = time.time()
    current_period_tasks = 0
    count = 0
    log.info('抽取用户的关注列表... ')
    for uid in user_info:
        find_following(uid, 0, 100)
        count += 1
        
    # 记录抽取失败的用户
    log.info('抽取失败的用户id：')
    for uid in failed_set:
        log.info(uid)
    log.info('抽取完成.')
    file_following.close()
    
    #####
    FOLLOWERS_FILE_PATH = 'social/ustv/followers-remain'
    failed_set = set()
    file_followers = open(FOLLOWERS_FILE_PATH, 'w')
    user_info = load_user('social/ustv/followers-ustv-remain')
    log.info('Number of users in followers: %d' % len(user_info))
        
    period_start_time = time.time()
    current_period_tasks = 0
    count = 0
    log.info('抽取用户的粉丝列表... ')
    for uid in user_info:
        find_followers(uid, 0, 100)
        count += 1
        
    # 记录抽取失败的用户
    log.info('抽取失败的用户id：')
    for uid in failed_set:
        log.info(uid)
    log.info('抽取完成.')
    
    file_followers.close()
    
if __name__ == '__main__':
    main()

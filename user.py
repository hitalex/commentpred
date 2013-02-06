#encoding=utf8

"""
此脚本用于从数据库中抽取出2012年10月和11月发表的topic或者评论的活跃用户，
并找到他们所有的关注和被关注信息，存放与文件中

"""
import sys
from datetime import datetime
import time
import logging
from threading import Lock

from douban_client import DoubanClient
from douban_client.api.error import DoubanError

from logconfig import congifLogger
from prepare import load_user_list
import stacktracer

# config logging
log = logging.getLogger('Main.user')
congifLogger("user.log", 5)

""""
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
"""

# Douban API
API_KEY = '0c0cb6f7df695ce1242624e79e3c16a3'
API_SECRET = 'b73d7a87176fbd16'
your_redirect_uri = 'http://alexkong.net'
code = '4c4708d2802303f9'
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

def find_followers(user_id, start, count, followers_path, user_info, failed_set):
    """ 找到所有的粉丝
    """    
    task_control()
    
    try:
        plist = douban_client.user.followers(user_id, start, count)
    except DoubanError:
        failed_set.add(user_id)
        return
        
    uid_set = set()
    for p in plist:
        uid_set.add(p[u'uid'])
        
    user_info[user_id] = user_info[user_id].union(uid_set)
    
    if len(plist) >= count:
        find_followers(user_id, start+count, count, followers_path, user_info, failed_set)
    else:
        save_result(followers_path, user_id, user_info[user_id])
        log.info('Number of followers for %s: %d' % (user_id, len(user_info[user_id])))
        #user_info[user_id] = None # release memory
    
def find_following(user_id, start, count, following_path, user_info, failed_set):
    """ 找到所有的关注
    """
    task_control()
    try:
        plist = douban_client.user.following(user_id, start, count)
    except DoubanError:
        failed_set.add(user_id)
        return
        
    uid_set = set()
    for p in plist:
        uid_set.add(p[u'uid'])
        
    user_info[user_id] = user_info[user_id].union(uid_set)
    
    if len(plist) >= count:
        find_following(user_id, start+count, count, following_path, user_info, failed_set)
    else:
        save_result(following_path, user_id, user_info[user_id])
        log.info('Number of followings for %s: %d' % (user_id, len(user_info[user_id])))
        #user_info[user_id] = None # release memory
    
def save_result(filepath, user_id, uid_set):
    """ 将抓取结果存入文件
    """
    f = open(filepath, 'a')
    f.write(user_id + '[=]' + ','.join(uid_set) + '\n')
    f.close()
        
def load_new_user_set(old_user_path, new_user_path):
    """ 得到新增的用户列表
    """
    old_user_set = set(load_user_list(old_user_path))
    new_user_set = set(load_user_list(new_user_path))
    
    return new_user_set - old_user_set

def main(argv):
    if len(argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = argv[1]
    log.info('Prepare user followings and followers for group: %s' % group_id)
    
    global max_tasks_per_period, current_period_tasks, period_start_time
    
    # 指定group
    print 'Loading users...'
    #old_user_path = 'social/' + group_id + '/all-users-' + group_id + '-new'
    #new_user_path = 'social/' + group_id + '/filtered-user-behavior-' + group_id
    #user_set = load_new_user_set(old_user_path, new_user_path)
    path = 'social/' + group_id + '/filtered-user-behavior-' + group_id
    user_set = set(load_user_list(path))
    # uid ==> following or followers
    user_info = dict() # 保存所有的uid
    failed_set = set() # 抓取失败的uid
    
    for uid in user_set:
        user_info[uid] = set()
    log.info('Number of users in following: %d' % len(user_info))

    following_path = 'social/' + group_id + '/following-remain'
    followers_path = 'social/' + group_id + '/followers-remain'
    
    period_start_time = time.time()
    current_period_tasks = 0
    print '抽取用户的关注列表... '
    for uid in user_info:
        find_following(uid, 0, 100, following_path, user_info, failed_set)
        pass
    # 记录抽取失败的用户
    log.info('抽取关注列表失败的用户id：')
    log.info('\n' + '\n'.join(failed_set))
    
    log.info('抽取完成.')
    
    #####
    user_info = dict()
    for uid in user_set:
        user_info[uid] = set()
    failed_set = set()
    period_start_time = time.time()
    current_period_tasks = 0

    print '抽取用户的粉丝列表... '
    log.info('抽取用户的粉丝列表... ')
    for uid in user_info:
        find_followers(uid, 0, 100, followers_path, user_info, failed_set)
        
    # 记录抽取失败的用户
    log.info('抽取用户粉丝失败的用户id：')
    log.info('\n' + '\n'.join(failed_set))

    log.info('Group %s 抽取完成.' % group_id)
    print 'Done.'
    
if __name__ == '__main__':
    #stacktracer.trace_start("trace.html",interval=5,auto=True) # Set auto flag to always update file!
    main(sys.argv)
    #stacktracer.trace_stop()

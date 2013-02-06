#encoding=utf8

"""
尽最大的可能保留信息，所以并不需要保证all-users和following、followers三者的信息保持一致性
唯一的保证是：它们之中的信息不重复
"""
import sys

def load_user(path, user_set):
    f = open(path)
    for line in f:
        line = line.strip()
        user_set.add(line)
        
    f.close()
    
    return user_set
    
def save_user(path, user_set):
    f = open(path, 'w')
    for uid in user_set:
        f.write(uid + '\n')
        
    f.close()
    
def load_following_followers(path, follow_dict):
    """导入关注或者粉丝列表信息
    """
    f = open(path)
    for line in f:
        line = line.strip()
        seg_list=  line.split('[=]')
        uid = seg_list[0]
        if not uid in follow_dict:
            follow_dict[uid] = seg_list[1] # 直接存储字符串列表
    f.close()
    
def save_following_followers(path, follow_dict):
    f = open(path, 'w')
    for uid in follow_dict:
        f.write(uid + '[=]' + follow_dict[uid] + '\n')
        
    f.close()

if __name__ == '__main__':
    all_user_set = set()
    load_user('all-users-ustv', all_user_set)
    load_user('filtered-user-behavior-ustv', all_user_set)
    load_user('all-users-ustv-old', all_user_set)
    save_user('all-users-ustv-new', all_user_set)
    print 'All users: %d' % len(all_user_set)
    all_user_set = set() # release memorty
    
    following_dict = dict()
    load_following_followers('following-ustv', following_dict)
    load_following_followers('following-remain', following_dict)
    save_following_followers('following-ustv-new', following_dict)
    print 'All following: %d' % len(following_dict)
    following_dict = dict() # release memory
    
    followers_dict = dict()
    load_following_followers('followers-ustv', followers_dict)
    load_following_followers('followers-remain', followers_dict)
    save_following_followers('followers-ustv-new', followers_dict)
    print 'All followers: %d' % len(followers_dict)
    followers_dict = dict() # release memory

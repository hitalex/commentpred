#encoding=utf8

"""
发现当用户总数为5778，但是followers和following信息要比这个数少
"""

def find_remain(path, all_users, remain_path):
    # load following info
    part_all_users = set()
    f = open(path)
    for line in f:
        line = line.strip()
        uid = line.split(' ')[0]
        part_all_users.add(uid)
    f.close()
        
    assert(part_all_users < all_users)
    remain = all_users - part_all_users
    # 将剩余的uid写入另外一个文件
    f = open(remain_path, 'w')
    for uid in remain:
        f.write(uid + '\n')
        
    f.close()
    
    return remain

all_users = set()
f = open('social/ustv/users-ustv')
for uid in f:
    uid = uid.strip()
    all_users.add(uid)
    
print 'Number of all distinct users: %d' % len(all_users)

following_remain = find_remain('social/ustv/following-ustv', all_users, 'social/ustv/following-ustv-remain')
followers_remain = find_remain('social/ustv/followers-ustv', all_users, 'social/ustv/followers-ustv-remain')



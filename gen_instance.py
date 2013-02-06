#coding=utf-8

"""
根据已经得到的内容信息，用户关注信息以及行为信息，生成训练和测试instance
注意：现在抓取的用户是5700多，而平均每个帖子的参与人数要远小于这个数，所以
这也就意味着有非常多的负样本
"""
import logging
import codecs
import re
import sys
import urlparse
from random import random, shuffle

import numpy as np
from scipy.sparse import lil_matrix  # sparse matrix to store 
from gensim import corpora, models

from logconfig import congifLogger
from prepare_corpus import remove_url, seg_chinese
from patterns import REURL,REIMGURL
from prepare import load_user_list

# config logging
log = logging.getLogger('Main.gen_instance')
congifLogger("gen_instance.log", 5)

# 匹配中文的模式
CHAR_PATTERN = re.compile(ur'[\u4e00-\u9fa5]')

def get_topic_users(topic_path):
    """ 从训练集或者测试集的topic集合中获得所有出现的用户
    """
    user_set = set()
    f = codecs.open(topic_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if len(seg_list) != 8:
            log.info('Bad formatted topic: %s' % line)
            continue
        uid = seg_list[2]
        user_set.add(uid)
        comment_user_set = set((seg_list[7]).split(','))
        user_set = user_set | comment_user_set
    f.close()
    
    return user_set

def load_users(file_path, train_topic_path, test_topic_path):
    """ 导入所有的user，并建立从uid到index的映射以及index到uid的映射
    """
    # 导入social/文件夹中所有的用户信息
    f = codecs.open(file_path, 'r', 'utf-8')
    all_users = set()
    for uid in f:
        uid = uid.strip()
        all_users.add(uid)        
    f.close()
    log.info('All users: %d' % len(all_users))
    
    train_user_set = get_topic_users(train_topic_path)
    test_user_set = get_topic_users(test_topic_path)
    train_test_user_set = train_user_set | test_user_set
    log.info('Users in training and testing: %d' % len(train_test_user_set))
    # 只返回那些在两者之间都存在的user id
    # 这样能够保证
    all_users = all_users & train_test_user_set
    log.info('Number of users will be used: %d' % len(all_users))
    
    return all_users

def load_user_interest(file_path, all_user_set):
    """ 导入用户的behavior信息和兴趣分布
    """
    f = codecs.open(file_path, 'r', 'utf-8')
    # user_id ==> [topic_num, comment_num, interest_vec]
    user = dict()
    found_user_set = set() # 那些出现在所有用户集合和interest集合中的用户
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[0]
        if uid in all_user_set:
            found_user_set.add(uid)
            interest = (seg_list[1]).split(',')
            interest = [float(item) for item in interest]
            user[uid] = interest
        
    f.close()
    if len(found_user_set) < len(all_user_set):
        tmp = all_user_set - found_user_set
        ulist = []
        for uid in tmp:
            ulist.append(uid)
        log.error('Users that not found in user interest file: %s' % ','.join(ulist))
    
    return user, found_user_set
    
def load_user_behavior(file_path, all_user_set):
    """
    导入用户的behavior信息
    """
    f = codecs.open(file_path, 'r', 'utf-8')
    # user_id ==> [topic_num, comment_num, interest_vec]
    behavior = dict()
    found_user_set = set()
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[0]
        if uid in all_user_set:
            found_user_set.add(uid)
            num_comments = int(seg_list[1])
            num_topics = int(seg_list[2])
            behavior[uid] = (num_comments, num_topics)
    f.close()
    
    if len(found_user_set) < len(all_user_set):
        tmp = all_user_set - found_user_set
        ulist = []
        for uid in tmp:
            ulist.append(uid)
        log.error('Users that not found in user behavior file: %s' % ','.join(ulist))
    else:
        log.info('All user behavior info is found in file: %s' % file_path)
        
    return behavior, found_user_set
    
def scan_following_followers(path, all_user_set):
    """ 在following或者followers信息中找到所有的用户和all_user_set的交集
    """
    found_user_set = set()
    f = codecs.open(path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[0]
        if uid in all_user_set:
            found_user_set.add(uid)
    f.close()
    
    if len(found_user_set) < len(all_user_set):
        tmp = all_user_set - found_user_set
        ulist = []
        for uid in tmp:
            ulist.append(uid)
        log.error('Users that not found in user following info file %s : %s' % (path, ','.join(ulist)))
    else:
        log.info('All user follow info is found in file: %s' % path)
        
    return found_user_set
    
def get_following_info(uid2index, following_path, followers_path):
    """ 根据用户的关注和被关注信息，获取好友关系矩阵
    如果uid1关注uid2，那么matrix[uid1][uid2] = 1，否则为0。采用稀疏矩阵来存储。
    """
    total_users = len(uid2index) # total users
    following_count = [-1] * total_users # 关注的用户的个数
    followers_count = [-1] * total_users # 粉丝的个数
    friendship = lil_matrix((total_users, total_users), dtype = np.dtype(int))
    # 查找关注
    f = codecs.open(following_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        if line == '':
            continue
        tmp_list = line.split('[=]')
        uid = tmp_list[0]
        if len(tmp_list) > 1:
            following_list = (tmp_list[1]).split(',')
        else:
            following_list = []
        if uid in uid2index:
            from_index = uid2index[uid]
            following_count[from_index] = len(following_list)
            for to_uid in following_list:
                to_uid = to_uid.strip()
                if to_uid in uid2index:
                    to_index = uid2index[to_uid]
                    friendship[from_index, to_index] = 1
        else:
            #log.error('Following uid not found in user set: %s' % uid)
            pass
    f.close()
    # 查找粉丝信息
    f = codecs.open(followers_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        if line == '':
            continue
        tmp_list = line.split('[=]')
        uid = tmp_list[0]
        if len(tmp_list) > 1:
            follower_list = (tmp_list[1]).split(',')
        else:
            follower_list = []
        if uid in uid2index:
            to_index = uid2index[uid]
            followers_count[to_index] = len(follower_list)
            for from_uid in follower_list:
                from_uid = from_uid.strip()
                if from_uid in uid2index:
                    from_index = uid2index[from_uid]
                    friendship[from_index, to_index] = 1
        else:
            #log.error('Follower uid not found in user set: %s' % uid)
            pass
    f.close()
    
    return friendship, following_count, followers_count
    
def save_following_info(following_info_path, friendship, index2uid):
    """ 将用户之间的关注关系写入文件
    """
    f = codecs.open(following_info_path, 'w', 'utf-8')
    from_list, to_list = friendship.nonzero()
    count = len(from_list)
    for i in range(count):
        from_uid = index2uid[from_list[i]]
        to_uid = index2uid[to_list[i]]
        f.write(from_uid + '[=]' + to_uid)
    f.close()
    log.info('Total following links: %d' % count)
    
def get_mutual_following(friendship):
    """ 计算任意两个用户共同follow的人的个数
    注意：在这里mutual_following是个正三角的形状，需要保证：
    mutual_following[from_index][to_index]中, frome_index < to_index
    mutual_following实际上已经不算sparse matrix
    """
    log.info('开始计算两个用户共同follow的人：')
    total_user = (friendship.shape)[0]
    mutual_following = lil_matrix((total_users, total_users), dtype = np.dtype(int))
    for i in range(total_user):
        fi = friendship.getrow(i).todense()
        for j in range(i):
            fj = friendship.getrow(j).todense()
            mutual_following[i, j] = (fi * np.transpose(fj))[0,0]
            if mutual_following[i, j] > 0:
                #log.info('User %d and user %d shared %d followings.' % (i, j, mutual_following[i,j]))
                pass
    
    log.info('计算结束。')
    return mutual_following
    
def save_mutual_following_info(mutual_following_path, mutual_following, index2uid):
    """ 保存mutual friendship信息
    """
    f = open(mutual_following_path, 'w')
    total_user = len(index2uid)
    # 只记录那些共同好友不为0的uid 对
    rows, cols = mutual_following.nonzero()
    for index in range(len(rows)):
        i = rows[index]
        j = cols[index]
        f.write('%s %s %d\n' % (index2uid[i], index2uid[j], mutual_following[i,j]))
    f.close()
    
def load_mutual_following(mutual_following_path, uid2index):
    """ 导入相互关注关系
    """
    total_user = len(uid2index)
    f = open(mutual_following_path, 'r')
    mutual_following = lil_matrix((total_user, total_user), dtype = np.dtype(int))
    for line in f:
        line = line.strip()
        seg_list = line.split(' ')
        from_uid = seg_list[0]
        to_uid = seg_list[1]
        if from_uid in uid2index and to_uid in uid2index:
            from_index = uid2index[from_uid]
            to_index = uid2index[to_uid]
            count = int(seg_list[2])
            mutual_following[from_index, to_index] = count
    f.close()
    
    return mutual_following
    
def count_chinese(text):
    """ 根据unicode字符串，查找中文字符的个数
    注意：需要确保text为unicode
    """
    if not isinstance(text, unicode):
        print '%s is Not unicode.' % text
        return None
        
    char_list = CHAR_PATTERN.findall(text)
    return len(char_list)
    
def gen_content_feature(topic_path, ldamodel, dictionary):
    """ 生成内容特征，包括：标题长度、内容长度、是否包含图片、是否包含外链、topic分布.
    另外，还包括参与topic讨论的用户的id列表
    注意：标题长度和内容长度都只是计算汉字的字数。返回list。
    另外，需要非常注意的是：LDA模型必须和Dictionary匹配
    再另外，这里会将所有的topic信息以及评论者的信息保存，而并不考虑它们是否在all_user_set中。
    这种考虑是基于，希望最大限度的保留原始的训练、测试topic信息。
    """
    content_features = []
    comment_user_list = [] # 在某个topic下留下评论的用户id列表
    f = codecs.open(topic_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        if len(seg_list) != 8:
            log.info('Bad formatted topic: %s' % line)
            continue
        topic_id = seg_list[0]
        creator = seg_list[2]
        title = seg_list[4]
        content = seg_list[5]
        if seg_list[7] == '':
            uid_list = []
        else:
            uid_list = (seg_list[7]).split(',') # 参与评论的用户id
        # 找到在title和content中汉字的数目
        title_count = count_chinese(title)
        content_count = count_chinese(content)
        # 找到是否包含图片
        url_list = REIMGURL.findall(content)
        num_img = len(url_list) # number of images
        # 包含外链的个数
        url_list = REURL.findall(content)
        num_out_link = 0
        for url_group in url_list:
            url = url_group[0] # 包括整个URL
            hostname = urlparse.urlparse(url).hostname
            if hostname != None and hostname != 'www.douban.com':
                num_out_link += 1
                break
        text = seg_chinese(remove_url(title)) + ' ' + seg_chinese(remove_url(content))
        document = text.split(' ')
        doc_bow = dictionary.doc2bow(document)
        doc_lda = ldamodel.__getitem__(doc_bow, eps = 0)
        # 保证doc_lda中是按照topic的顺序排列
        doc_lda = [topicvalue for topicindex, topicvalue in doc_lda]
        content_features.append((topic_id, creator, title_count, content_count, num_img, num_out_link, doc_lda))
        comment_user_list.append((topic_id, uid_list))
        
    return content_features, comment_user_list
    
def get_euclidean_distance(a, b):
    #import pdb
    #pdb.set_trace()
    assert(len(b) == len(b))
    a = np.array(a)
    b = np.array(b)
    return np.linalg.norm(a-b)
    
def get_candidate_comment_user(topic_id, commenting_user_set, K, index2uid, uid2index):
    """ 根据真正的评论用户和比例K，找到评论用户的候选集
    """
    assert(K > 1)
    # 返回找到的user的index
    result = set()
    # 加入所有的真正评论的用户
    for uid in commenting_user_set:
        result.add(uid2index[uid])
    
    total_user = len(index2uid)
    count = int((K - 1) * len(commenting_user_set))
    # 如果所需要的用户数大于或者等于总用户数
    if count + len(commenting_user_set) >= len(index2uid):
        log.info('Maximum user used in topic: %s' % topic_id)
        return range(len(index2uid))
    
    shuffled_list = range(total_user)
    shuffle(shuffled_list)
    for index in shuffled_list:
        if (not index2uid[index] in commenting_user_set) and (not index in result):
            result.add(index)
            count -= 1
        if count <= 0:
            break
    if count > 0:
        log.info('Too many true comment users: %d' % len(commenting_user_set))
        
    log.info('Number of candidate comment users for topic %s is: %d' % (topic_id, len(result)))
    if len(result) == len(index2uid):
        log.info('Topic %s have maximum candidate comment users. Number of true cumment users: %d' % (topic_id, len(commenting_user_set)))
    
    return list(result)

def combine_feature(binary_path, feature_path, topic_index_path, index2uid, uid2index, comment_user_list, \
        content_feature, user_interest, user_behavior, friendship, following_count, followers_count, mutual_following, K):
    """ 生成最终的feature训练文件
    `binary_path` 用来预测某个topic下是否会有评论
    `feature_path` 预测会有哪些用户进行评论。注意：这里会产生两个feature文件，分别用户存放positive和negative的训练样本
    """
    #assert(len(comment_user_list) == len(content_feature))
    bf = codecs.open(binary_path, 'w', 'utf-8')
    fpositive = codecs.open(feature_path + '-positive', 'w', 'utf-8') # 存放正样本
    fnegative = codecs.open(feature_path + '-negative', 'w', 'utf-8') # 存放负样本
    ft = codecs.open(topic_index_path, 'w', 'utf-8')
    topic_count = len(comment_user_list)
    topic_count_used = 0 # 真正使用的topic的个数
    comment_user_count = 0 # 一共参与评论的user
    creator_set = set() # 保存所有的未在总用户中的creator
    num_topic_without_comment = 0 # 没有评论的topic数量
    num_topic_with_comment = 0    # 有评论的topic数量
    for topic_index in range(topic_count):
        topic_id = comment_user_list[topic_index][0]
        print 'Combine topic features for topic: %s' % topic_id
        
        topic_content_feature = content_feature[topic_index]
        #assert(topic_content_feature[0] == topic_id)        # check
        creator_id = topic_content_feature[1]
        # 有可能发帖人已经被过滤掉
        if not creator_id in uid2index:
            creator_set.add(creator_id)
            continue
        # 在topic下评论的用户集合
        commenting_user_set = set(comment_user_list[topic_index][1])
        # 保证评论的用户在总的集合中
        to_be_removed = set()
        for user_id in commenting_user_set:
            if not user_id in uid2index:
                to_be_removed.add(user_id)
        # 在预测时，并不考虑帖子的作者是否会回复
        to_be_removed.add(creator_id)
        commenting_user_set = commenting_user_set - to_be_removed
        # 不考虑没有评论的情况
        if len(commenting_user_set) == 0:
            log.info('Skip topic %s, because it has no comments.' % topic_id)
            continue
        elif len(commenting_user_set) < 5:
            log.info('Skip topic %s, because its number of comments is fewer than 5.' % topic_id)
            continue
            
        creator_index = uid2index[creator_id]
        title_count = topic_content_feature[2]                      # feature 1: title character count
        content_count = topic_content_feature[3]                    # feature 2: content character count
        num_img = topic_content_feature[4]                          # feature 3: number of images
        num_out_link = topic_content_feature[5]                     # feature 4: number of out links
        # topic distribution for each topic
        doc_lda = topic_content_feature[6] 
        creator_num_topics = user_behavior[creator_id][1]           # feature 5: number of topics by the creator
        creator_num_comments = user_behavior[creator_id][0]         # feature 6: number of comments by the creator
        # 帖子发布者的兴趣向量
        creator_interest = user_interest[creator_id]
        creator_num_following = following_count[creator_index]      # feature 7: number of follwwing of the creator
        creator_num_followers = followers_count[creator_index]      # feature 8: number of followers of the creator
        topic_count_used += 1
        comment_user_count += len(commenting_user_set)
        
        # 写入binary classification的feature文件
        if len(commenting_user_set) == 0:
            num_topic_without_comment += 1
            label = -1
        else:
            num_topic_with_comment += 1
            label = +1
        bf.write('%d 1:%d 2:%d 3:%d 4:%d 5:%d 6:%d 7:%d 8:%d\n' % \
            (label, title_count, content_count, num_img, num_out_link, \
            creator_num_topics, creator_num_comments, creator_num_following, creator_num_followers))
        # 如果一个topic有n条评论用户，那么需要找到k*n个（k>1）用户作为候选集，这个候选集中
        # 将包括真正评论的用户，也包括其他没有参与讨论的用户
        candidate_comment_user = get_candidate_comment_user(topic_id, commenting_user_set, K, index2uid, uid2index)
        # 记录topic id以及对应的comment user 列表: topic_id[=]true_comment_user[=]candidate comment user
        tmp = [index2uid[index] for index in candidate_comment_user] # 记录uid
        ft.write(topic_id + '[=]' + ','.join(commenting_user_set) + '[=]' + ','.join(tmp) + '\n')
        # 对于每个用户，产生一个训练或者测试instance
        for user_index in candidate_comment_user:
            uid = index2uid[user_index]
            num_topics = user_behavior[uid][1]                      # feature 9: number of topics the user has posted
            num_comments = user_behavior[uid][0]                    # feature 10: number of comments the user has posted
            interest = user_interest[uid]
            content_sim = get_euclidean_distance(doc_lda, interest)  # feature 11: topic similarity between the target user and the content
            topic_sim = get_euclidean_distance(creator_interest, interest) # feature 12: topic similarity between the target user and the creator
            user_num_following = following_count[user_index]        # feature 13: number of following for the user
            user_num_followers = followers_count[user_index]        # feature 14: number of followers for the user
            is_following = friendship[user_index, creator_index]    # feature 15: whether the user is following the creator
            if user_index < creator_index:                          # feature 16: number of mutual friends
                num_mutual_following = mutual_following[user_index, creator_index]
            else:
                num_mutual_following = mutual_following[creator_index, user_index]
            if uid in commenting_user_set:
                label = +1
                f = fpositive
            else:
                label = -1
                f = fnegative
            # prepare LIBSVM format data, will use liblinear
            f.write('%d 1:%d 2:%d 3:%d 4:%d 5:%d 6:%d 7:%d 8:%d 9:%d 10:%d 11:%f 12:%f 13:%d 14:%d 15:%d 16:%d\n' %\
                    (label, title_count, content_count, num_img, num_out_link, creator_num_topics, creator_num_comments,\
                    creator_num_following, creator_num_followers, num_topics, num_comments, content_sim, topic_sim, \
                    user_num_following, user_num_followers, is_following, num_mutual_following))
                    
    log.info('Total topics: %d' % topic_count)
    log.info('Topics used: %d' % topic_count_used)
    log.info('Total number of comments: %d' % comment_user_count)
    log.info('Number of topics with comment: %d' % num_topic_with_comment)
    log.info('Number of topics without comment: %d' % num_topic_without_comment)
    
    alist = []
    for creator_id in creator_set:
        alist.append(creator_id)
    log.info('Number of creators not in all users set: %d.' % len(creator_set))
    log.info('The creator that not in all_user_set: %s' % ','.join(alist))
    
    bf.close()
    fpositive.close()
    fnegative.close()
    ft.close()
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = sys.argv[1]
    log.info('Generate instance for group: %s' % group_id)
    
    # 在这里只考虑根据训练集和测试集中出现的用户
    # 而在social/文件夹中的用户信息只是作为一个数据库，它们包含了所有的用户social信息
    train_topic_path = 'tables/' + group_id + '/train-topic-' + group_id
    test_topic_path = 'tables/' + group_id + '/test-topic-' + group_id
    log.info('Loading all users...')
    users_path = 'social/' + group_id + '/filtered-user-behavior-' + group_id
    #all_user_set = load_users(users_path, train_topic_path, test_topic_path)
    all_user_set=  set(load_user_list(users_path))
    
    # 用户的兴趣和behavior信息，包括发表topic，回复topic数量，以及自己的兴趣向量
    user_interest_path = 'tables/' + group_id + '/user-interest-' + group_id
    log.info('Loading user interest info...')
    user_interest, all_user_set = load_user_interest(user_interest_path, all_user_set)
    log.info('Done. Number of user interest: %d' % len(user_interest))
    print 'Number of user interest: %d' % len(user_interest)
    
    # 导入用户的behavior信息
    user_behavior_path = 'tables/' + group_id + '/behavior-' + group_id
    log.info('Loading user behavior...')
    user_behavior, all_user_set = load_user_behavior(user_behavior_path, all_user_set)
    log.info('Done. Number of user behaivor: %d' % len(user_behavior))
    print 'Number of user behaivor : %d' % len(user_behavior)
    
    following_path = 'social/' + group_id + '/following-' + group_id
    followers_path = 'social/' + group_id + '/followers-' + group_id
    # 这里并不保证following或者followers中包含了所有的用户信息
    # 浏览following_path，找到与all_user_set的交集
    all_user_set = scan_following_followers(following_path, all_user_set)
    all_user_set = scan_following_followers(followers_path, all_user_set)
    
    # 建立索引
    # 注意：all_user_set 在这里是逐渐减少的，取得是它们的交集
    total_users = len(all_user_set)
    index2uid = []
    uid2index = dict()
    index = 0
    for uid in all_user_set:
        index2uid.append(uid)
        uid2index[uid] = index
        index += 1
    print 'Total users: %d' % total_users
    # 存储user在程序中的index，即顺序
    user_index_path = 'svm/' + group_id + '/users-index'
    f = codecs.open(user_index_path, 'w', 'utf-8')
    for uid in index2uid:
        f.write(uid + '\n')
    f.close()
    
    log.info('Get user friendship...')
    # 用稀疏矩阵存储用户的关注信息
    friendship, following_count, followers_count = get_following_info(uid2index, following_path, followers_path)
    # 保存friendship信息
    following_info_path = 'social/' + group_id + '/following-info-' + group_id
    print 'Saving following info to file: %s' % following_info_path
    save_following_info(following_info_path, friendship, index2uid)
    
    # 关注的统计信息
    nonzero_count = len((friendship.nonzero())[0])
    print 'Nonzero entries count: %d in total %d, percentage: %f' % \
            (nonzero_count, total_users * total_users, nonzero_count * 1.0 / (total_users * total_users))
    print 'Number of non-set following: %d' % following_count.count(-1)
    print 'Number of non-set followers: %d' % followers_count.count(-1)
    print 'Average number of following: %f' % (sum(following_count) * 1.0 / total_users)
    print 'Average number of followers: %f' % (sum(followers_count) * 1.0 / total_users)
    
    # 计算共同关注的人的个数
    log.info('Caculating mutual following...')
    #mutual_following = get_mutual_following(friendship)
    #mutual_following = lil_matrix((total_users, total_users), dtype = np.dtype(int)) # for test
    mutual_following_path = 'social/' + group_id + '/mutual-following-' + group_id
    #print 'Saving mutual following info to file: %s' % mutual_following_path
    #save_mutual_following_info(mutual_following_path, mutual_following, index2uid)
    print 'Loading mutual following info from file: %s' % mutual_following_path
    mutual_following = load_mutual_following(mutual_following_path, uid2index)
        
    # 导入lda模型
    print 'Loading LDA models and dict...'
    log.info('Loading LDA model...')
    model_path = 'ldamodels/' + group_id + '/title-comment-' + group_id + '.ldamodel'
    ldamodel = models.ldamodel.LdaModel.load(model_path)
    log.info('Loading dict...')
    dict_path = 'ldamodels/' + group_id + '/dict-title-comment-' + group_id + '.dict'
    dictionary = corpora.dictionary.Dictionary.load(dict_path)
    
    # 获得每个topic的feature
    print 'Gen content features...'
    log.info('Prepare training content features...')
    train_content_feature, train_comment_user_list = gen_content_feature(train_topic_path, ldamodel, dictionary)
    log.info('Prepare testing content features...')
    test_content_feature, test_comment_user_list = gen_content_feature(test_topic_path, ldamodel, dictionary)
    
    # 根据以上所有的feature，生成feature文件
    # 预测是否会有用户评论的feature训练和测试文件
    binary_train_feature_path = 'features/' + group_id + '/binary-train-feature-' + group_id
    binary_test_feature_path = 'features/' + group_id + '/binary-test-feature-' + group_id
    # 预测会有哪些用户评论的feature训练和测试文件
    train_feature_path = 'features/' + group_id + '/train-feature-' + group_id
    test_feature_path = 'features/' + group_id + '/test-feature-' + group_id
    # 记录在程序中，topic的index以及其对应的comment用户
    train_topic_index_path = 'svm/' + group_id + '/train-topic-index-' + group_id
    test_topic_index_path = 'svm/' + group_id + '/test-topic-index-' + group_id
    
    # candidate set的容量是真正评论用户的K倍
    K = 10
    # prepare training set
    # 需要保证这里的每个user都有所有的信息
    print 'Combine all features...'
    log.info('Combine training features all together...')
    combine_feature(binary_train_feature_path, train_feature_path, train_topic_index_path, index2uid, uid2index, \
        train_comment_user_list, train_content_feature, user_interest, user_behavior, friendship, following_count, \
        followers_count, mutual_following, K)
    
    # prepare test set
    log.info('Combine testing features all together...')
    combine_feature(binary_test_feature_path, test_feature_path, test_topic_index_path, index2uid, uid2index, \
        test_comment_user_list, test_content_feature, user_interest, user_behavior, friendship, following_count, \
        followers_count, mutual_following, K)
    log.info('All done. Good luck!')

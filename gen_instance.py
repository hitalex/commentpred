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

import numpy as np
from scipy.sparse import lil_matrix  # sparse matrix to store 
from gensim import corpora, models
import jieba

from logconfig import congifLogger
from prepare_corpus import remove_url, seg_chinese
from patterns import REURL,REIMGURL

# config logging
log = logging.getLogger('Main.gen_instance')
congifLogger("gen_instance.log", 5)

# 匹配中文的模式
CHAR_PATTERN = re.compile(ur'[\u4e00-\u9fa5]')

def load_users(file_path):
    """ 导入所有的user，并建立从uid到index的映射以及index到uid的映射
    """
    f = codecs.open(file_path, 'r', 'utf-8')
    index2uid = []
    uid2index = dict()
    index = 0
    for uid in f:
        uid = uid.strip()
        index2uid.append(uid)
        uid2index[uid] = index
        index += 1
        
    f.close()
    return index2uid, uid2index

def load_user_interest(file_path, uid2index):
    """ 导入用户的behavior信息和兴趣分布
    """
    f = codecs.open(file_path, 'r', 'utf-8')
    # user_id ==> [topic_num, comment_num, interest_vec]
    user = dict()
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[0]
        if uid in uid2index:
            num_topics = int(seg_list[1])
            num_comments = int(seg_list[2])
            interest = (seg_list[3]).split(',')
            interest = [float(item) for item in interest]
            user[uid] = (num_topics, num_comments, interest)
        
    f.close()
    return user
    
def get_following_info(index2uid, uid2index, following_path, followers_path):
    """ 根据用户的关注和被关注信息，获取好友关系矩阵
    如果uid1关注uid2，那么matrix[uid1][uid2] = True，否则为False。采用稀疏矩阵来存储。
    """
    total_users = len(index2uid) # total users
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
            log.error('Following uid not found in user set: %s' % uid)
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
            log.error('Follower uid not found in user set: %s' % uid)
    f.close()
    
    return friendship, following_count, followers_count
    
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
            uid_list = (seg_list[7]).split(',')
        # 找到在title和content中汉字的数目
        title_count = count_chinese(title)
        content_count = count_chinese(content)
        # 找到是否包含图片
        obj = REIMGURL.search(content)
        if obj is None:
            contain_img = False
        else:
            contain_img = True
        # 是否包含外链
        url_list = REURL.findall(content)
        contain_out_link = False
        for url_group in url_list:
            url = url_group[0] # 包括整个URL
            hostname = urlparse.urlparse(url).hostname
            if hostname != None and hostname != 'www.douban.com':
                contain_out_link = True
                break
        text = seg_chinese(remove_url(title)) + ' ' + seg_chinese(remove_url(content))
        document = text.split(' ')
        doc_bow = dictionary.doc2bow(document)
        doc_lda = ldamodel.__getitem__(doc_bow, eps = 0)
        # 保证doc_lda中是按照topic的顺序排列
        doc_lda = [topicvalue for topicindex, topicvalue in doc_lda]
        content_features.append((topic_id, creator, title_count, content_count, contain_img, contain_out_link, doc_lda))
        comment_user_list.append((topic_id, uid_list))
        
    return content_features, comment_user_list
    
def get_euclidean_distance(a, b):
    #import pdb
    #pdb.set_trace()
    assert(len(b) == len(b))
    a = np.array(a)
    b = np.array(b)
    return np.linalg.norm(a-b)

def combine_feature(feature_path, index2uid, uid2index, comment_user_list, content_feature, user_interest, friendship, following_count, followers_count):
    """ 生成最终的feature训练文件
    Note: Almost done here, finally!
    """
    assert(len(comment_user_list) == len(content_feature))
    f = codecs.open(feature_path, 'w', 'utf-8')
    topic_count = len(comment_user_list)
    topics_count_used = 0
    comment_user_count = 0 # 一共参与的user
    creator_set = set() # 保存所有的未在总用户中的creator
    for topic_index in range(topic_count):
        topic_id = comment_user_list[topic_index][0]
        # 在topic下评论的用户集合
        commenting_user_set = set(comment_user_list[topic_index][1])
        # 保证评论的用户在总的集合中
        to_be_removed = set()
        for user_id in commenting_user_set:
            if not user_id in uid2index:
                to_be_removed.add(user_id)
        commenting_user_set = commenting_user_set - to_be_removed
        
        topic_content_feature = content_feature[topic_index]
        assert(topic_content_feature[0] == topic_id)        # check
        creator_id = topic_content_feature[1]
        # 有可能发帖人已经被过滤掉
        if not creator_id in uid2index:
            creator_set.add(creator_id)
            continue
        creator_index = uid2index[creator_id]
        title_count = topic_content_feature[2]                      # feature 1: title character count
        content_count = topic_content_feature[3]                    # feature 2: content character count
        contain_img = topic_content_feature[4]                      # feature 3: whether it contains images
        contain_out_link = topic_content_feature[5]                 # feature 4: whether it contains out link
        # topic distribution for each topic
        doc_lda = topic_content_feature[6] 
        creator_num_topics = user_interest[creator_id][0]           # feature 5: number of topics for the creator
        creator_num_comments = user_interest[creator_id][1]         # feature 6: number of comments by the creator
        creator_num_following = following_count[creator_index]      # feature 7: number of follwwing for the creator
        creator_num_followers = followers_count[creator_index]      # feature 8: number of followers for the creator
        topics_count_used += 1
        commenting_user_count += len(commenting_user_set)
        # 对于每个用户，产生一个训练或者测试instance
        for user_index in range(len(index2uid)):
            uid = index2uid[user_index]
            num_topics = user_interest[uid][0]                      # feature 9: number of topics the user has posted
            num_comments = user_interest[uid][1]                     # feature 10: number of comments the user has posted
            interest = user_interest[uid][2]
            similarity = get_euclidean_distance(doc_lda, interest)  # feature 11: topic similarity
            user_num_following = following_count[user_index]        # feature 12: number of following for the user
            user_num_followers = followers_count[user_index]        # feature 13: number of followers for the user
            is_following = friendship[user_index, creator_index]    # feature 14: whether the user is following the creator
            if uid in commenting_user_set:
                label = +1
            else:
                label = -1
            if contain_img:
                img_feature = 1
            else:
                img_feature = 0
            if contain_out_link:
                out_link_feature = 1
            else:
                out_link_feature = 0
            # prepare LIBSVM format data, will use liblinear
            f.write('%d 1:%d 2:%d 3:%d 4:%d 5:%d 6:%d 7:%d 8:%d 9:%d 10:%d 11:%f 12:%d 13:%d 14:%d\n' %\
                    (label, title_count, content_count, img_feature, out_link_feature, creator_num_topics, creator_num_comments,\
                    creator_num_following, creator_num_followers, num_topics, num_comments, similarity, user_num_following,\
                    user_num_followers, is_following))
                    
    log.info('Total topics: %d' % topic_count)
    log.info('Topics used: %d' % count)
    log.info('Total number of comments: %d' % len(commenting_user_count))
    log.info('Number of creators not in all users set: %d. And here they are:' % len(creator_set))
    for creator_id in creator_set:
        log.info(creator_id)
    f.close()
    
if __name__ == '__main__':
    group_id = 'ustv'
    
    log.info('Loading all users...')
    users_path = 'social/' + group_id + '/users-' + group_id
    index2uid, uid2index = load_users(users_path)
    total_users = len(index2uid)
    log.info('Done. Number of users: %d' % total_users)
    print 'Total users: %d' % total_users
    
    # 用户的兴趣和behavior信息，包括发表topic，回复topic数量，以及自己的兴趣向量
    user_interest_path = 'tables/' + group_id + '/user-interest'
    log.info('Loading user behavior and interest info...')
    user_interest = load_user_interest(user_interest_path, uid2index)
    log.info('Done. Number of user interest: %d' % len(user_interest))
    print 'Number of user interest: %d' % len(user_interest)
    
    # 用稀疏矩阵存储用户的关注信息
    log.info('Loading friendship info...')
    following_path = 'social/' + group_id + '/following-' + group_id
    followers_path = 'social/' + group_id + '/followers-' + group_id
    friendship, following_count, followers_count = get_following_info(index2uid, uid2index, following_path, followers_path)
    # 关注的统计信息
    nonzero_count = len((friendship.nonzero())[0])
    print 'Nonzero entries count: %d in total %d, percentage: %f' % \
            (nonzero_count, total_users * total_users, nonzero_count * 1.0 / (total_users * total_users))
    print 'Number of non-set following: %d' % following_count.count(-1)
    print 'Number of non-set followers: %d' % followers_count.count(-1)
    print 'Average number of following: %f' % (sum(following_count) * 1.0 / total_users)
    print 'Average number of followers: %f' % (sum(followers_count) * 1.0 / total_users)
    
    # 导入lad模型
    log.info('Loading LDA model...')
    model_path = 'ldamodels/' + group_id + '/title-comment-' + group_id + '.ldamodel'
    ldamodel = models.ldamodel.LdaModel.load(model_path)
    log.info('Loading dict...')
    dict_path = 'ldamodels/' + group_id + '/dict-title-comment-' + group_id + '.dict'
    dictionary = corpora.dictionary.Dictionary.load(dict_path)
    
    # 获得每个topic的feature
    train_topic_path = 'tables/' + group_id + '/train-topic-' + group_id
    test_topic_path = 'tables/' + group_id + '/test-topic-' + group_id
    
    log.info('Prepare training content features...')
    train_content_feature, train_comment_user_list = gen_content_feature(train_topic_path, ldamodel, dictionary)
    log.info('Prepare testing content features...')
    test_content_feature, test_comment_user_list = gen_content_feature(test_topic_path, ldamodel, dictionary)
    
    # 根据以上所有的feature，生成feature文件
    train_feature_path = 'features/' + group_id + '/train-feature-' + group_id
    test_feature_path = 'features/' + group_id + '/test-feature-' + group_id
    
    log.info('Combine training features all together...')
    combine_feature(train_feature_path, index2uid, uid2index, \
        train_comment_user_list, train_content_feature, user_interest, friendship, following_count, followers_count)
    log.info('Combine testing features all together...')
    combine_feature(test_feature_path, index2uid, uid2index, \
        test_comment_user_list, test_content_feature, user_interest, friendship, following_count, followers_count)
    log.info('All done. Good luck!')

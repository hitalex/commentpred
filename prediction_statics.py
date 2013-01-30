# coding=utf-8

"""
该脚本检查采用Logistic Regression by LIBLINEAR的概率输出，得到precision@K
"""
import logging

from operator import itemgetter
from logconfig import congifLogger

# config logging
log = logging.getLogger('Main.statics')
congifLogger("prediction_statics.log", 5)

def load_user(filepath):
    """ 按照文件中user id的顺序读入，返回list
    """
    uid_list = []
    f = open(filepath)
    for line in f:
        line = line.strip()
        uid_list.append(line)
        
    return uid_list
    
def load_test_topic(filepath):
    """ 导入测试topic的index以及对应的真正的参与人数
    """
    topic_list = []
    f = open(filepath)
    for line in f:
        line = line.strip()
        seg_list = line.split('[=]')
        topic_id = seg_list[0]
        if seg_list[1] == '':
            topic_list.append((topic_id, set()))
        else:
            comment_user_set = set((seg_list[1]).split(','))
            topic_list.append((topic_id, comment_user_set))
                
    return topic_list
    
def get_precision_at_K(predict_result_path, user_list, topic_list, K):
    """
    计算每个topic在K位置的precison
    """
    precision = [-1] * len(topic_list)
    total_user = len(user_list)
    if K > total_user:
        print 'K should be larger than the total number of users.'
        return
        
    f = open(predict_result_path)
    f.readline() # omit the header: labels -1 1
    count = 0
    prob_list = [] # 记录对应每个用户的概率
    for line in f:
        if count >0 and (count % total_user == 0):
            # 得到当前的topic index
            topic_index = count / total_user - 1
            topic_id = topic_list[topic_index][0]
            true_comment_users = topic_list[topic_index][1]
            # 从大到小排列
            prob_list = sorted(prob_list, key=itemgetter(1), reverse=True)
            predict_users = set() # 预测得到的用户集合
            for i in range(K):
                user_index = prob_list[i][0]
                predict_users.add(user_list[user_index])
            if len(true_comment_users) == 0:
                log.info('Topic %s has no comments.' % topic_id)
            else:
                p = len(predict_users & true_comment_users) * 1.0 / len(true_comment_users)
                log.info('Precision@%d for topic: %s is %f (%d out of %d)' % (K, topic_id, p, \
                    len(predict_users & true_comment_users), len(true_comment_users)))
                precision[topic_index] = p
            
            prob_list = []
        line = line.strip() # it looks like this: -1 0.99952 0.000480238
        seg_list = line.split(' ')
        label = int(seg_list[0])
        negative_prob = float(seg_list[1])
        positive_prob = float(seg_list[2])
        user_index = count % total_user
        prob_list.append((user_index, positive_prob))
        count += 1
        
    return precision
    
def get_precision_one_class(predict_result_one_class_path, user_list, topic_list):
    """ 统计One-class SVM所得到的预测结果
    """
    total_user = len(user_list)
    f = open(predict_result_one_class_path)
    count = 0
    label_list = [0] * total_user
    statics = [None] * len(topic_list)
    for line in f:
        if count >0 and count % total_user == 0:
            # 得到当前的topic index
            topic_index = count / total_user - 1
            topic_id = topic_list[topic_index][0]            
            true_comment_users = topic_list[topic_index][1]
            predicted_comment_users = set()
            for index in range(total_user):
                if label_list[index] == 1:
                    predicted_comment_users.add(user_list[index])
            log.info('Topic id: %s; Number of true comment users: %d, number of predicted comment users: %d' % \
                    (topic_id, len(true_comment_users), len(predicted_comment_users)))
            
            if len(true_comment_users) == 0:
                log.info('Topic %s has no comments.' % topic_id)
            else:
                # view it as classification task
                tp = 0 # true positive
                tn = 0 # true negative
                fp = 0 # false positive
                fn = 0 # false negative
                for i in range(total_user):
                    uid = user_list[i]
                    label = label_list[i]
                    if label == 1 and uid in true_comment_users:
                        tp += 1
                    elif label == -1 and uid in true_comment_users:
                        fn += 1
                    elif label == 1 and not uid in true_comment_users:
                        fp += 1
                    elif label == -1 and not uid in true_comment_users:
                        tn += 1
                    else:
                        log.error('Label error for user index: %d' % i)
                if tp + fp == 0:
                    log.info('Topic %s: tp + fp = 0, which means: Predict no comments.' % topic_id)
                elif tp + fn == 0:
                    log.info('Topic %s: tp + fn = 0, which means: All predicted are wrong.' % topic_id)
                else:
                    precision = tp * 1.0 / (tp + fp)
                    recall = tp * 1.0 / (tp + fn)
                    statics[topic_index] = (topic_id, precision, recall)
                    log.info('Topic %s: Precision: %f, Recall: %f' % (topic_id, precision, recall))
                
            label_list = [0] * total_user
            
        line = line.strip()
        user_index = count % total_user
        label_list[user_index] = int(line)
        count += 1
    
    return statics

if __name__ == '__main__':
    group_id = 'ustv'
    # index files
    user_index_path = 'svm/' + group_id + '/users-index'
    user_list = load_user(user_index_path)
    
    test_topic_index_path = 'svm/' + group_id + '/test-topic-index-' + group_id
    topic_list = load_test_topic(test_topic_index_path)
    
    print 'Statics of LR...'
    predict_result_path = 'svm/' + group_id + '/predict-result'
    K = 50
    precison = get_precision_at_K(predict_result_path, user_list, topic_list, K)
    
    print 'Statics of one class SVM...'
    predict_result_one_class_path = 'svm/' + group_id + '/predict-result-one-class'
    statics_one_class = get_precision_one_class(predict_result_one_class_path, user_list, topic_list)

# coding=utf-8

"""
该脚本检查采用Logistic Regression by LIBLINEAR的概率输出，得到precision@K
"""
import logging
import sys
import random

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
            candidate_user_list = seg_list[2].split(',')
            topic_list.append((topic_id, comment_user_set, candidate_user_list))
                
    return topic_list
    
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
    
def get_precision_at_K(predict_result_path, topic_list, K):
    """
    计算每个topic在K位置的precison
    """
    assert(K > 0)
    precision = dict()
        
    f = open(predict_result_path)
    header = f.readline()
    label, pos, neg = header.split()
    if pos == '1':
        flag = True
    else:
        flag = False
    count = 0
    
    for topic_id, true_comment_user_set, candidate_user_list in topic_list:
        prob_list = [] # 记录对应每个用户的概率
        n = len(candidate_user_list)
        # 读入所有的测试用户的评论概率
        for i in range(n):
            line = f.readline()
            line = line.strip()
            seg_list = line.split(' ')
            label = int(seg_list[0])
            if flag:
                negative_prob = float(seg_list[2])
                positive_prob = float(seg_list[1])
            else:
                negative_prob = float(seg_list[1])
                positive_prob = float(seg_list[2])
            uid = candidate_user_list[i]
            prob_list.append((uid, positive_prob))
        # 按照概率排序
        prob_list = sorted(prob_list, key=itemgetter(1), reverse=True)
        predict_users = set() # 预测得到的用户集合
        
        if K >= len(prob_list):
            K = len(prob_list)
            
        for i in range(K):
            uid = prob_list[i][0]
            predict_users.add(uid)
            
        if len(true_comment_user_set) == 0:
            log.info('Topic %s has no comments.' % topic_id)
            p = 0
        else:
            p = len(predict_users & true_comment_user_set) * 1.0 / K
            log.info('Precision@%d for topic: %s is %f (%d out of %d)' % (K, topic_id, p, \
                len(predict_users & true_comment_user_set), len(true_comment_user_set)))
        
        # 同时记录 topic_id和precision
        precision[topic_id] = p
        
    return precision
    
def evaluation(group_id):
    """ 被调用的主评价函数
    """    
    test_topic_index_path = 'svm/' + group_id + '/test-topic-index-' + group_id
    topic_list = load_test_topic(test_topic_index_path)

    topic_id_list = [] # 按照顺序记录所有的topic id
    for topic_id, true_comment_user_set, candidate_user_list in topic_list:
        topic_id_list.append(topic_id)
        
    print 'Statics of LR...'
    predict_result_path = 'svm/' + group_id + '/predict-result'
    #predict_result_path = 'features/ustv/output'
    prediction_result = []
    for K in range(5, 50, 5):
        print 'Caculating precision@%d' % K
        precision = get_precision_at_K(predict_result_path, topic_list, K)
        prediction_result.append((K, precision))
    
    return prediction_result
    
def save_prediction_result(group_id, prediction_result, R, index):
    """ 保存最终的预测结果
    """
    for K, precision in prediction_result:
        result_path = 'result/%s/prediction-result-%d-%d-%d' % (group_id, R, index, K)
        f = open(result_path, 'w')
        for topic_id in precision:
            f.write('%s %f\n' % (topic_id, precision[topic_id]))
        
        f.close()
    
if __name__ == '__main__':
    if len(sys.argv) < 4:
        print 'python prediction_statics.py group_id R index'
        sys.exit(0)
    
    group_id = sys.argv[1]
    R = int(sys.argv[2])
    index = int(sys.argv[3])
    log.info('Predictiong statics for group: %s, with R = %d, index = %d' % (group_id, R, index))
    # index files
    #user_index_path = 'svm/' + group_id + '/users-index'
    #user_list = load_user(user_index_path)
    
    print 'Predictiong statics for group: %s, with R = %d, index = %d' % (group_id, R, index)
    prediction_result = evaluation(group_id)
    
    save_prediction_result(group_id, prediction_result, R, index)
    
    #print 'Statics of one class SVM...'
    #predict_result_one_class_path = 'svm/' + group_id + '/predict-result-one-class'
    #statics_one_class = get_precision_one_class(predict_result_one_class_path, user_list, topic_list)

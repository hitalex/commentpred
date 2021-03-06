# coding=utf8

"""
SVM训练和预测
"""

import os
import sys
from random import random

def svm_training(group_id):
    """ R表示target user set的大小比例
    index表示，对于一定的R，是第几次实验。
    注意：R和index的取值不同，主要决定了prediction-result的命名的不同
    """
    train_positive_path = 'features/' + group_id + '/train-feature-' + group_id + '-positive'
    train_negative_path = 'features/' + group_id + '/train-feature-' + group_id + '-negative'

    test_positive_path = 'features/' + group_id + '/test-feature-' + group_id + '-positive'
    test_negative_path = 'features/' + group_id + '/test-feature-' + group_id + '-negative'
    test_path = 'features/' + group_id + '/test-feature-' + group_id
    train_path = 'features/' + group_id + '/train-feature-' + group_id

    # 将test的negative和positve合在一起
    os.system('cd ~/github/crawler/')
    print 'Combine positive and negative instances of test set...'
    os.system('cat ' + test_positive_path + ' ' + test_negative_path + ' > ' + test_path)
    print 'Combine positive and negative instances of training set...'
    os.system('cat ' + train_positive_path + ' ' + train_negative_path + ' > ' + train_path)

    print 'Scaling the test and train files...'
    print 'Scaling %s' % test_path
    os.system('~/libsvm-3.16/svm-scale -l 0 -u 1 ' + test_path + ' > ' + test_path + '-scaled')
    print 'Scaling %s' % train_path
    os.system('~/libsvm-3.16/svm-scale -l 0 -u 1 ' + train_path + ' > ' + train_path + '-scaled')

    test_path += '-scaled'
    train_path += '-scaled'

    svm_base_path = 'svm/' + group_id + '/'
    print 'Prepare training set is done. Then train a models and predict...'
    model_file = svm_base_path + 'model'
    os.system('~/liblinear-1.93/train -s 0 %s %s' % (train_path, model_file))
    
    print 'Predicting result...'
    output_file = svm_base_path + 'predict-result'
    print 'Test file: %s, model file: %s, predict result: %s' % (test_path, model_file, output_file)
    os.system('~/liblinear-1.93/predict -b 1 %s %s %s' % (test_path, model_file, output_file))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = sys.argv[1]
    R = 10
    index = 0
    print 'SVM training and predicting for group: %s with R = %d, index = %d' % (group_id, R, index)
    
    svm_training(group_id)

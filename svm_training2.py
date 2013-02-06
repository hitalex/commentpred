# coding=utf8

"""
为SVM训练准备训练数据。
这里采用的方法是：根据negative instance和positive instance的比例，例如为n:1，
则将negative instance划分为n份，分别将划分的每一份都和positive instance作为训练集，
这样则可以训练出n个model。然后，分别用这n个模型进行测试，得到n个概率值并计算它们的平均值，
这样最终得到每一个test instance的概率值
"""

import os
from random import random

group_id = 'ustv'

train_positive_path = 'features/' + group_id + '/train-feature-' + group_id + '-positive'
train_negative_path = 'features/' + group_id + '/train-feature-' + group_id + '-negative'

test_positive_path = 'features/' + group_id + '/test-feature-' + group_id + '-positive'
test_negative_path = 'features/' + group_id + '/test-feature-' + group_id + '-negative'
test_path = 'features/' + group_id + '/test-feature-' + group_id

# 将test的negative和positve合在一起
print 'Combine positive and negative instances of test set...'
os.system('cd ~/github/crawler/')
os.system('cat ' + test_positive_path + ' ' + test_negative_path + ' > ' + test_path)

print 'Counting line of potive and negative instances...'
tmp = os.popen('wc -l features/%s/train-feature-%s-positive' % (group_id, group_id)).readlines()[0]
pline_count = int(tmp.split(' ')[0])
tmp = os.popen('wc -l features/%s/train-feature-%s-negative' % (group_id, group_id)).readlines()[0]
nline_count = int(tmp.split(' ')[0])
print 'Positive instances: %d, negative instances: %d' % (pline_count, nline_count)
n = nline_count * 1.0 / pline_count
print 'Ratio: %f' % n
n = int(n)
print 'So, there will be %d SVM training and SVM models.' % n

print 'Scaling the test and train files...'
print 'Scaling %s' % test_path
os.system('~/libsvm-3.16/svm-scale -l 0 -u 1 ' + test_path + ' > ' + test_path + '-scaled')
print 'Scaling %s' % train_positive_path
os.system('~/libsvm-3.16/svm-scale -l 0 -u 1 ' + train_positive_path + ' > ' + train_positive_path + '-scaled')
print 'Scaling %s' % train_negative_path
os.system('~/libsvm-3.16/svm-scale -l 0 -u 1 ' + train_negative_path + ' > ' + train_negative_path + '-scaled')

print 'Prepare training files...'
base_path = 'features/' + group_id + '/train-sets/'
train_positive_path += '-scaled'
train_negative_path += '-scaled'

# create n feature files
fpositive = open(train_positive_path, 'r')
file_list = []
for i in range(n):
    f = open(base_path + 'train-feature-' + str(i), 'a')
    file_list.append(f)
    fpositive.seek(os.SEEK_SET)
    for line in fpositive:
        f.write(line)

fpositive.close()

fnegative = open(train_negative_path, 'r')
for line in fnegative:
    r = random()
    index = int(r * n)
    f = file_list[index]
    f.write(line)
    
# close files
fnegative.close()
for i in range(n):
    file_list[i].close()

svm_base_path = 'svm/' + group_id + '/models/'
print 'Prepare training set is done. Then train some models and predict...'
for i in range(n):
    print 'Train model #%d...' % i
    train_file = base_path + 'train-feature-' + str(i)
    model_file = svm_base_path + 'model-' + str(i)
    os.system('~/liblinear-1.93/train -s 0 %s %s' % (train_file, model_file))
    print 'Predicting result...'
    output_file = svm_base_path + 'predict-result-' + str(i)
    os.system('~/liblinear-1.93/predict -b 1 %s %s %s' % (test_path, model_file, output_file))
    

print 'Combine the predict result...'
# get the number of test instances
tmp = os.popen('wc -l features/%s/test-feature-%s' % (group_id, group_id)).readlines()[0]
test_num_instances = int(tmp.split(' ')[0])
prob = [0] * test_num_instances
print '%d test instances...' % test_num_instances

for i in range(n):
    path = svm_base_path + 'predict-result-' + str(i)
    print 'Combining %s' % path
    f = open(path, 'r')
    index = 0
    header = f.readline()
    label, pos, neg = header.split()
    if pos == '1':
        flag = True
    else:
        flag = False
        
    for line in f:
        line = line.strip()
        seg_list = line.split(' ')
        if flag:
            negative_prob = float(seg_list[2])
            positive_prob = float(seg_list[1])
        else:
            negative_prob = float(seg_list[1])
            positive_prob = float(seg_list[2])
        prob[index] += positive_prob
        index += 1
    f.close()

print 'Writing resut to file...'
prob = [p*1.0/n for p in prob]
result = open(svm_base_path + 'predict-result', 'w')
result.write('label 1 -1\n') # header
for p in prob:
    if p >= 0.5:
        label = 1
    else:
        label = -1
    result.write('%d %f %f\n' % (label, p, 1-p))
result.close()

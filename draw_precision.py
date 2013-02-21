# coding=utf-8

"""
该脚本读取所有的precision，并对相同的R求平均，并做图
"""
import sys

import matplotlib.pyplot as plt
import pylab
import random


def draw_precision(topic_id_list, R, group_id, prediction_result):
    """ 根据id列表，画出对应与不同的K的precision
    注意：这里得到的precision应该是：对应与相同的R，做几次实验得到的平均值
    """
    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
    marker_list = ['.', ',', 'o', '*', '+', '*', 'd', 's', 'p', 'v'] # 一共9中marker style
    
    index = 0
    assert(len(prediction_result) <= len(marker_list)) # 确保linestyle够用

    fig = plt.figure()
    ax = fig.add_subplot(111)
    for K, precision in prediction_result[0:3]:
        p = []
        for topic_id in topic_id_list:
            p.append(precision[topic_id])
        p = sorted(p, reverse=True)
        sp = [str(item) for item in p]
        #log.info(' '.join(sp) + '\n\n')
        
        ax.hold(True)
        print 'Drawing Precision@%d for group: %s with R = %d, marker = %s' % (K, group_id, R, marker_list[index])
        ax.plot(range(len(p)), p, color = 'k', ls = 'None', marker = marker_list[index])
        index += 1
        
        ax.set_xlabel('Thread index')
        ax.set_ylabel('Precision')
        ax.set_title('Precision@K for %s (R = %d)' % (group_id, R))
        
    plt.show()
    
def draw_precision_subplots(topic_id_list, R, group_id, prediction_result):
    """ 将几个图放进不同的subplots中，并隐藏xlabel
    """
    K_set = set([10, 20, 30, 40]) # 目前启用的K的集合
    fig = plt.figure()
    ax_list = []
    ax_list.append(fig.add_subplot(2, 2, 1))
    ax_list.append(fig.add_subplot(2, 2, 2))
    ax_list.append(fig.add_subplot(2, 2, 3))
    ax_list.append(fig.add_subplot(2, 2, 4))
    
    # 寻找最大的precision
    max_precision = 0
    for K, precision in prediction_result:
        if not K in K_set:
            continue
        for topic_id in topic_id_list:
            if precision[topic_id] > max_precision:
                max_precision = precision[topic_id]
    # 找到离max_precision最近的0.05, 0.10, 0.15...
    r = pylab.frange(0, 1, 0.05)
    x_max = 0
    for i in range(len(r)):
        if max_precision > r[i] and max_precision <= r[i+1]:
            x_max = r[i+1]
            break
    step = x_max * 1.0 / 5 # 步长
    
    # 找到最大的n
    max_n = 0
    index = 0
    for K, precision in prediction_result:
        if not K in K_set:
            continue
        p = []
        for topic_id in topic_id_list:
            p.append(precision[topic_id])
            
        # 选取axes子区域
        ax = ax_list[index]
        n, bins, patches = ax.hist(p, pylab.frange(0, x_max, step), normed = False, facecolor='blue', alpha=0.75)
        if max(n) > max_n:
            max_n = max(n)
        ax.cla() # 清除测试直方图
        index += 1
        
    # 找到离max_n最近的5，10，15，20...
    r = range(0, 500, 5)
    assert(len(topic_id_list) < 500)
    max_count = 0
    for i in range(len(r)):
        if max_n > r[i] and max_n <= r[i+1]:
            max_count = r[i+1]
            break
    
    # 开始真正的画图
    index = 0
    for K, precision in prediction_result:
        if not K in K_set:
            continue
        p = []
        for topic_id in topic_id_list:
            p.append(precision[topic_id])
            
        # 选取axes子区域
        ax = ax_list[index]
        n, bins, patches = ax.hist(p, pylab.frange(0, x_max, step), normed = False, facecolor='blue', alpha=0.75)
        #ax.set_xlabel('Precision@%d' % K)
        ax.set_xlim(0, x_max)
        ax.set_ylabel('Number of threads')
        ax.set_ylim(0, max_count)
        ax.set_title('Precision@%d' % K)
        ax.set_xticks(pylab.frange(0, x_max, step))
        ax.set_yticks(range(0, max_count, 10))
        ax.grid(True)
        
        # 控制显示
        if index == 0:
            for ticklabel in ax.get_xticklabels():
                ticklabel.set_visible(False)
            
        elif index == 1:
            for ticklabel in ax.get_xticklabels():
                ticklabel.set_visible(False)
            for ticklabel in ax.get_yticklabels():
                ticklabel.set_visible(False)
            ax.set_ylabel('')
        elif index == 2:
            ax.set_xlabel('Precision')
            pass
        elif index == 3:
            for ticklabel in ax.get_yticklabels():
                ticklabel.set_visible(False)
            ax.set_xlabel('Precision')
            ax.set_ylabel('')
            
        else:
            assert(False)
        
        index += 1
        
    plt.show()
        
        
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'python draw_precision.py group_id R'
        sys.exit(0)
    
    group_id = sys.argv[1]
    R = int(sys.argv[2])
    
    prediction_result = []
    for K in range(5, 50, 5):
        precision = dict()
        for index in range(5):
            result_path = 'result/%s/prediction-result-%d-%d-%d' % (group_id, R, index, K)
            f = open(result_path)
            for line in f:
                line = line.strip()
                seg_list = line.split()
                topic_id = seg_list[0]
                p = float(seg_list[1])
                if topic_id in precision:
                    precision[topic_id] += p
                else:
                    precision[topic_id] = p
            f.close()
        # 求平均值
        for topic_id in precision:
            precision[topic_id] = precision[topic_id] / 5
        prediction_result.append((K, precision))
    
    topic_id_list = []
    for topic_id in prediction_result[0][1]:
        topic_id_list.append(topic_id)
        
    #draw_precision(topic_id_list, R, group_id, prediction_result)
    draw_precision_subplots(topic_id_list, R, group_id, prediction_result)

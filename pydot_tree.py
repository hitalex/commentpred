#coding:utf8

"""
此脚本将从文件输入评论的结构，并画出评论树结构
"""

import pydot

# 读入所有的topic id列表
topic_list = []
f = open("data/test.txt")
for tid in f:
    tid = tid.strip()
    if tid is not "":
        topic_list.append(tid)
        
        
# 对于每个topic，做图
for tid in topic_list:
    f = open("structure/test/" + tid + ".txt")
    # created a directed graph
    graph = pydot.Dot(graph_type='digraph')
    root = pydot.Node('topic_' + tid, label = tid)
    graph.add_node(root)
    
    for line in f:
        line = line.strip()
        item_list = line.split(" ")
        for i in range(len(item_list)):
            item_list[i] = item_list[i].strip()
        
        node = pydot.Node(item_list[0], label=item_list[1])
        graph.add_node(node)
        if len(item_list) == 4:
            graph.add_edge(pydot.Edge(item_list[2], item_list[0]))
            #print "Add edge from ", item_list[0], " to ", item_list[2] 
        elif len(item_list) == 2:
            graph.add_edge(pydot.Edge('topic_' + tid, item_list[0]))
        else:
            print "Bad comment structure."
        
    graph.write_png('structure/test/' + tid + '.png')

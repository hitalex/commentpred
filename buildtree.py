#coding:utf8

"""
buildtree.py
~~~~~~~~~~~~~

此脚本按照评论结构画出评论树
"""
import os
import sys

import networkx as nx
import matplotlib.pyplot as plt

try:
    from networkx import graphviz_layout
except ImportError:
    raise ImportError("This example needs Graphviz and either PyGraphviz or Pydot")

if len(sys.argv) <= 1:
    print "Group IDs were not provided."
    sys.exit()
# add group ids
group_id = sys.argv[1]

# 读入所有的topic id列表
topic_list = []
print "Loading topic list for group: ", group_id
f = open("data/" + group_id + ".txt")
for tid in f:
    tid = tid.strip()
    if tid is not "":
        topic_list.append(tid)
        
# 对于每个topic，做图
plt.figure(num=None, figsize=(20, 20), dpi=50, facecolor='w', edgecolor='k')

path = "image/" + group_id + "/"
if not os.path.exists(path):
    os.mkdir(path)
        
for tid in topic_list:
    print "Processing for topic: ", tid
    try:
        path = "structure/" + group_id + "/" + tid + ".txt"
        f = open(path, "r")
    except IOError:
        print "File not found. %s" % path
        continue
        
    color = 0
    node_color = []
    G = nx.Graph()
    G.add_node("topic_" + tid)
    node_color.append(color)
    
    for line in f:
        line = line.strip()
        item_list = line.split(" ")
        for i in range(len(item_list)):
            item_list[i] = item_list[i].strip()
        
        G.add_node(item_list[0], user_id = item_list[1])
        color += 1
        node_color.append(color)
        if len(item_list) == 4: 
            # 判断引用的评论是否已经在节点中
            if (not G.has_node(item_list[2])) or (not G.has_node(item_list[0])):
                print "Reference comment not found. Comment id: ", item_list[0], " Ref comment id: ", item_list[2]
            G.add_edge(item_list[0], item_list[2])
            #print "Add edge from ", item_list[0], " to ", item_list[2] 
        elif len(item_list) == 2:
            G.add_edge("topic_" + tid, item_list[0])
            #print "Add edge from topic_"+tid, " to ", item_list[0]
        else:
            print "Bad comment structure."
    
    if len(G.nodes()) == 0:
        continue
        
    if len(node_color) != len(G.nodes()):
        print "Color node: ", len(node_color)
        print "Number of nodes: ", len(G.nodes())
        print "Not enough color node.", "Error in topic: ", tid
        continue
    
    h = plt.figure()
    pos=nx.graphviz_layout(G,prog="twopi",root="topic_"+tid)
    nx.draw(G, pos, with_labels=False, node_color=node_color, alpha=0.7, node_size=30, hold=False)
    plt.savefig( "image/" +group_id + "/" + tid +  ".jpg", dpi=200)
    plt.close(h)

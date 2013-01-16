#coding:utf8

"""
此文件调用 images2gif 模块来为每个topic生成一张gif图像
并将图片保存在gif/group_id/topic_id中
"""
import os

import matplotlib.pyplot as plt
import networkx as nx
from PIL import Image

import images2gif

def save_image(group_id, topic_id, G, node_color):
    """
    G the graph to be drawed
    """
    index = len(G.nodes()) - 1
    h = plt.figure()
    pos=nx.graphviz_layout(G,prog="twopi",root="topic_"+topic_id)
    nx.draw(G, pos, with_labels=False, node_color=node_color, alpha=0.7, node_size=30, hold=False)
    path = "gif/%s/%s/%s_%d.jpg" % (group_id, topic_id, topic_id, index)
    print "Saving jpg image: ", path
    plt.savefig( path , dpi=200)
    plt.close(h)

def create_image(group_id, topic_id):
    # 创建存放图片的路径
    path = "gif/" + group_id + "/"
    if not os.path.exists(path):
        os.mkdir(path)
        
    path = "gif/" + group_id + "/" + topic_id + "/"
    if not os.path.exists(path):
        os.mkdir(path)
        
    print "Processing for topic: ", topic_id
    try:
        path = "structure/" + group_id + "/" + topic_id + ".txt"
        f = open(path, "r")
    except IOError:
        print "File not found. %s" % path
        return 0
        
    color = 0
    node_color = []
    G = nx.Graph()
    G.add_node("topic_" + topic_id)
    node_color.append(color)
    save_image(group_id, topic_id, G, node_color)
    
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
            G.add_edge("topic_" + topic_id, item_list[0])
            #print "Add edge from topic_"+topic_id, " to ", item_list[0]
        else:
            print "Bad comment structure."
            
        save_image(group_id, topic_id, G, node_color)
    
    if len(G.nodes()) == 0:
        return 0
        
    if len(node_color) != len(G.nodes()):
        print "Color node: ", len(node_color)
        print "Number of nodes: ", len(G.nodes())
        print "Not enough color node.", "Error in topic: ", topic_id
        return 0
    
    return len(G.nodes())
        
def create_gif(group_id, topic_id, count): # count 为生成的图片数量
    # 利用已经生成jpg图像生成gif图像
    images = []
    
    for i in range(count):
        path = "gif/%s/%s_%d.jpg" % (group_id, topic_id, i)
        img = Image.open(path)
        images.append(img)
    
    path = "gif/%s/%s/%s.gif" % (group_id, topic_id, topic_id)
    print "Saving GIF iamge: ", path
    images2gif.writeGif(path, images, duration=0.5, nq=0.1)
    
if __name__ == '__main__':
    group_id = 'insidestory'
    topic_id = '23061108'
    
    count = create_image(group_id, topic_id)
    create_gif(group_id, topic_id, count)

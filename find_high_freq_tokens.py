#coding=utf-8

"""
从Dictionary中得到高document frequency的token
"""
import operator
import codecs

import gensim

group_id = 'ustv'
indicator = 'title-only'
base_path = 'tables/' + group_id + '/'
dict_path = base_path + group_id + '-dict-' + indicator + '.dict'
dictionary = gensim.corpora.Dictionary.load(dict_path)

dfs_list = []
for token, tokenid in sorted(dictionary.token2id.iteritems()):
    dfs_list.append((tokenid, token, dictionary.dfs.get(tokenid, 0)))

dfs_list = sorted(dfs_list, key = operator.itemgetter(2), reverse = True)

f = codecs.open(base_path + '/dict-dfs', 'w', 'utf-8')
for item in dfs_list:
    f.write('Token id: %d, Token: %s, dfs: %d\n' % item)
    
f.close()

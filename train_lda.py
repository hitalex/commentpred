#encoding=utf-8

"""
此脚本根据已经准备好的文本集，训练LDA模型
"""

import logging
import sys
import codecs
from datetime import datetime

reload(sys)
sys.setdefaultencoding('utf-8')

from gensim import corpora, models, similarities
from gensim.models.ldamodel import LdaModel

from logconfig import congifLogger

STOP_WORDS_PATH = 'dataset/chinese-english-stopwords.txt'

# config logging
log = logging.getLogger('Main.train_lda')
congifLogger("train_lda.log", 5)

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO, filename = "train_lda.log")

def load_stop_words():
    """导入所有的中文停用词
    """
    stoplist = set()
    f = codecs.open(STOP_WORDS_PATH, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        stoplist.add(line)
        
    return stoplist
    
def load_documents(file_path):
    """ 导入所有的文档
    Note：此时所有的文档都放在一个文件中
    """
    documents = []
    f = codecs.open(file_path, 'r', 'utf-8')
    for line in f:
        line = line.strip()
        if line != '':
            documents.append(line)
        
    return documents
    
def is_filtered_word(word):
    """ 判断某个单词是否满足token的标准
    """
    # 至少是两个字词，同时过滤单个英文字符
    if len(word) == 1:
        return True
    
    # 过滤数字
    flag = True
    try:
        float(word)
    except ValueError:
        flag = False
    # 如果没有引起ValueError，则是数字
    if flag:
        return True
    
    return False
        
    
def build_dict_corpus(source_text_path, corpus_path, dict_path):
    """ 建立字典和corpus，并存储到文件中
    `source_text_path` 源文本所在的文件路径
    `corpus_path` 存放corpus文件的路径
    `dict_path` 字典存储路径
    """
    log.info('Loading stop words...')
    stoplist = load_stop_words()
    log.info('Done.')
    
    log.info('Loading documents...')
    documents = load_documents(source_text_path)
    log.info('Done.')
    
    log.info('Remove one time words...')
    texts = [[word for word in document.lower().split(' ') if word not in stoplist]
        for document in documents]
    # remove words that appear only once
    #print 'Number of documents: %d, then find all tokens...' % len(texts)
    #all_tokens = sum(texts, [])
    #print 'Number of all tokens: %d' % len(all_tokens)
    #print 'finding tokens that appear only once...'
    #tokens_once = set(word for word in set(all_tokens) if all_tokens.count(word) == 1)
    #print 'Number of token_once: %d, done' % len(tokens_once)
    #tokens_once = []
    # 去掉只出现一次的词和只包含一个字的词
    # 在这里需要保证使用的是python的unicode编码
    texts = [[word for word in text if not is_filtered_word(word)]
        for text in texts]
    log.info('Done.')
    
    # build dict
    log.info('Building and saving dict...')
    dictionary = corpora.Dictionary(texts)
    log.info('Filter extremes...')
    # filter extremes, 
    # see: http://radimrehurek.com/gensim/corpora/dictionary.html#gensim.corpora.dictionary.Dictionary.filter_extremes
    dictionary.filter_extremes(no_below = 1, no_above = 0.8, keep_n = None)
    dictionary.save(dict_path) # store the dictionary, for future reference
    log.info('Done.')
    
    log.info('Building and saving corpus...')
    corpus = [dictionary.doc2bow(text) for text in texts]
    corpora.MmCorpus.serialize(corpus_path, corpus) # store to disk, for later use
    log.info('Done')
    

def main(argv):
    if len(argv) < 4:
        print 'python train_lda.py group_id num_topics passes'
        sys.exit(1)
        
    group_id = argv[1]
    num_topics = int(argv[2])
    passes = int(argv[3])
    log.info('Prepare corpus for group: %s' % group_id)

    base_path = 'tables/' + group_id + '/'
    model_base_path = 'ldamodels/' + group_id + '/'
    
    # buid dict and corpus
    #now = datetime.now()
    indicator = 'title-comment'
    source_path = base_path + 'corpus-topic-comment'
    
    corpus_path = model_base_path + 'corpus-'+ indicator + '-' + group_id + '.mm'
    dict_path = model_base_path + 'dict-' + indicator + '-' + group_id + '.dict'
    
    log.info('Building the dict...')
    build_dict_corpus(source_path, corpus_path, dict_path)
    
    log.info('Loading dict from pre-saved file...')
    dictionary = corpora.Dictionary.load(dict_path)
    log.info('Done')
    
    #dictionary.save_as_text(base_path + 'text-dict.txt')
    
    log.info('Build a lda model...')
    log.info('Loading corpus from pre-saved .mm file...')
    mmcorpus = corpora.MmCorpus(corpus_path)
    log.info('Done')
    
    log.info('Training lda model...')
    model = LdaModel(mmcorpus, num_topics=num_topics, id2word = dictionary, passes = passes)
    model_path = model_base_path + '-' + indicator + '-' + group_id + '.ldamodel'
    model.save(model_path)
    log.info('Done.')
    
    model = LdaModel.load(model_path)
    model.show_topics(topics=num_topics, topn=10, log=True)

if __name__ == '__main__':
    main(sys.argv)

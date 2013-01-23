#encoding=utf-8

"""
此脚本根据已经准备好的文本集，训练LDA模型
"""

import logging
import sys
import codecs

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
    all_tokens = sum(texts, [])
    tokens_once = set(word for word in set(all_tokens) if all_tokens.count(word) == 1)
    # 去掉只出现一次的词和只包含一个字的词
    # 在这里需要保证使用的是python的unicode编码
    texts = [[word for word in text if (word not in tokens_once and len(word) > 1)]
        for text in texts]
    log.info('Done.')
    
    # build dict
    log.info('Building and saving dict...')
    dictionary = corpora.Dictionary(texts)
    dictionary.save(dict_path) # store the dictionary, for future reference
    log.info('Done.')
    
    log.info('Building and saving corpus...')
    corpus = [dictionary.doc2bow(text) for text in texts]
    corpora.MmCorpus.serialize(corpus_path, corpus) # store to disk, for later use
    log.info('Done')
    

def main(argv):
    if len(argv) < 2:
        print 'Group ID not provided.'
        sys.exit(1)
        
    group_id = argv[1]
    log.info('Prepare corpus for group: %s' % group_id)

    base_path = 'tables/' + group_id + '/'
    
    # buid dict and corpus
    build_dict_corpus(base_path + 'source-text.txt', base_path + group_id + '.mm', base_path + group_id + '.dict')
    
    log.info('Loading dict from pre-saved file...')
    dictionary = corpora.Dictionary.load(base_path + group_id + '.dict')
    log.info('Done')
    
    dictionary.save_as_text(base_path + 'text-dict.txt')
    
    log.info('Build a lda model...')
    log.info('Loading corpus from pre-saved .mm file...')
    mmcorpus = corpora.MmCorpus(base_path + group_id + '.mm')
    log.info('Done')
    
    log.info('Training lda model...')
    model = LdaModel(mmcorpus, num_topics=10, id2word = dictionary, passes = 20)
    model.save(base_path + group_id + '.ldamodel')
    log.info('Done.')
    
    model = LdaModel.load(base_path + group_id + '.ldamodel')
    model.show_topics(topics=3, topn=10, log=True)

if __name__ == '__main__':
    main(sys.argv)

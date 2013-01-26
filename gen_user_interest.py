#encoding=utf8

"""
根据LDA模型和用户的关注数据，产生用户的兴趣向量
"""
import sys
import codecs
import logging

from gensim import models, corpora

from logconfig import congifLogger

# config logging
log = logging.getLogger('Main.interest')
congifLogger("gen_user_interest.log", 5)

# python gen_user_interest.py ustv tables/ustv/behavior-ustv.txt tables/ustv/ustv-title-comment.ldamodel tables/ustv/ustv-dict-title-comment.dict tables/ustv/user_interest

def main(argv):
    if len(argv) < 6:
        print 'Not enough parameters.'
        sys.exit(0)
    group_id = argv[1]
    behavior_path = argv[2]
    model_path = argv[3]
    dict_path = argv[4]
    user_interest_path = argv[5]
    
    bf = codecs.open(behavior_path, 'r', 'utf-8')
    uf = codecs.open(user_interest_path, 'w', 'utf-8')
    log.info('Loading LDA model...')
    model = models.ldamodel.LdaModel.load(model_path) # load model
    log.info('Loading dict...')
    dictionary = corpora.dictionary.Dictionary.load(dict_path) # load dict
    
    for line in bf:
        line = line.strip()
        seg_list = line.split('[=]')
        uid = seg_list[0]
        uf.write(uid + '[=]')
        text = seg_list[3]
        document = text.split(' ')
        doc_bow = dictionary.doc2bow(document)
        doc_lda = model.__getitem__(doc_bow, eps = 0)
        #print doc_lda
        probs = [topicvalue for topicid, topicvalue in doc_lda]
        str_probs = [str(prob) for prob in probs]
        uf.write(','.join(str_probs) + '\n')
        
    bf.close()
    uf.close()

if __name__ == '__main__':
    main(sys.argv)

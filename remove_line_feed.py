#encoding=utf-8

"""
功能：将TopicInfo或者CommentInfo中的每条记录放在一行中，即消除换行符
"""
import sys
import codecs

def remove(file_path, new_file_path):
    f = codecs.open(file_path, 'r', 'utf-8')
    nf = codecs.open(new_file_path, 'w', 'utf-8')
    row = ''
    count = 0
    for line in f:
        line = line.strip()
        if line != '[*ROWEND*]':
            row += (line + ' ')
            continue
        nf.write(row + '\n')
        count += 1
        row = ''
        
    f.close()
    nf.close()

if __name__ == '__main__':
    remove(sys.argv[1], sys.argv[2])

crawler
=======

#### A Web crawler.  
* Start from the url and crawl the web pages with a specified depth.  
* Save the pages which contain a keyword(if provided) into database.  
* Support multi-threading.  
* Support logging.  
* Support self-testing.  

#### 注意：
目前已经修改了原来的代码，现在用于抓取豆瓣小组的信息，包括小组ID、创建时间、组内人数等。

### 抓取操作步骤
* 抓取小组的ID, GID
* 根据得到的小组ID，抓取小组的讨论列表，放在data/GID.txt
* 根据讨论列表，抓取小组的评论数据，并生成评论结构, 放在data/GID/topic_id.txt和structure/GID/topic_id.txt
* 可视化评论树，放在image/GID/topic_id.jpg

usage
-------------
```shell
main.py [-h] -u URL -d DEPTH [--logfile FILE] [--loglevel {1,2,3,4,5}]
               [--thread NUM] [--dbfile FILE] [--key KEYWORD] [--testself]
```

optional arguments:
-------------
```shell
  -h, --help            show this help message and exit
  -u URL                Specify the begin url
  -d DEPTH              Specify the crawling depth
  --logfile FILE        The log file path, Default: spider.log
  --loglevel {1,2,3,4,5}
                        The level of logging details. Larger number record
                        more details. Default:3
  --thread NUM          The amount of threads. Default:10
  --dbfile FILE         The SQLite file path. Default:data.sql
  --key KEYWORD         The keyword for crawling. Default: None. For more then
                        one word, quote them. example: --key 'Hello world'
  --testself            Crawler self test

```

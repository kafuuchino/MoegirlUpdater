# -*- coding: utf-8 -*-
import sys
reload(sys)
import datetime
import json
import urllib,urllib2
import calendar
import time
import os
from bs4 import BeautifulSoup
import logging,logging.handlers
import traceback
import weibo
from collections import OrderedDict
sys.setdefaultencoding('utf-8')
#from MU_conf import MUconf
from MU_utils import r,unique_str,loggingInit,for_cat,for_rc,_decode_dict
os.chdir(os.path.dirname(sys.argv[0]))
PUSHEDPREFIX="PUSHED-"
EDITEDPREFIX='EDITED-'
EXPIRETIME='72*3600'
THREEDAYS=259200
log=loggingInit('log/update.log')
def GetCategory(title):
    apiurl="http://zh.moegirl.org/api.php"
    parmas = urllib.urlencode({'format':'json','action':'query','prop':'categories','titles':title})
    req=urllib2.Request(url=apiurl,data=parmas)
    res_data=urllib2.urlopen(req)
    ori=res_data.read()
    categories=json.loads(ori, object_hook=_decode_dict)
    cat=for_cat(categories)
    return cat
def GetImage(title):
    try:
        url="http://zh.moegirl.org/"+title
        f=urllib.urlopen(url)
    except:
        return None
    src=f.read()
    f.close
    ssrc=BeautifulSoup(src,"html.parser")
    try:
        image_div=ssrc.find_all('a',class_='image')
        for i in range(len(image_div)):
            imgtag=image_div[i].find('img')
            if (int(imgtag['width']) > 200 and int(imgtag['height']) > 100): #出问题都是anna的锅
                img = imgtag['src']
                break
            else:
                continue
    except:
        return None
    isExists=os.path.exists('imgcache')
    if not isExists:
        os.makedirs('imgcache')
    name=unique_str()
    TheImageIsReadyToPush=False
    if locals().has_key("img"):
        try:
            with open('imgcache/'+name,'wb') as f:
                con=urllib.urlopen("http:"+img)
                f.write(con.read())
                f.flush()
                TheImageIsReadyToPush=True
                r.hset('img',EDITEDPREFIX+title,name)
        except BaseException, e:
                log.debug(e)
                return None
    else:
        return None
    return TheImageIsReadyToPush
def ForbiddenItemsFilter(item):
    cat=GetCategory(item)
    ForCat="Category:屏蔽更新姬推送的条目"
    for i in range(len(cat)):
        if cat[i]==ForCat.encode('utf-8'):
            return False
            break
    return True
def ForbiddenItemPushed(title):
    for key in r.hkeys('queue'):
        if r.hget('queue',key)==EDITEDPREFIX+title:
            return False
            break
    return True

class MU_UpdateData(object):
    def __init__(self):
        super(MU_UpdateData,self).__init__()
        self.cache=[]
        self.SendFlag=False
    def initupdater(self):
        self.GetRecentChanges(2)
    def GetRecentChanges(self):
        value=for_rc()
        for i in range(len(value)):
            if value[i]['newlen']>1000:
                self.cache.append(value[i]['title'])
            else:
                pass
        return self.cache
    def FilterValid(self):
        self.GetRecentChanges()
        self.cache=filter(ForbiddenItemsFilter,self.cache)
        self.cache=filter(ForbiddenItemPushed,self.cache)
        return self.cache
    def SaveRecentChanges(self):
        self.FilterValid()
        for item in self.cache:
            flag=GetImage(item)
            if flag==True:
                itemkey=EDITEDPREFIX+item
                r.hset('queue',itemkey,item)
                timenow=time.time()
                r.zadd('expire',itemkey,timenow)
            else:
                pass
    def RemoveExpiredItems(self):
        timenow=time.time()
        ThreeDaysAgo=time.time()-THREEDAYS
        zset=r.zrangebyscore('expire',ThreeDaysAgo,timenow)
        hkeys=r.hkeys('queue')
        setofzset=set(zset)
        setofhkeys=set(hkeys)
        intersection=list(setofzset&setofhkeys)
        print intersection
        print zset
        for i in range(len(hkeys)):
            if hkeys[i] not in intersection:
                r.zrem('expire',hkeys[i])
                r.hdel('queue',hkeys[i])
                name=r.hget('img',hkeys[i])
                os.remove('imgcache/'+name)
                r.hdel('img',hkeys[i])

item='123'
update=MU_UpdateData()
#update.SaveRecentChanges()
update.RemoveExpiredItems()
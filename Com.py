# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import signal
import requests
from time import sleep
import pandas as pd
import time

class ApiException(Exception):
    pass

def signal_handler(signum, frame):
    global shutdown
    signal_handler(signal.SIGINT, signal.SIG_DFL)
    shutdown = True
    
API_KEY = {'X-API-Key': '114514'}
shutdown = False    
base_url="http://localhost:9999/v1"

def get_header(string):
    words=string.split()
    if "RBOB" in words:
        return "RBOB"
    elif "HEATING" in words:
        return "HO"
    else: 
        return "Refinery"
    
    
def parse_news_content(header, content):
    if header=='HO':
        words=content.split()
        #find avg temp
        avg_temp=words[words.index('average')+4]
        #realized temp
        real_temp=words[words.index('realized')+4]
        #sd
        sd=words[words.index('deviation')+6]
        #expected change
        change=0
        if content.find('respond')> 0:
            c=words[words.index('respond')+6]
            c=c.rstrip('%.')
            change=float(c)/100
        #current price
        cur_p=words[words.index('HO')+2]
        cur_p=cur_p.lstrip('$')
        cur_p=cur_p.rstrip('.<br><br>')
        price=float(cur_p)*(1+change)+(float(real_temp)-float(avg_temp))/float(sd)
        return price
    elif header=='RBOB':
        if len(content)>0:
           words=content.split('.')
           return words[-2]
        else:
            return ""
    
    
    
def get_new(s):
    url=base_url+'/news'
    resp=s.get(url)
    news_book=pd.DataFrame(columns=['tick','header','content'])
    if resp.ok:
        book=resp.json()
        for i in range(3):
            #print(book[i])
            tick=book[i]['tick']
            header=get_header(book[i]['headline'])
            content=parse_news_content(header, book[i]['body'])
            row=pd.DataFrame({'tick':tick,'header':header,'content':content},index=[0])
            news_book=pd.concat([news_book,row],ignore_index=True)
        return news_book
    else:
        raise ApiException('Authorization error. Please check API key')  
    



def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        while True:
            news=get_new(s)
            print(news)
            time.sleep(10)


if __name__ == "__main__":
    main()
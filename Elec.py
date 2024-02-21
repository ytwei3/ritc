# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 17:52:30 2024

@author: yzhang3336
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

def get_header(headline, body):
    demand=0
    low=0
    high=0
    avg=0
    hl_words=headline.split()
    body_words=body.split()
    if "TEMPERATURE" in hl_words:
        if "between" in body_words:
            low=float(body_words[body_words.index('between')+ 1])
            high=float(body_words[body_words.index('between')+3])
            avg=(low+high)/2
        elif "average" in body_words:
            avg=float(body_words[body_words.index('average')+5])

    
    demand=200-15*avg+0.8*avg*avg-0.01*avg*avg*avg
    return low, high, avg, demand
    

    
def get_news(s):
    url=base_url+'/news'
    resp=s.get(url)
    news_book=pd.DataFrame(columns=['tick','low','high','demand_S','demand_F'])
    if resp.ok:
        book=resp.json()
        for i in range(3):
            #print(book[i])
            tick=book[i]['tick']
            low,high,avg,demand_S=get_header(book[i]['headline'], book[i]['body'])
            row=pd.DataFrame({'tick':tick,'low':low,'high':high,'demand_S':round(demand_S,0),'demand_F':round(demand_S/5,0)},index=[0])
            news_book=pd.concat([news_book,row],ignore_index=True)
        return news_book
    else:
        raise ApiException('Authorization error. Please check API key') \
            

def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        while True:
            news_list=get_news(s)
            print(news_list)
            time.sleep(20)

if __name__ == "__main__":
    main()
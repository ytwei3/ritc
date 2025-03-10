import signal
import time

import requests
from time import sleep

API_KEY = {'X-API-KEY': ''}

RATE_LIMIT_PER_SECOND = 100
SPEED_BUMP = 1 / RATE_LIMIT_PER_SECOND

# quantity
quantity = 10000
quantity_limit = 10000

# potential profit
buy_potential_profit = 0.02
sell_potential_profit = 0.02

# set interval to beat potential player
INTERVAL = 0.00

PROFIT_INTERVAL = 0.02


def simplest_algo(s):
    trading = True
    while trading:
        resp = s.get('http://localhost:9999/v1/securities').json()
        crzy_m_bid = resp[0]['bid']
        crzy_m_ask = resp[0]['ask']
        crzy_a_bid = resp[1]['bid']
        crzy_a_ask = resp[1]['ask']

        if crzy_m_bid > crzy_a_ask:
            s.post('http://localhost:9999/v1/orders',
                   params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': quantity, 'action': 'BUY'})
            s.post('http://localhost:9999/v1/orders',
                   params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': quantity, 'action': 'SELL'})
            sleep(0.2)
            continue

        if crzy_a_bid > crzy_m_ask:
            s.post('http://localhost:9999/v1/orders',
                   params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': quantity, 'action': 'BUY'})
            s.post('http://localhost:9999/v1/orders',
                   params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': quantity, 'action': 'SELL'})
            sleep(0.2)


def limit_only(s):
    trading = True
    while trading:
        resp = s.get('http://localhost:9999/v1/securities').json()
        crzy_m_bid = resp[0]['bid']
        crzy_m_ask = resp[0]['ask']
        crzy_a_bid = resp[1]['bid']
        crzy_a_ask = resp[1]['ask']

        cost = resp[0]['vwap']
        pos = resp[0]['position']

        if crzy_m_bid > crzy_a_ask:
            s.post('http://localhost:9999/v1/orders',
                   params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'price' : crzy_a_ask + INTERVAL, 'quantity': quantity, 'action': 'BUY'})
            s.post('http://localhost:9999/v1/orders',
                   params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'price' : crzy_m_bid - INTERVAL, 'quantity': quantity, 'action': 'SELL'})
            sleep(0.05)
            continue

        if crzy_a_bid > crzy_m_ask:
            s.post('http://localhost:9999/v1/orders',
                    params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'price' : crzy_m_ask + INTERVAL, 'quantity': quantity, 'action': 'BUY'})
            s.post('http://localhost:9999/v1/orders',
                    params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'price' : crzy_a_bid - INTERVAL, 'quantity': quantity, 'action': 'SELL'})
            sleep(0.05)
            continue

        # # # deal with overbuy/oversell position
        if pos > 0:
            # pick the max difference with crzy_m_bid and crzy_a_ask
            best_ask_price = max(cost, crzy_m_bid, crzy_a_bid)
            sell_limit_quantity = min(10000, pos)
            if best_ask_price == crzy_m_bid and best_ask_price - cost >= PROFIT_INTERVAL:
                s.post('http://localhost:9999/v1/orders',
                       params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': sell_limit_quantity,
                               'action': 'SELL'})
                sleep(SPEED_BUMP)
            elif best_ask_price == crzy_a_bid and best_ask_price - cost >= PROFIT_INTERVAL:
                s.post('http://localhost:9999/v1/orders',
                       params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': sell_limit_quantity,
                               'action': 'SELL'})
                sleep(SPEED_BUMP)
        elif pos < 0:
            best_bid_price = min(cost, crzy_m_ask, crzy_a_ask)
            buy_limit_quantity = min(10000, -pos)
            if best_bid_price == crzy_m_ask and cost - best_bid_price - cost >= PROFIT_INTERVAL:
                s.post('http://localhost:9999/v1/orders',
                       params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': buy_limit_quantity,
                               'action': 'BUY'})
                sleep(SPEED_BUMP)
            elif best_bid_price == crzy_a_ask and cost - best_bid_price - cost >= PROFIT_INTERVAL:
                s.post('http://localhost:9999/v1/orders',
                       params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': buy_limit_quantity,
                               'action': 'BUY'})
                sleep(SPEED_BUMP)


if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    with requests.Session() as s:
        # get info for this case
        s.headers.update(API_KEY)
        r = s.get("http://localhost:9999/v1/case")
        print(r.json())

        print("speed bump: ", SPEED_BUMP)
        r = s.get("http://localhost:9999/v1/securities")

        # start the algo
        # simplest_algo(s)
        limit_only(s)
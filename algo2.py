import time
from time import sleep
import requests

import pandas as pd


API_KEY = {'X-API-Key': '114514'}
BASE_URL = "http://localhost:9999/v1"


BID_ASK_SPREAD = 0.05

INVENTORY_THRESHOLD_1 = 15000
INVENTORY_THRESHOLD_2 = 6000
INVENTORY_THRESHOLD_3 = 10000
INVENTORY_THRESHOLD_4 = -6000
INVENTORY_THRESHOLD_5 = -10000

SAFE_VALUE_1 = 6000
SAFE_VALUE_2 = 6000

K = 1


QUANTITY = 3000
SPEED_BUMP = 3


def main():
    ticker = "RIT_U"
    with requests.session() as s:
        s.headers.update(API_KEY)
        tick = s.get(BASE_URL + '/case').json()['tick']
        while 0 < tick < 300:
            print("algo2 works on tick: ", tick)
            sec = s.get(BASE_URL + '/securities').json()[0]
            book = s.get(BASE_URL + '/securities/book', params={'ticker': ticker}).json()

            bids = book['bids']
            asks = book['asks']
            position = sec['position']

            obs_bid_1 = (bids[0]['quantity'] - bids[0]['quantity_filled']) / (asks[0]['quantity'] - asks[0]['quantity_filled'])
            obs_bid_2 = (bids[1]['quantity'] - bids[1]['quantity_filled']) / (asks[1]['quantity'] - asks[1]['quantity_filled'])
            obs_bid_3 = (bids[2]['quantity'] - bids[2]['quantity_filled']) / (asks[2]['quantity'] - asks[2]['quantity_filled'])
            obs_bid_4 = (bids[3]['quantity'] - bids[3]['quantity_filled']) / (asks[3]['quantity'] - asks[3]['quantity_filled'])

            obs_ask_1 = (asks[0]['quantity'] - asks[0]['quantity_filled']) / (bids[0]['quantity'] - bids[0]['quantity_filled'])
            obs_ask_2 = (asks[1]['quantity'] - asks[1]['quantity_filled']) / (bids[1]['quantity'] - bids[1]['quantity_filled'])
            obs_ask_3 = (asks[2]['quantity'] - asks[2]['quantity_filled']) / (bids[2]['quantity'] - bids[2]['quantity_filled'])
            obs_ask_4 = (asks[3]['quantity'] - asks[3]['quantity_filled']) / (bids[3]['quantity'] - bids[3]['quantity_filled'])

            if sec['ask'] - sec['bid'] >= BID_ASK_SPREAD:
                if abs(position) < INVENTORY_THRESHOLD_1:
                    s.post(BASE_URL + '/orders',
                           params={'ticker': ticker, 'type': 'LIMIT', 'price': asks[0]['price'] - 0.01, 'quantity': QUANTITY, 'action': 'SELL'})
                    s.post(BASE_URL + '/orders',
                           params={'ticker': ticker, 'type': 'LIMIT', 'price': bids[0]['price'] + 0.01, 'quantity': QUANTITY, 'action': 'BUY'})
            elif sec['ask'] - sec['bid'] < BID_ASK_SPREAD:
                if position < INVENTORY_THRESHOLD_2:
                    if obs_bid_2 < K < obs_bid_3:
                        s.post(BASE_URL + '/orders',
                               params={'ticker': ticker, 'type': 'LIMIT', 'price': bids[2]['price'] + 0.01, 'quantity': QUANTITY, 'action': 'BUY'})
                    elif obs_bid_1 < K < obs_bid_2:
                        s.post(BASE_URL + '/orders',
                               params={'ticker': ticker, 'type': 'LIMIT', 'price': bids[1]['price'] + 0.01, 'quantity': QUANTITY, 'action': 'BUY'})
                    elif obs_bid_1 > K:
                        s.post(BASE_URL + '/orders',
                               params={'ticker': ticker, 'type': 'LIMIT', 'price': bids[0]['price'], 'quantity': QUANTITY, 'action': 'BUY'})
                elif position > INVENTORY_THRESHOLD_2 and obs_ask_1 > K:
                    s.post(BASE_URL + '/orders',
                           params={'ticker': ticker, 'type': 'LIMIT', 'price': asks[0]['price'] - 0.01, 'quantity': QUANTITY, 'action': 'SELL'})
                elif position > INVENTORY_THRESHOLD_3 and obs_ask_1 > K:
                    s.post(BASE_URL + '/orders',
                           params={'ticker': ticker, 'type': 'LIMIT', 'price': asks[0]['price'] - 0.01, 'quantity': QUANTITY, 'action': 'SELL'})

                if position > INVENTORY_THRESHOLD_4:
                    if obs_ask_2 < K < obs_ask_3:
                        s.post(BASE_URL + '/orders',
                               params={'ticker': ticker, 'type': 'LIMIT', 'price': asks[2]['price'] - 0.01, 'quantity': QUANTITY, 'action': 'SELL'})
                    elif obs_ask_1 < K < obs_ask_2:
                        s.post(BASE_URL + '/orders',
                               params={'ticker': ticker, 'type': 'LIMIT', 'price': asks[1]['price'] - 0.01, 'quantity': QUANTITY, 'action': 'SELL'})
                    elif obs_ask_1 > K:
                        s.post(BASE_URL + '/orders',
                               params={'ticker': ticker, 'type': 'LIMIT', 'price': asks[0]['price'], 'quantity': QUANTITY, 'action': 'SELL'})
                elif position < INVENTORY_THRESHOLD_4 and obs_bid_1 > K:
                    s.post(BASE_URL + '/orders',
                           params={'ticker': ticker, 'type': 'LIMIT', 'price': bids[0]['price'] + 0.01, 'quantity': QUANTITY, 'action': 'BUY'})
                elif position < INVENTORY_THRESHOLD_5 and obs_bid_1 > K:
                    s.post(BASE_URL + '/orders',
                           params={'ticker': ticker, 'type': 'LIMIT', 'price': bids[0]['price'] + 0.01, 'quantity': QUANTITY, 'action': 'BUY'})

            # ---------------------------------------------------------------
            # position management
            # ---------------------------------------------------------------
            # print(open_orders)

            open_order = s.get(BASE_URL + '/orders').json()
            if abs(position) > SAFE_VALUE_1 and len(open_order) > 12:
                s.post(BASE_URL + '/orders/cancel', params={'all': 1})
            elif abs(position) < SAFE_VALUE_2 and len(open_order) > 24:
                s.post(BASE_URL + '/orders/cancel', params={'all': 1})

            tick = s.get(BASE_URL + '/case').json()['tick']
            sleep(SPEED_BUMP)


if __name__ == '__main__':
    main()
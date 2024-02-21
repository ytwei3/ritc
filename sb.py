from time import sleep
import concurrent.futures

import requests
import time

session = requests.Session()
session.headers.update({"x-api-key": "114514"})


mega_orders_price = []

def pop_last_mega_transacted_price(ticker):
    s = session.get(f"http://localhost:9999/v1/securities/book?ticker={ticker}").json()
    for order in s['bids']:
        if order['quantity'] > 10000:
            # mega_orders.append(order)
            print("mega order found")
            print("order size: ", order['quantity'])
            print(order)
            if order["quantity_filled"] > 0:
                return order['price']

    for order in s['asks']:
        if order['quantity'] > 10000:
            # mega_orders.append(order)
            print("mega order found")
            print("order size: ", order['quantity'])
            print(order)
            if order["quantity_filled"] > 0:
                return order['price']



while True:
    pop_last_mega_transacted_price("ALPHA")
    sleep(0.2)
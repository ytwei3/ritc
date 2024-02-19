import concurrent.futures

import requests
import time

s = requests.Session()
s.headers.update({"x-api-key": "114514"})


def sumbit(ticker):
    r = s.post(
        "http://localhost:9999/v1/orders",
        params={
            "ticker": ticker,
            "type": "MARKET",
            "quantity": "1",
            "action": "BUY",
        },
    )


# send orders to ALPHA, GAMMA, THETA
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    for _ in range(1000):
        executor.submit(sumbit, "ALGO")

    print("done")
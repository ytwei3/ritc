from time import sleep
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
            "action": "SELL",
        },
    )


# send orders to ALPHA, GAMMA, THETA
# with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
#     for _ in range(20):
#         executor.submit(sumbit, "ALGO")
#
#     print("done")


# t = time.time()
# sec = s.get("http://localhost:9999/v1/securities", params={"ticker":"ALPHA"}).json()
# while True:
#     sec_new = s.get("http://localhost:9999/v1/securities", params={"ticker": "ALPHA"}).json()
#     if sec_new != sec:
#         print("changed time:", time.time() - t)
#         t = time.time()


# r = s.post("http://localhost:9999/v1/orders", params={"ticker": "ALPHA", "type": "MARKET", "quantity": "10000", "action": "BUY"})
#     for _ in range(20):
#         executor.submit(sumbit, "ALGO")
# print(r.json())


sleep(2)
for _ in range(20):
    sumbit("ALPHA")



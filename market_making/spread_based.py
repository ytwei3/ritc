from time import sleep
import requests

s = requests.Session()
s.headers.update({"x-api-key": "114514"})


def post_market_order(ticker, action, quantity):
    r = s.post(
        "http://localhost:9999/v1/orders",
        params={
            "ticker": ticker,
            "type": "MARKET",
            "quantity": quantity,
            "action": action,
        },
    )
    return r.json()


def post_limit_order(ticker, action, quantity, price):
    r = s.post(
        "http://localhost:9999/v1/orders",
        params={
            "ticker": ticker,
            "type": "LIMIT",
            "quantity": quantity,
            "action": action,
            "price": price,
        },
    )
    return r.json()


while True:
    sec = s.get("http://localhost:9999/v1/securities").json()
    cad = sec[0]
    usd = sec[1]
    hawk = sec[2]
    dove = sec[3]
    ritc = sec[4]
    ritu = sec[5]

    if ritc["ask"] > dove["bid"] + hawk["bid"] + 0.2:
        r = post_limit_order("RIT_C", "SELL", 1000, ritu["bid"] - 0.01)
        print(r)
        post_limit_order("DOVE", "BUY", 1000, dove["bid"] + 0.01)
        post_limit_order("HAWK", "BUY", 1000, hawk["bid"] + 0.01)

    if dove["ask"] + hawk["ask"] > ritc["bid"] + 0.2:
        r = post_limit_order("RIT_C", "BUY", 1000, ritc["bid"] + 0.01)
        print(r)
        post_limit_order("RIT_U", "SELL", 1000, ritu["ask"] - 0.01)

    if ritu["ask"] * usd["last"] > ritc["bid"] + 0.2:
        r = post_limit_order("RIT_C", "BUY", 1000, ritc["bid"] + 0.01)
        print(r)
        post_limit_order("RIT_U", "SELL", 1000, ritu["ask"] - 0.01)
    if ritc["ask"] > ritu["bid"] * usd["last"] + 0.2:
        r = post_limit_order("RIT_U", "BUY", 1000, ritu["bid"] + 0.01)
        print(r)
        post_limit_order("RIT_C", "SELL", 1000, ritc["ask"] - 0.01)

    # if usd["position"] != 0:
    #     r = post_market_order("USD", "SELL", usd["position"])
    #     print(r)

    sleep(1)

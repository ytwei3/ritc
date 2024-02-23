"""
CAPM Beta Algorithmic Trading Case
Rotman BMO Finance Research and Trading Lab, Uniersity of Toronto (C) All rights reserved.

Preamble:
-> Code will have a small start up period; however, trades should only be executed once forward market price is available,
hence there should not be any issue caused.

-> Code only runs effectively if the News articles are formatted as they are now. The only way to get the required new data is by parsing the text.
"""
import re
import signal
import time

import requests
from time import sleep
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
import numpy.ma as ma
import concurrent.futures


CAPM_vals = {}
expected_return = {}
real_return = {}
profit = {}

open_order_status = "NONE"
order_id = 0

front_running = True
front_running_quantity = 1000
mege_order_size = 100000000


RITM_P_ALL = np.zeros(600)
RITM_R_ALL = np.zeros(600)

aa_P_ALL = np.zeros(600)
aa_LP_ALL = np.zeros(600)
aa_R_ALL = np.zeros(600)
aa_BETA_ALL = np.zeros(600)
aa_BETAMA_ALL = np.zeros(600)
aa_BETAC_ALL = np.zeros(600)

bb_P_ALL = np.zeros(600)
bb_LP_ALL = np.zeros(600)
bb_R_ALL = np.zeros(600)
bb_BETA_ALL = np.zeros(600)
bb_BETAMA_ALL = np.zeros(600)
bb_BETAC_ALL = np.zeros(600)

cc_P_ALL = np.zeros(600)
cc_LP_ALL = np.zeros(600)
cc_R_ALL = np.zeros(600)
cc_BETA_ALL = np.zeros(600)
cc_BETAMA_ALL = np.zeros(600)
cc_BETAC_ALL = np.zeros(600)


# class that passes error message, ends the program
class ApiException(Exception):
    pass


# code that lets us shut down if CTRL C is pressed


def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True


API_KEY = {"X-API-Key": "114514"}
shutdown = False
session = requests.Session()
session.headers.update(API_KEY)


def get_position(ticker):
    sec = session.get("http://localhost:9999/v1/securities", params={"ticker": ticker}).json()
    return sec["position"]


def gross_position():
    return abs(get_position("ALPHA")) + abs(get_position("GAMMA")) + abs(get_position("THETA"))


def net_position():
    return get_position("ALPHA") + get_position("GAMMA") + get_position("THETA")


def get_tick(session):
    resp = session.get("http://localhost:9999/v1/case")
    if resp.ok:
        case = resp.json()
        return case["tick"]
    raise ApiException("fail - cant get tick")


# code that parses the first and latest news instances for forward market predictions and the risk free rate
# Important: this code only works if the only '%' character is in front of the RISK FREE RATE and the onle '$' character is in front of the forward price suggestions
def get_news(session):
    news = session.get("http://localhost:9999/v1/news")
    if news.ok:
        newsbook = news.json()
        for i in range(len(newsbook[-1]["body"])):
            if newsbook[-1]["body"][i] == "%":
                CAPM_vals["%Rf"] = round(
                    float(newsbook[-1]["body"][i - 4: i]) / 100, 4
                )
        latest_news = newsbook[0]
        if len(newsbook) > 1:
            # print(latest_news["body"])
            forward = re.findall(r"\d+\.\d+", latest_news["body"])
            if not forward:
                forward = re.findall(r"\d+", latest_news["body"])
            CAPM_vals["forward"] = float(forward[0])
            CAPM_vals["tick"] = int(re.findall(r"\d+", latest_news["body"])[0])
        return CAPM_vals
    raise ApiException("timeout")


# gets all the price data for all securities
def pop_prices(session):
    price_act = session.get("http://localhost:9999/v1/securities")
    if price_act.ok:
        prices = price_act.json()
        return prices
    raise ApiException("fail - cant get securities")

# Buy or Sell function, put in your own parameters


def buy_or_sell(session, real_return):  # , signal="BUY"):
    max_er = max(real_return, key=real_return.get)
    min_er = min(real_return, key=real_return.get)

    gross_pos = abs(get_position("ALPHA")) + abs(get_position("GAMMA")) + abs(get_position("THETA"))
    net_pos = get_position("ALPHA") + get_position("GAMMA") + get_position("THETA")
    if real_return[max_er] > 0.6 and gross_pos < 250000 and net_pos < 100000:
        r = session.post(
            "http://localhost:9999/v1/orders",
            params={
                "ticker": max_er,
                "type": "MARKET",
                "quantity": "10000",
                "action": "BUY",
            },
        )

    if real_return[min_er] < -0.6 and gross_pos < 250000 and net_pos > -100000:
        r = session.post(
            "http://localhost:9999/v1/orders",
            params={
                "ticker": min_er,
                "type": "MARKET",
                "quantity": "10000",
                "action": "SELL",
            }
        )


def post_market_order(ticker, action, quantity):
    r = session.post(
        "http://localhost:9999/v1/orders",
        params={
            "ticker": ticker,
            "type": "MARKET",
            "quantity": quantity,
            "action": action,
        },
    )

    if r.status_code == 429:
        wait = r.json()["wait"]
        sleep(wait)
        post_market_order(ticker, action, quantity)

    return r


def post_limit_order(ticker, action, quantity, price):
    r = session.post(
        "http://localhost:9999/v1/orders",
        params={
            "ticker": ticker,
            "type": "LIMIT",
            "quantity": quantity,
            "action": action,
            "price": price,
        },
    )

    if r.status_code == 429:
        wait = r.json()["wait"]
        sleep(wait)
        post_market_order(ticker, action, quantity)

    return r


def pop_last_mega_transacted_price(ticker):
    s = session.get(f"http://localhost:9999/v1/securities/book?ticker={ticker}").json()
    for order in s['bids']:
        if order['quantity'] > 10000:
            print("mega order found")
            print("order size: ", order['quantity'])
            print(order)
            if order["quantity_filled"] > 0:
                return order['price']

    for order in s['asks']:
        if order['quantity'] > 10000:
            print("mega order found")
            print("order size: ", order['quantity'])
            print(order)
            if order["quantity_filled"] > 0:
                return order['price']

    raise Exception("No last transacted mega order found")


def setup_portfolio(CAPM_vals, real_return, action):
    max_er = max(real_return, key=real_return.get)
    min_er = min(real_return, key=real_return.get)

    # gross_pos = abs(get_position("ALPHA")) + abs(get_position("GAMMA")) + abs(get_position("THETA"))
    # net_pos = get_position("ALPHA") + get_position("GAMMA") + get_position("THETA")
    for _ in range(10):
        post_market_order(max_er, "BUY" if action == "BUY" else "SELL", 10000)

    for _ in range(10):
        r = post_market_order(min_er, "SELL" if action == "SELL" else "BUY", 10000)
        print(r)

    for _ in range(5):
        post_market_order(max_er, "BUY" if action == "BUY" else "SELL", 10000)


def close_all_positions(session):
    securities = session.get("http://localhost:9999/v1/securities").json()
    for sec in securities:
        if sec["position"] > 0:
            position = sec["position"]
            while position > 0:
                session.post(
                    "http://localhost:9999/v1/orders",
                    params={
                        "ticker": sec["ticker"],
                        "type": "MARKET",
                        "quantity": min(position, 10000),
                        "action": "SELL",
                    },
                )
                position -= 10000
                sleep(0.1)
        elif sec["position"] < 0:
            position = sec["position"]
            while position < 0:
                session.post(
                    "http://localhost:9999/v1/orders",
                    params={
                        "ticker": sec["ticker"],
                        "type": "MARKET",
                        "quantity": min(-position, 10000),
                        "action": "BUY",
                    },
                )
                position += 10000
                sleep(0.1)


def get_last_transacted_mega_order_price(ticker):
    s = session.get(f"http://localhost:9999/v1/securities/book", params={"ticker": ticker}).json()
    for open_order in s['bids']:
        if open_order['quantity'] > 10000 and open_order['quantity_filled'] > 0:
            return open_order['price']

    for open_order in s['asks']:
        if open_order['quantity'] > 10000 and open_order['quantity_filled'] > 0:
            return open_order['price']

    return None


def mega_order_exists(ticker, side):
    s = session.get(f"http://localhost:9999/v1/securities/book", params={"ticker": ticker}).json()
    for open_order in s[side]:
        if open_order['quantity'] > 10000:
            return True

    return False

def retrieve_mega_order(ticker, side=""):
    s = session.get(f"http://localhost:9999/v1/securities/book", params={"ticker": ticker}).json()
    for open_order in s['asks']:
        if open_order['quantity'] > 10000:
            return open_order['price'], open_order['quantity'], open_order['quantity_filled'], open_order['order_id']


def main():
    S2aa = 0
    S2taa = 0
    Windows1 = 5
    SH1 = 2
    aa = 0.5
    id00aa = 0
    tt00aa = 0

    with requests.Session() as session:
        session.headers.update(API_KEY)

        holding_position = False
        while get_tick(session) < 600 and not shutdown:
            # print("running")
            tt = get_tick(session)
            RITM_P_ALL[tt - 1] = \
            session.get("http://localhost:9999/v1/securities", params={"ticker": "RITM"}).json()[0][
                "last"]
            if tt > 2:
                RITM_R_ALL[tt - 1] = RITM_P_ALL[tt - 1] / RITM_P_ALL[tt - 2]

        # ALPHA
        aa_LP_ALL[tt - 1] = session.get("http://localhost:9999/v1/securities", params={"ticker": "ALPHA"}).json()[0][
            "last"]
        # Check if mega order exist,
        # 1.	If mega order does not exist, pass
        # 2.	if mega order does exist, retrieve price as pp00, size as size00, filled as ff00
        # 2.1 If ff00 == 0, pass
        # 	  2.2 If ff00 > 0, aa_P_ALL[tt-1] = pp00, k
        if mega_order_exists("ALPHA", "asks"):
            pp00, size00, ff00, mega_order_id = retrieve_mega_order("ALPHA")
            if ff00 == 0:
                aa_P_ALL[tt - 1] = aa_LP_ALL[tt - 1]
            if ff00 > 0:
                aa_P_ALL[tt - 1] = pp00
        else:
            aa_P_ALL[tt - 1] = aa_LP_ALL[tt - 1]
        # print("aa_P_ALL: ", aa_P_ALL[tt - 1])

        if tt > 2:
            if np.isnan(aa_P_ALL[tt - 1]):
                pp00 = aa_LP_ALL[tt - 1]
            else:
                pp00 = aa_P_ALL[tt - 1]

            if np.isnan(aa_P_ALL[tt - 2]):
                pp11 = aa_LP_ALL[tt - 2]
            else:
                pp11 = aa_P_ALL[tt - 2]

            aa_R_ALL[tt - 1] = pp00 / pp11
            # print("aa_R_ALL: ", aa_R_ALL[tt - 1])

        if tt > Windows1:

            sr00 = aa_R_ALL[tt - Windows1:tt]
            mr00 = RITM_R_ALL[tt - Windows1:tt]

            tmp1 = np.isnan(sr00)
            tmp2 = np.isnan(mr00)
            # merge tmp1 and tmp2 union set
            tmp3 = np.logical_and(~tmp1, ~tmp2)

            sr11 = sr00[tmp3]
            mr11 = mr00[tmp3]

            aa_BETA_ALL[tt - 1] = np.cov(sr11, mr11)[0][1] / np.var(sr11)

            if tt > 2 * Windows1:
                aa_BETAMA_ALL[tt - 1] = aa_BETA_ALL[tt - Windows1:tt].mean()
                if abs(aa_BETA_ALL[tt - 1] - aa_BETAMA_ALL[tt - 1]) >= 0.2:
                    aa_BETAC_ALL[tt - 1] = aa_BETA_ALL[tt - 2]
                if abs(aa_BETA_ALL[tt - 1] - aa_BETAMA_ALL[tt - 1]) < 0.2:
                    aa_BETAC_ALL[tt - 1] = aa_BETA_ALL[tt - 1]
            else:
                aa_BETAC_ALL[tt - 1] = aa_BETA_ALL[tt - 1]
        # THETA
        bb_LP_ALL[tt - 1] = session.get("http://localhost:9999/v1/securities", params={"ticker": "THETA"}).json()[0][
            "last"]
        # Check if mega order exist,
        # 1.	If mega order does not exist, pass
        # 2.	if mega order does exist, retrieve price as pp00, size as size00, filled as ff00
        # 2.1 If ff00 == 0, pass
        # 	  2.2 If ff00 > 0, bb_P_ALL[tt-1] = pp00, k
        if mega_order_exists("THETA", "asks"):
            pp00, size00, ff00, mega_order_id = retrieve_mega_order("THETA")
            if ff00 == 0:
                bb_P_ALL[tt - 1] = bb_LP_ALL[tt - 1]
            if ff00 > 0:
                bb_P_ALL[tt - 1] = pp00
        else:
            bb_P_ALL[tt - 1] = bb_LP_ALL[tt - 1]
        # print("bb_P_ALL: ", bb_P_ALL[tt - 1])

        if tt > 2:
            if np.isnan(bb_P_ALL[tt - 1]):
                pp00 = bb_LP_ALL[tt - 1]
            else:
                pp00 = bb_P_ALL[tt - 1]

            if np.isnan(bb_P_ALL[tt - 2]):
                pp11 = bb_LP_ALL[tt - 2]
            else:
                pp11 = bb_P_ALL[tt - 2]

            bb_R_ALL[tt - 1] = pp00 / pp11
            # print("bb_R_ALL: ", bb_R_ALL[tt - 1])

        if tt > Windows1:

            sr00 = bb_R_ALL[tt - Windows1:tt]
            mr00 = RITM_R_ALL[tt - Windows1:tt]

            tmp1 = np.isnan(sr00)
            tmp2 = np.isnan(mr00)
            # merge tmp1 and tmp2 union set
            tmp3 = np.logical_and(~tmp1, ~tmp2)

            sr11 = sr00[tmp3]
            mr11 = mr00[tmp3]

            bb_BETA_ALL[tt - 1] = np.cov(sr11, mr11)[0][1] / np.var(sr11)

            if tt > 2 * Windows1:
                bb_BETAMA_ALL[tt - 1] = bb_BETA_ALL[tt - Windows1:tt].mean()
                if abs(bb_BETA_ALL[tt - 1] - bb_BETAMA_ALL[tt - 1]) >= 0.2:
                    bb_BETAC_ALL[tt - 1] = bb_BETA_ALL[tt - 2]
                if abs(bb_BETA_ALL[tt - 1] - bb_BETAMA_ALL[tt - 1]) < 0.2:
                    bb_BETAC_ALL[tt - 1] = bb_BETA_ALL[tt - 1]
            else:
                bb_BETAC_ALL[tt - 1] = bb_BETA_ALL[tt - 1]
        # GAMMA
        CC_LP_ALL[tt - 1] = session.get("http://localhost:9999/v1/securities", params={"ticker": "GAMMA"}).json()[0][
            "last"]
        # Check if mega order exist,
        # 1.	If mega order does not exist, pass
        # 2.	if mega order does exist, retrieve price as pp00, size as size00, filled as ff00
        # 2.1 If ff00 == 0, pass
        # 	  2.2 If ff00 > 0, CC_P_ALL[tt-1] = pp00, k
        if mega_order_exists("GAMMA", "asks"):
            pp00, size00, ff00, mega_order_id = retrieve_mega_order("GAMMA")
            if ff00 == 0:
                CC_P_ALL[tt - 1] = CC_LP_ALL[tt - 1]
            if ff00 > 0:
                CC_P_ALL[tt - 1] = pp00
        else:
            CC_P_ALL[tt - 1] = CC_LP_ALL[tt - 1]
        # print("CC_P_ALL: ", CC_P_ALL[tt - 1])

        if tt > 2:
            if np.isnan(CC_P_ALL[tt - 1]):
                pp00 = CC_LP_ALL[tt - 1]
            else:
                pp00 = CC_P_ALL[tt - 1]

            if np.isnan(CC_P_ALL[tt - 2]):
                pp11 = CC_LP_ALL[tt - 2]
            else:
                pp11 = CC_P_ALL[tt - 2]

            CC_R_ALL[tt - 1] = pp00 / pp11
            # print("CC_R_ALL: ", CC_R_ALL[tt - 1])

        if tt > Windows1:

            sr00 = CC_R_ALL[tt - Windows1:tt]
            mr00 = RITM_R_ALL[tt - Windows1:tt]

            tmp1 = np.isnan(sr00)
            tmp2 = np.isnan(mr00)
            # merge tmp1 and tmp2 union set
            tmp3 = np.logical_and(~tmp1, ~tmp2)

            sr11 = sr00[tmp3]
            mr11 = mr00[tmp3]

            CC_BETA_ALL[tt - 1] = np.cov(sr11, mr11)[0][1] / np.var(sr11)

            if tt > 2 * Windows1:
                CC_BETAMA_ALL[tt - 1] = CC_BETA_ALL[tt - Windows1:tt].mean()
                if abs(CC_BETA_ALL[tt - 1] - CC_BETAMA_ALL[tt - 1]) >= 0.2:
                    CC_BETAC_ALL[tt - 1] = CC_BETA_ALL[tt - 2]
                if abs(CC_BETA_ALL[tt - 1] - CC_BETAMA_ALL[tt - 1]) < 0.2:
                    CC_BETAC_ALL[tt - 1] = CC_BETA_ALL[tt - 1]
            else:
                CC_BETAC_ALL[tt - 1] = CC_BETA_ALL[tt - 1]
    # ----------------- measure -----------------

            if STOCK_BETAC_ALL[tt - 1] != 0:
                if S2aa == 1 and tt - S2taa <= 2:
                    continue
                if S2aa == 1 and tt - S2taa > 2 and id00aa != 0:
                    q00 = session.get("http://localhost:9999/v1/orders/" + str(id00aa)).json()["quantity_filled"]
                    session.delete("http://localhost:9999/v1/orders/" + str(id00aa))
                    session.post("http://localhost:9999/v1/orders", params={"ticker": "ALPHA", "type": "MARKET", "quantity": Vt * aa - q00, "action": "SELL"})

                    S2aa = 0
                    id00aa = 0
                    q00 = 0

                if S2aa == 0:
                    if STOCK_BETAC_ALL[tt - 1] * (RITM_P_ALL[tt - 1] - RITM_P_ALL[tt - 3]) > 0:
                        S2aa = 1

                        if mega_order_exists("ALPHA", "asks"):
                            print("here exist mega order")
                            pp00, size00, ff00, mega_order_id = retrieve_mega_order("ALPHA")

                            # get orderbook
                            sec = session.get("http://localhost:9999/v1/securities/book", params={"ticker": "ALPHA"}).json()
                            Vt = 0
                            for order in sec['asks']:
                                if order['quantity'] <= 10000 and order["price"] < pp00 -0.05:
                                    Vt += order['quantity']

                            print("Vt: ", Vt)
                            if Vt * aa > 10000:
                                S2aa = 0
                            elif Vt > 0:
                                session.post("http://localhost:9999/v1/orders", params={"ticker": "ALPHA", "type": "MARKET", "quantity": Vt * aa, "action": "BUY"})
                                r = session.post("http://localhost:9999/v1/orders", params={"ticker": "ALPHA", "type": "LIMIT", "quantity": Vt * aa, "action": "SELL", "price": pp00 - 0.01}).json()
                                print("limit order: ", r)
                                id00aa = r["order_id"]

                                print("id00aa: ", id00aa)
                                print("tt00aa: ", tt00aa)
                                print("order info", session.get("http://localhost:9999/v1/orders/" + str(id00aa)).json())
                                tt00aa = get_tick(session)
                                S2taa = tt00aa
                            else:
                                S2aa = 0

                            if mega_order_exists("ALPHA", "asks"):
                                pp11, size11, ff11, mega_order_id11 = retrieve_mega_order("ALPHA")
                                if pp11 >= pp00:
                                    tt11 = get_tick(session)
                                    if tt11 - tt00aa >= SH1 and id00aa != 0:
                                        q00 = session.get("http://localhost:9999/v1/orders/" + str(id00aa)).json()["quantity_filled"]
                                        session.delete("http://localhost:9999/v1/orders/" + str(id00aa))
                                        session.post("http://localhost:9999/v1/orders", params={"ticker": "ALPHA", "type": "MARKET", "quantity": Vt * aa - q00, "action": "SELL"})
                                        S2aa = 0
                                        id00aa = 0
                                        q00 = 0
                                    else:
                                        continue
                                else:
                                    q00 = session.get("http://localhost:9999/v1/orders/" + str(id00aa)).json()[
                                        "quantity_filled"]
                                    session.delete("http://localhost:9999/v1/orders/" + str(id00aa))
                                    session.post("http://localhost:9999/v1/orders",
                                                 params={"ticker": "ALPHA", "type": "MARKET", "quantity": Vt * aa - q00,
                                                         "action": "SELL"})
                                    S2aa = 0
                                    id00aa = 0
                                    q00 = 0




                            else:
                                q00 = session.get("http://localhost:9999/v1/orders/" + str(id00aa)).json()["quantity_filled"]
                                session.delete("http://localhost:9999/v1/orders/" + str(id00aa))
                                session.post("http://localhost:9999/v1/orders", params={"ticker": "ALPHA", "type": "MARKET", "quantity": Vt * aa - q00, "action": "SELL"})
                                S2aa = 0
                                id00aa = 0
                                q00 = 0




                        else:
                            S2aa = 0






            sleep(0.2)


if __name__ == "__main__":
    main()

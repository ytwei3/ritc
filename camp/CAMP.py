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
import concurrent.futures
import statsmodels.api as sm


CAPM_vals = {}
expected_return = {}
real_return = {}
profit = {}

open_order_status = "NONE"
order_id = 0

front_running = True
front_running_quantity = 1000
mege_order_size = 100000000


# class that passes error message, ends the program
class ApiException(Exception):
    pass


# code that lets us shut down if CTRL C is pressed
def linear_regression(ritm, alpha):
    ritm_clean = ritm.dropna(subset=["%Rm"])
    alpha_clean = alpha.dropna(subset=["%Ri"])

    x = ritm_clean["%Rm"].values.reshape(-1, 1)
    y = alpha_clean['%Ri']

    x = sm.add_constant(x)

    model = sm.OLS(y, x).fit()

    return model


def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True


API_KEY = {"X-API-Key": "114514"}
shutdown = False
session = requests.Session()
session.headers.update(API_KEY)


def get_position(ticker):
    sec = session.get("http://localhost:9999/v1/securities", params={"ticker": ticker}).json()[0]
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


def main():
    with requests.Session() as session:
        session.headers.update(API_KEY)

        holding_position = False
        while get_tick(session) < 600 and not shutdown:
            # update the forward market price and rf rate
            get_news(session)
            tick = get_tick(session)

            ritm = pd.DataFrame(session.get(f"http://localhost:9999/v1/securities/history",
                                            params={"ticker": "RITM", "limit": 30}).json())
            alpha = pd.DataFrame(session.get(f"http://localhost:9999/v1/securities/history",
                                             params={"ticker": "ALPHA", "limit": 30}).json())
            gamma = pd.DataFrame(session.get(f"http://localhost:9999/v1/securities/history",
                                             params={"ticker": "GAMMA", "limit": 30}).json())
            theta = pd.DataFrame(session.get(f"http://localhost:9999/v1/securities/history",
                                             params={"ticker": "THETA", "limit": 30}).json())

            ritm["%Rm"] = (ritm["close"] / ritm["close"].shift(-1)) - 1
            alpha["%Ri"] = (alpha["close"] / alpha["close"].shift(-1)) - 1
            gamma["%Ri"] = (gamma["close"] / gamma["close"].shift(-1)) - 1
            theta["%Ri"] = (theta["close"] / theta["close"].shift(-1)) - 1

            beta_alpha = (alpha["%Ri"].cov(ritm["%Rm"])) / (ritm["%Rm"].var())
            beta_gamma = (gamma["%Ri"].cov(ritm["%Rm"])) / (ritm["%Rm"].var())
            beta_theta = (theta["%Ri"].cov(ritm["%Rm"])) / (ritm["%Rm"].var())

            CAPM_vals["Beta - ALPHA"] = beta_alpha
            CAPM_vals["Beta - GAMMA"] = beta_gamma
            CAPM_vals["Beta - THETA"] = beta_theta

            print("Beta : ", CAPM_vals["Beta - ALPHA"],
                  CAPM_vals["Beta - GAMMA"], CAPM_vals["Beta - THETA"])

            securities = session.get("http://localhost:9999/v1/securities").json()
            # record camp, index is the tick
            if "tick" in CAPM_vals.keys():
                if tick < CAPM_vals["tick"]:
                    CAPM_vals["%RM"] = (CAPM_vals["forward"] - securities[0]["last"]) / securities[0]["last"]

                    er_alpha = CAPM_vals["%Rf"] + CAPM_vals["Beta - ALPHA"] * (
                        CAPM_vals["%RM"] - CAPM_vals["%Rf"]
                    )
                    er_gamma = CAPM_vals["%Rf"] + CAPM_vals["Beta - GAMMA"] * (
                        CAPM_vals["%RM"] - CAPM_vals["%Rf"]
                    )
                    er_theta = CAPM_vals["%Rf"] + CAPM_vals["Beta - THETA"] * (
                        CAPM_vals["%RM"] - CAPM_vals["%Rf"]
                    )

                    expected_return["ALPHA"] = er_alpha
                    expected_return["GAMMA"] = er_gamma
                    expected_return["THETA"] = er_theta


                elif tick == CAPM_vals["tick"]:
                    close_all_positions(session)
                    continue
                else:
                    print("Waiting for the market to catch up")
                    continue
            else:
                print("No news yet.")
                continue

            real_return["ALPHA"] = er_alpha * securities[1]["last"]
            real_return["GAMMA"] = er_gamma * securities[2]["last"]
            real_return["THETA"] = er_theta * securities[3]["last"]

            profit["ALPHA"] = abs(real_return["ALPHA"]) - 0.6
            profit["GAMMA"] = abs(real_return["GAMMA"]) - 0.4
            profit["THETA"] = abs(real_return["THETA"]) - 0.2

            max_profit_ticker = max(profit, key=profit.get)
            min_profit_ticker = min(profit, key=profit.get)

            print("alpha real return: ", real_return["ALPHA"])
            print("gamma real return: ", real_return["GAMMA"])
            print("theta real return: ", real_return["THETA"])

            print("in news")

            gross_pos = abs(get_position("ALPHA")) + abs(get_position("GAMMA")) + abs(get_position("THETA"))
            net_pos = get_position("ALPHA") + get_position("GAMMA") + get_position("THETA")
            if profit[max_profit_ticker] > 0.1 and gross_pos < 250000 and abs(net_pos) < 100000:
                post_market_order(max_profit_ticker, "BUY" if real_return[max_profit_ticker] > 0 else "SELL", 10000)

            gross_pos = abs(get_position("ALPHA")) + abs(get_position("GAMMA")) + abs(get_position("THETA"))
            net_pos = get_position("ALPHA") + get_position("GAMMA") + get_position("THETA")
            if profit[min_profit_ticker] > 0.1 and gross_pos < 250000 and abs(net_pos) < 100000:
                post_market_order(min_profit_ticker, "SELL" if real_return[min_profit_ticker] > 0 else "BUY", 10000)

            sleep(0.2)


if __name__ == "__main__":
    main()

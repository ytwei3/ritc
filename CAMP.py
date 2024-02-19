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
import concurrent.futures


CAPM_vals = {}
expected_return = {}
real_return = {}

excuter = concurrent.futures.ThreadPoolExecutor(max_workers=10)


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
    return session.get("http://localhost:9999/v1/securities", params={"ticker": ticker}).json()[0]["position"]


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

def post_order(ticker, action, quantity):
    r = session.post(
        "http://localhost:9999/v1/orders",
        params={
            "ticker": ticker,
            "type": "MARKET",
            "quantity": quantity,
            "action": action,
        },
    )
    return r

def setup_portfolio(real_return):
    max_er = max(real_return, key=real_return.get)
    min_er = min(real_return, key=real_return.get)

    if max_er > 0 and min_er > 0:
        for _ in range(10):
            post_order(max_er, "BUY", "10000")
        for _ in range(7):
            post_order(min_er, "SELL", "10000")
        for _ in range(7):
            post_order(max_er, "BUY", "10000")

        post_order(max_er, "SELL", "5000")
        post_order(max_er, "BUY", "5000")

    elif max_er < 0 and min_er < 0:
        for _ in range(10):
            post_order(max_er, "SELL", "10000")
        for _ in range(7):
            post_order(min_er, "BUY", "10000")
        for _ in range(7):
            post_order(max_er, "SELL", "10000")

        post_order(max_er, "BUY", "5000")
        post_order(max_er, "SELL", "5000")

    else:


    # if three has same sign, then buy the largest one 100000, then short the smallest one 75000
    # then buy the largest one 75000


# def pop_real_bid_ask(session, ticker):
#     s = session.get(
#         f"http://localhost:9999/v1/securities/book?ticker={ticker}").json()
#     bid, ask = 0, 0
#
#     for open_order in s['bids']:
#         if open_order['quantity'] > 10000:
#             bid = open_order['price']
#             break
#
#     for open_order in s['asks']:
#         if open_order['quantity'] > 10000:
#             ask = open_order['price']
#             break
#
#     # if bid == 0 or ask == 0:
#     #     raise ApiException("No bid or ask found")
#
#     return bid, ask


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


# def beta_from_linear_regression(ritm, ticker):
#     ritm_clean = ritm.dropna(subset=["%Rm"])
#     ticker_clean = ticker.dropna(subset=["%Ri"])

#     x = ritm_clean["%Rm"].values.reshape(-1, 1)
#     y = ticker_clean['%Ri']

#     model = LinearRegression()
#     model.fit(x, y)

    # return model.coef_


def main():
    with requests.Session() as session:
        session.headers.update(API_KEY)
        ritm = pd.DataFrame(columns=["RITM", "BID", "ASK", "LAST", "%Rm"])
        alpha = pd.DataFrame(
            columns=["ALPHA", "BID", "ASK", "LAST", "%Ri", "%Rm"])
        gamma = pd.DataFrame(
            columns=["GAMMA", "BID", "ASK", "LAST", "%Ri", "%Rm"])
        theta = pd.DataFrame(
            columns=["THETA", "BID", "ASK", "LAST", "%Ri", "%Rm"])
        while get_tick(session) < 600 and not shutdown:
            t = time.time()

            # update the forward market price and rf rate
            get_news(session)

            # update RITM bid-ask dataframe
            pdt_RITM = pd.DataFrame(pop_prices(session)[0])
            ritmp = pd.DataFrame(
                {
                    "RITM": "",
                    "BID": pdt_RITM["bid"],
                    "ASK": pdt_RITM["ask"],
                    # "LAST": (pdt_RITM["bid"] + pdt_RITM["ask"]) / 2,
                    "LAST": pdt_RITM["last"],
                    "%Rm": "",
                }, index=[0]
            )
            if ritm["BID"].empty or ritmp["LAST"].iloc[0] != ritm["LAST"].iloc[0]:
                ritm = pd.concat([ritmp, ritm.loc[:]]).reset_index(drop=True)
                ritm["%Rm"] = (ritm["LAST"] / ritm["LAST"].shift(-1)) - 1
                if ritm.shape[0] >= 31:
                    ritm = ritm.iloc[:30]

            # generate expected market return paramter
            if "forward" in CAPM_vals.keys():
                CAPM_vals["%RM"] = (CAPM_vals["forward"] - ritm["LAST"].iloc[0]) / ritm[
                    "LAST"
                ].iloc[0]
            else:
                CAPM_vals["%RM"] = ""

            # update ALPHA bid-ask dataframe
            pdt_ALPHA = pd.DataFrame(pop_prices(session)[1])

            # alpha_bid, alpha_ask = pop_real_bid_ask(session, "ALPHA")
            alphap = pd.DataFrame(
                {
                    "ALPHA": "",
                    "BID": pdt_ALPHA["bid"],
                    "ASK": pdt_ALPHA["ask"],
                    "LAST": pdt_ALPHA["last"],
                    "%Ri": "",
                    "%Rm": "",
                }, index=[0]
            )
            if alpha["BID"].empty or alphap["LAST"].iloc[0] != alpha["LAST"].iloc[0]:
                alpha = pd.concat([alphap, alpha.loc[:]]
                                  ).reset_index(drop=True)
                alpha["%Ri"] = (alpha["LAST"] / alpha["LAST"].shift(-1)) - 1
                alpha["%Rm"] = (ritm["LAST"] / ritm["LAST"].shift(-1)) - 1
                if alpha.shape[0] >= 31:
                    alpha = alpha.iloc[:30]

            # update GAMMA bid-ask dataframe
            pdt_GAMMA = pd.DataFrame(pop_prices(session)[2])

            # gamma_bid, gamma_ask = pop_real_bid_ask(session, "GAMMA")
            gammap = pd.DataFrame(
                {
                    "GAMMA": "",
                    # "BID": gamma_bid,
                    # "ASK": gamma_ask,
                    "BID": pdt_GAMMA["bid"],
                    "ASK": pdt_GAMMA["ask"],
                    # "LAST": (gamma_bid + gamma_ask) / 2,
                    "LAST": pdt_GAMMA["last"],

                    "%Ri": "",
                    "%Rm": "",
                }, index=[0]
            )
            if gamma["BID"].empty or gammap["LAST"].iloc[0] != gamma["LAST"].iloc[0]:
                gamma = pd.concat([gammap, gamma.loc[:]]
                                  ).reset_index(drop=True)
                gamma["%Ri"] = (gamma["LAST"] / gamma["LAST"].shift(-1)) - 1
                gamma["%Rm"] = (ritm["LAST"] / ritm["LAST"].shift(-1)) - 1
                if gamma.shape[0] >= 31:
                    gamma = gamma.iloc[:30]

            # update THETA bid-ask dataframe
            pdt_THETA = pd.DataFrame(pop_prices(session)[3])

            # theta_bid, theta_ask = pop_real_bid_ask(session, "THETA")
            thetap = pd.DataFrame(
                {
                    "THETA": "",
                    # "BID": theta_bid,
                    # "ASK": theta_ask,
                    "BID": pdt_THETA["bid"],
                    "ASK": pdt_THETA["ask"],
                    # "LAST": (theta_bid + theta_ask) / 2,
                    "LAST": pdt_THETA["last"],
                    "%Ri": "",
                    "%Rm": "",
                }, index=[0]
            )
            if theta["BID"].empty or thetap["LAST"].iloc[0] != theta["LAST"].iloc[0]:
                theta = pd.concat([thetap, theta.loc[:]]
                                  ).reset_index(drop=True)
                theta["%Ri"] = (theta["LAST"] / theta["LAST"].shift(-1)) - 1
                theta["%Rm"] = (ritm["LAST"] / ritm["LAST"].shift(-1)) - 1
                if theta.shape[0] >= 31:
                    theta = theta.iloc[:30]

            beta_alpha = (alpha["%Ri"].cov(ritm["%Rm"])) / (ritm["%Rm"].var())
            beta_gamma = (gamma["%Ri"].cov(ritm["%Rm"])) / (ritm["%Rm"].var())
            beta_theta = (theta["%Ri"].cov(ritm["%Rm"])) / (ritm["%Rm"].var())

            CAPM_vals["Beta - ALPHA"] = beta_alpha
            CAPM_vals["Beta - GAMMA"] = beta_gamma
            CAPM_vals["Beta - THETA"] = beta_theta

            print(get_tick(session))
            print("Beta : ", CAPM_vals["Beta - ALPHA"],
                  CAPM_vals["Beta - GAMMA"], CAPM_vals["Beta - THETA"])

            # if len(alpha) > 10:
            #     print("LG Beta : ", beta_from_linear_regression(ritm, alpha),  beta_from_linear_regression(
            #         ritm, gamma),  beta_from_linear_regression(ritm, theta))

            # record camp, index is the tick
            if CAPM_vals["%RM"] != "":
                er_alpha = CAPM_vals["%Rf"] + CAPM_vals["Beta - ALPHA"] * (
                    CAPM_vals["%RM"] - CAPM_vals["%Rf"]
                )
                er_gamma = CAPM_vals["%Rf"] + CAPM_vals["Beta - GAMMA"] * (
                    CAPM_vals["%RM"] - CAPM_vals["%Rf"]
                )
                er_theta = CAPM_vals["%Rf"] + CAPM_vals["Beta - THETA"] * (
                    CAPM_vals["%RM"] - CAPM_vals["%Rf"]
                )
            else:
                er_alpha = "Wait for market forward price"
                er_gamma = "Wait for market forward price"
                er_theta = "Wait for market forward price"

            expected_return["ALPHA"] = er_alpha
            expected_return["GAMMA"] = er_gamma
            expected_return["THETA"] = er_theta

            # if er_alpha is not string
            if type(er_alpha) != str:
                real_return["ALPHA"] = er_alpha * alpha.at[0, "LAST"]
                real_return["GAMMA"] = er_gamma * gamma.at[0, "LAST"]
                real_return["THETA"] = er_theta * theta.at[0, "LAST"]

                if real_return["ALPHA"] > 0:
                    real_return["ALPHA action"] = "BUY"
                elif real_return["ALPHA"] < 0:
                    real_return["ALPHA action"] = "SELL"

                real_return["Adjust ALPHA"] = abs(real_return["ALPHA"]) - 0.6

                if real_return["GAMMA"] > 0:
                    real_return["GAMMA action"] = "BUY"
                elif real_return["GAMMA"] < 0:
                    real_return["GAMMA action"] = "SELL"

                real_return["Adjust GAMMA"] = abs(real_return["GAMMA"]) - 0.4

                if real_return["THETA"] > 0:
                    real_return["THETA action"] = "BUY"
                elif real_return["THETA"] < 0:
                    real_return["THETA action"] = "SELL"

                real_return["Adjust THETA"] = abs(real_return["THETA"]) - 0.2

                print("alpha real return: ", real_return["ALPHA"])
                print("gamma real return: ", real_return["GAMMA"])
                print("theta real return: ", real_return["THETA"])

                print("alpha adjusted return: ", real_return["Adjust ALPHA"])
                print("gamma adjusted return: ", real_return["Adjust GAMMA"])
                print("theta adjusted return: ", real_return["Adjust THETA"])

            tick = get_tick(session)
            news = session.get("http://localhost:9999/v1/news").json()

            # print("ritm bid ask spread is:", ritm["ASK"].iloc[0] - ritm["BID"].iloc[0])
            # print("alpha bid ask spread is:", alpha["ASK"].iloc[0] - alpha["BID"].iloc[0])
            # print("gamma bid ask spread is:", gamma["ASK"].iloc[0] - gamma["BID"].iloc[0])
            # print("theta bid ask spread is:", theta["ASK"].iloc[0] - theta["BID"].iloc[0])

            if len(news) > 1:
                if "tick" in CAPM_vals.keys() and tick < CAPM_vals["tick"]:
                    print("in news")
                    buy_or_sell(session, real_return)
                    # if ((pdt_RITM["bid"] + pdt_RITM["ask"]) / 2 > CAPM_vals["forward"]).bool():
                    #     buy_or_sell(session, expected_return, "SELL")
                    # else:
                    #     buy_or_sell(session, expected_return, "BUY")
                if "tick" in CAPM_vals.keys() and tick == CAPM_vals["tick"]:
                    print("Tick is equal to the forward market prediction: ", CAPM_vals["tick"])
                    print("forward market prediction: ", CAPM_vals["forward"])
                    print("last price: ", pdt_RITM["last"])
                else:
                    # print(
                    #     "Tick is less than the forward market prediction, waiting for the market to catch up")
                    close_all_positions(session)

            # print statement (print, expected_return function, any of the tickers, or CAPM_vals dictionary)
            # print(expected_return)

            # slow down for debuf purposes
            sleep(0.5)


if __name__ == "__main__":
    main()

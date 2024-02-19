import requests
from time import sleep
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QRadioButton,
)

API_KEY = {"X-API-Key": "114514"}
s = requests.Session()
s.headers.update(API_KEY)


def post_order(s, type, quantity, action, ticker):
    r = s.post("http://localhost:9999/v1/orders?type="
            + type + "&quantity=" + str(quantity) + "&action=" + action + "&ticker=" + ticker)

    if r.status_code == 429:
        wait = r.json()["wait"]
        sleep(wait)

        post_order(s, type, quantity, action, ticker)
    elif r.status_code != 200:
        print(r.json())


def straddle(s, price, action, period):
    for _ in range(5):
        post_order(s, "MARKET", 100, action, "RTM" + str(period) + 'C' + str(price))
        post_order(s, "MARKET", 100, action, "RTM" + str(period) + 'P' + str(price))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buy/Sell Straddle")
        self.setGeometry(400, 400, 400, 300)

        self.layout = QVBoxLayout()
        self.central_widget = QWidget(self)
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.strike_price_label = QLabel("Strike Price:", self)
        self.layout.addWidget(self.strike_price_label)

        self.strike_price_entry = QLineEdit(self)
        self.layout.addWidget(self.strike_price_entry)

        self.period_label = QLabel("Select Period:", self)
        self.layout.addWidget(self.period_label)

        self.period1_radio = QRadioButton("Period 1", self)
        self.period1_radio.setChecked(True)
        self.layout.addWidget(self.period1_radio)

        self.period2_radio = QRadioButton("Period 2", self)
        self.layout.addWidget(self.period2_radio)

        self.buy_button = QPushButton("Buy Straddle", self)
        self.buy_button.clicked.connect(self.buy_straddle)
        self.layout.addWidget(self.buy_button)

        self.sell_button = QPushButton("Sell Straddle", self)
        self.sell_button.clicked.connect(self.sell_straddle)
        self.layout.addWidget(self.sell_button)

    def buy_straddle(self):
        strike_price = self.strike_price_entry.text()
        if self.period1_radio.isChecked():
            period = 1
        else:
            period = 2

        straddle(s, strike_price, "BUY", period)
        print("Successfully bought straddle at strike price:", strike_price, "for period", period)

    def sell_straddle(self):
        strike_price = self.strike_price_entry.text()
        if self.period1_radio.isChecked():
            period = 1
        else:
            period = 2

        straddle(s, strike_price, "SELL", period)
        print("Successfully sold straddle at strike price:", strike_price, "for period", period)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
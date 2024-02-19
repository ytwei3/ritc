import requests

import pandas as pd
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

API_KEY = {"X-API-Key": "114514"}
BASE_URL = "http://localhost:9999/v1"

s = requests.Session()
s.headers.update(API_KEY)

sec = pd.DataFrame(s.get(BASE_URL + '/securities').json())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buy/Sell Entry")
        self.setGeometry(400, 400, 400, 300)

        self.layout = QVBoxLayout()
        self.central_widget = QWidget(self)
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.line_widgets = []  # List to store line widget instances

        self.add_line_button = QPushButton("Add entry", self)
        self.add_line_button.clicked.connect(self.add_line)
        self.layout.addWidget(self.add_line_button)

        self.add_line()  # Add initial line

    def add_line(self):
        line_widget = LineWidget(self)
        line_widget.delete_button.clicked.connect(
            lambda checked, widget=line_widget: self.delete_line(widget)
        )  # Connect delete button to delete_line method
        self.line_widgets.append(line_widget)
        self.layout.addWidget(line_widget)
        self.adjust_window_size()

    def delete_line(self, line_widget):
        line_widget.setParent(None)
        line_widget.delete_button.clicked.disconnect()  # Disconnect the signal to avoid multiple connections
        self.line_widgets.remove(line_widget)

        self.adjust_window_size()

    def adjust_window_size(self):
        content_width = self.layout.sizeHint().width()
        content_height = self.layout.sizeHint().height()

        # Set window size, add some extra padding
        self.setFixedSize(content_width + 20, content_height + 20)


class LineWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.url = "http://localhost:9999/v1"

        self.stock_combobox = QComboBox(self)
        self.stock_combobox.addItems(["USD", "HAWK", "DOVE", "RIT_C", "RIT_U"])

        self.buy_sell_button = QPushButton("BUY", self)
        self.buy_sell_button.clicked.connect(self.toggle_buy_sell)

        self.close_ticker_button = QPushButton("Close Ticker", self)
        self.close_ticker_button.clicked.connect(self.toggle_close_ticker)

        self.best_limit_button = QPushButton("Best Limit", self)
        self.best_limit_button.clicked.connect(self.toggle_best_limit)

        self.start_mm_button = QPushButton("Start MM", self)
        self.start_mm_button.clicked.connect(self.start_mm)

        self.stop_mm_button = QPushButton("Stop MM", self)
        self.stop_mm_button.clicked.connect(self.stop_mm)

        self.kill_limit_button = QPushButton("Kill Limit", self)
        self.kill_limit_button.clicked.connect(self.toggle_kill_limit)

        self.quantity_input = QLineEdit(self)
        self.quantity_input.setText("10000")
        self.quantity_input.setFixedWidth(80)
        self.quantity_input.setFixedHeight(20)

        self.order_type_button = QPushButton("MKT", self)
        self.order_type_button.clicked.connect(self.toggle_order_type)

        self.price_input = QLineEdit(self)
        self.price_input.setEnabled(False)
        self.price_input.setFixedWidth(80)
        self.price_input.setFixedHeight(20)

        self.submit_button = QPushButton(self.get_submit_button_text(), self)
        self.submit_button.clicked.connect(self.submit_order)
        self.set_submit_button_style()

        self.delete_button = QPushButton("Delete", self)  # Delete button

        # Corrected attribute name
        self.buy_sell_state = "BUY"  # Initial state is BUY
        self.order_type_state = "MKT"  # Initial state is Market Order

        layout = QHBoxLayout()

        ticker_label = QLabel("Ticker:")
        layout.addWidget(ticker_label)
        layout.addWidget(self.stock_combobox)

        layout.addWidget(self.buy_sell_button)

        quantity_label = QLabel("Quantity:")
        layout.addWidget(quantity_label)
        layout.addWidget(self.quantity_input)

        layout.addWidget(self.order_type_button)

        price_label = QLabel("Price:")
        layout.addWidget(price_label)
        layout.addWidget(self.price_input)

        layout.addWidget(self.submit_button)
        layout.addWidget(self.best_limit_button)
        layout.addWidget(self.close_ticker_button)

        layout.addWidget(self.start_mm_button)
        layout.addWidget(self.stop_mm_button)
        layout.addWidget(self.kill_limit_button)

        layout.addWidget(self.delete_button)  # Add delete button to layout

        self.setLayout(layout)

    def toggle_kill_limit(self):
        stock = self.stock_combobox.currentText()
        df = pd.DataFrame(s.get(self.url + "/orders").json())
        df = df[df["ticker"] == stock]

        for i in df['order_id']:
            s.delete(self.url + "/orders/" + str(i))

    def start_mm(self):
        stock = self.stock_combobox.currentText()
        response = s.post(self.url + "/mm/start", params={"ticker": stock})
        print("Response: ", response.json() if response else "No response")

    def stop_mm(self):
        stock = self.stock_combobox.currentText()
        response = s.post(self.url + "/mm/stop", params={"ticker": stock})
        print("Response: ", response.json() if response else "No response")

    def toggle_best_limit(self):
        stock = self.stock_combobox.currentText()
        action = self.buy_sell_state
        quantity = self.quantity_input.text()

        response = s.get(self.url + "/securities?ticker=" + stock).json()[0]
        if action == "BUY":
            resp = s.post(self.url + "/orders",
                          params={"ticker": stock, "type": "LIMIT", "action": "BUY", "quantity": quantity,
                                  "price": response["ask"]})
        elif action == "SELL":
            resp = s.post(self.url + "/orders",
                          params={"ticker": stock, "type": "LIMIT", "action": "SELL", "quantity": quantity,
                                  "price": response["bid"]})
        print("Response: ", resp.json() if resp else "No response")

    def toggle_close_ticker(self):
        stock = self.stock_combobox.currentText()
        if stock == "USD":
            quantity = 1000000
        else:
            quantity = 10000

        with requests.Session() as s:
            s.headers.update(API_KEY)
            pos = s.get(self.url + "/securities?ticker=" + stock).json()[0]["position"]

            while pos > 0:
                response = s.post(
                    self.url + "/orders",
                    params={
                        "ticker": stock,
                        "type": "MARKET",
                        "action": "SELL",
                        "quantity": min(quantity, pos),
                    },
                )
                print("Closing position for", stock, ":", response.json())
                pos -= min(quantity, pos)
            while pos < 0:
                response = s.post(
                    self.url + "/orders",
                    params={
                        "ticker": stock,
                        "type": "MARKET",
                        "action": "BUY",
                        "quantity": min(quantity, -pos),
                    },
                )
                print("Closing position for", stock, ":", response.json())
                pos += min(quantity, -pos)

    def toggle_buy_sell(self):
        if self.buy_sell_state == "BUY":
            self.buy_sell_state = "SELL"
            self.buy_sell_button.setText("SELL")
        else:
            self.buy_sell_state = "BUY"
            self.buy_sell_button.setText("BUY")
        self.submit_button.setText(self.get_submit_button_text())
        self.set_submit_button_style()

    def toggle_order_type(self):
        if self.order_type_state == "MKT":
            self.order_type_state = "LMT"
            self.order_type_button.setText("LMT")
            self.price_input.setEnabled(True)
        else:
            self.order_type_state = "MKT"
            self.order_type_button.setText("MKT")
            self.price_input.setEnabled(False)

    def get_submit_button_text(self):
        if self.buy_sell_button.text() == "BUY":
            return "Submit BUY"
        else:
            return "Submit SELL"

    def set_submit_button_style(self):
        if self.buy_sell_button.text() == "BUY":
            self.submit_button.setStyleSheet("background-color: rgb(0,255,127)")
        else:
            self.submit_button.setStyleSheet("background-color: rgb(240,128,128)")

    def submit_order(self):
        stock = self.stock_combobox.currentText()
        quantity = self.quantity_input.text()
        order_type = self.order_type_state
        price = self.price_input.text() if order_type == "LMT" else "MKT"
        response = None

        try:
            with requests.Session() as s:
                s.headers.update(API_KEY)
                response = s.post(
                    self.url + "/orders",
                    params={
                        "ticker": stock,
                        "type": "MARKET" if order_type == "MKT" else "LIMIT",
                        "action": self.buy_sell_state,
                        "quantity": quantity,
                        "price": price,
                    },
                )
        except Exception as e:
            print(e)

        print("-" * 20, "Submit Order" + "-" * 20)
        print("Stock:", stock)
        print("Quantity:", quantity)
        print("Order Type:", order_type)
        print("Price:", price)
        print("Response: ", response.json() if response else "No response")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()

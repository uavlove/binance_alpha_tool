import sys
import os
import json
import time
import threading
import requests
from datetime import datetime, timezone
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer

CONFIG_FILE = "api_key.json"

class BscScanApp(QWidget):
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.api_key = self.config.get("api_key", "")
        self.address = self.config.get("address", "")
        self.address_visible = self.config.get("address_visible", True)
        self.use_local_time = self.config.get("use_local_time", False)
        self.running = False
        self.block_height = '0'
        self.bnb_usd = 0.0

        self.init_ui()
        self.get_block_height()
        self.get_bnb_price()

    def init_ui(self):
        self.setWindowTitle("BSCScan Interface")

        self.web_edit = QLineEdit('https://api.bscscan.com/api')
        self.api_key_edit = QLineEdit('*' * len(self.api_key))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.editingFinished.connect(self.save_api_key)

        self.address_edit = QLineEdit(self.address)
        self.address_checkbox = QCheckBox("显示地址")
        self.address_checkbox.setChecked(self.address_visible)
        self.address_checkbox.stateChanged.connect(self.toggle_address_visibility)
        self.toggle_address_visibility()

        self.date_edit = QLineEdit(datetime.utcnow().strftime('%Y%m%d'))
        self.coin_edit = QLineEdit()

        self.local_time_checkbox = QCheckBox("使用本地时区")
        self.local_time_checkbox.setChecked(self.use_local_time)
        self.local_time_checkbox.stateChanged.connect(self.toggle_local_time)

        form_layout = QVBoxLayout()
        for label, edit in zip(["Web", "API Key", "Address", "Date", "Coin"],
                                [self.web_edit, self.api_key_edit, self.address_edit, self.date_edit, self.coin_edit]):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(edit)
            if label == "Address":
                row.addWidget(self.address_checkbox)
            form_layout.addLayout(row)
        form_layout.addWidget(self.local_time_checkbox)

        self.block_label = QLabel("BNB block height: ")
        self.bnb_price_label = QLabel("BNB USD: ")
        self.stats_label = QLabel("Send: 0 | Receive: 0 | Score: 0 | Profit: 0 | Next Level: 0 | Need: 0")
        self.bnb_gas_label = QLabel("BNB Gas: 0")
        self.total_profit_label = QLabel("Total Profit: 0")

        self.auto_btn = QPushButton("Auto Start")
        self.auto_btn.clicked.connect(self.toggle_auto)

        self.manual_btn = QPushButton("Manual")
        self.manual_btn.clicked.connect(self.fetch_data)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_table)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.auto_btn)
        btn_layout.addWidget(self.manual_btn)
        btn_layout.addWidget(self.clear_btn)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Token Symbol", "Value", "BNB Gas", "Transaction Index"])

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.block_label)
        main_layout.addWidget(self.bnb_price_label)
        main_layout.addWidget(self.stats_label)
        main_layout.addWidget(self.bnb_gas_label)
        main_layout.addWidget(self.total_profit_label)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.table)

        self.setLayout(main_layout)
        self.resize(900, 600)

    def toggle_local_time(self):
        self.use_local_time = self.local_time_checkbox.isChecked()
        self.config["use_local_time"] = self.use_local_time
        self.save_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_api_key(self):
        raw = self.api_key_edit.text()
        if '*' not in raw:
            self.api_key = raw
            self.config["api_key"] = self.api_key
            self.api_key_edit.setText('*' * len(self.api_key))
        self.save_config()

    def save_config(self):
        self.config["address"] = self.address_edit.text()
        self.config["address_visible"] = self.address_checkbox.isChecked()
        self.config["use_local_time"] = self.use_local_time
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def toggle_address_visibility(self):
        visible = self.address_checkbox.isChecked()
        self.address_edit.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)

    def get_timestamp(self):
        try:
            dt = datetime.strptime(self.date_edit.text(), '%Y%m%d')
            return int(dt.timestamp())
        except:
            QMessageBox.warning(self, "Error", "Invalid date format (YYYYMMDD).")
            return 0

    def get_block_height(self):
        ts = self.get_timestamp()
        if ts == 0 or not self.api_key:
            self.block_label.setText("BNB block height: Error (Invalid API key or time)")
            return
        url = f"{self.web_edit.text()}?module=block&action=getblocknobytime&timestamp={ts}&closest=before&apikey={self.api_key}"
        try:
            response = requests.get(url).json()
            if response.get("status") == "1" and "result" in response:
                self.block_height = response["result"]
                self.block_label.setText(f"BNB block height: {self.block_height}")
            else:
                self.block_label.setText("BNB block height: Error (API failure)")
        except:
            self.block_label.setText("BNB block height: Error")

    def get_bnb_price(self):
        if not self.api_key:
            self.bnb_price_label.setText("BNB USD: Error (Invalid API key)")
            return
        url = f"{self.web_edit.text()}?module=stats&action=bnbprice&apikey={self.api_key}"
        try:
            response = requests.get(url).json()
            if response.get("status") == "1" and "result" in response:
                usd = response['result']['ethusd']
                self.bnb_usd = float(usd)
                self.bnb_price_label.setText(f"BNB USD: {usd}")
            else:
                self.bnb_price_label.setText("BNB USD: Error (API failure)")
        except:
            self.bnb_price_label.setText("BNB USD: Error")

    def fetch_data(self):
        self.get_block_height()
        self.get_bnb_price()
        addr = self.address_edit.text()
        if not addr:
            QMessageBox.warning(self, "Input Error", "Address is required.")
            return

        if not self.api_key:
            QMessageBox.warning(self, "Input Error", "API Key is required.")
            return

        url = f"{self.web_edit.text()}?module=account&action=tokentx&address={addr}&page=1&offset=1000&startblock={self.block_height}&endblock=999999999&sort=asc&apikey={self.api_key}"
        try:
            response = requests.get(url).json()
            if response.get("status") != "1" or "result" not in response:
                raise ValueError("Invalid response from BscScan API")
            self.populate_table(response.get('result', []))
        except Exception as e:
            QMessageBox.critical(self, "Request Error", str(e))

    def safe_item(self, value):
        return QTableWidgetItem(str(value) if value is not None else "")

    def populate_table(self, results):
        self.clear_table()
        coins = [c.strip().upper() for c in self.coin_edit.text().split(',') if c.strip()]
        send, receive, bnb_gas_total = 0, 0, 0
        addr = self.address_edit.text().lower()
        for tx in results:
            if 'functionName' in tx and tx['functionName'].startswith('airdrop'):
                continue
            if coins and tx['tokenSymbol'].upper() not in coins:
                continue

            ts = int(tx['timeStamp'])
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            dt_str = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S') if self.use_local_time else dt.strftime('%Y-%m-%d %H:%M:%S')

            try:
                raw_value = int(tx['value'])
                decimals = int(tx['tokenDecimal'])
                value = raw_value / (10 ** decimals)
                is_send = tx['from'].lower() == addr
                is_receive = tx['to'].lower() == addr
                if is_send:
                    value = -value
            except:
                value = 0

            try:
                gas_used = int(tx.get('gasUsed', '0'))
                gas_price = int(tx.get('gasPrice', '0'))
                gas = -(gas_used * gas_price / (10 ** decimals))
                bnb_gas_total += gas * self.bnb_usd
            except:
                gas = 0

            if tx['tokenSymbol'].upper() == 'BSC-USD':
                if is_send:
                    send += value
                elif is_receive:
                    receive += value

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, self.safe_item(dt_str))
            self.table.setItem(row, 1, self.safe_item(tx.get('tokenSymbol')))
            self.table.setItem(row, 2, self.safe_item(f"{value:.12f}"))
            self.table.setItem(row, 3, self.safe_item(f"{gas:.12f}"))
            self.table.setItem(row, 4, self.safe_item(tx.get('transactionIndex')))

        profit = send + receive
        score = 0
        temp = abs(send)
        while temp >= 1:
            score += 1
            temp /= 2
        next_level = 2 ** (score + 1)
        need = next_level - abs(send)
        total_profit = profit + bnb_gas_total

        self.stats_label.setText(f"Send: {send:.2f} | Receive: {receive:.2f} | Score: {score} | Profit: {profit:.2f} | Next Level: {next_level:.2f} | Need: {need:.2f}")
        self.bnb_gas_label.setText(f"BNB Gas: {bnb_gas_total:.2f}")
        self.total_profit_label.setText(f"Total Profit: {total_profit:.2f}")

    def clear_table(self):
        self.table.setRowCount(0)

    def toggle_auto(self):
        if self.running:
            self.running = False
            self.auto_btn.setText("Auto Start")
        else:
            self.running = True
            self.auto_btn.setText("Stop")
            threading.Thread(target=self.auto_loop, daemon=True).start()

    def auto_loop(self):
        while self.running:
            self.fetch_data()
            for _ in range(10):
                if not self.running:
                    break
                time.sleep(1)

    def closeEvent(self, event):
        self.running = False
        time.sleep(0.2)
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BscScanApp()
    window.show()
    sys.exit(app.exec_())

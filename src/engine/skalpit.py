import logging
import time
import numpy as np
import pandas as pd
import sys
from datetime import datetime

from src.utils.indicators import calc_indi
from src.utils.utils import get_logger, start_of_min15, start_of_hour, start_of_hour4, start_of_day, date_to_seconds
from src.account.live_account import LiveAccount
from src.engine.engine import Engine
from src.engine.bybit_ws import BybitWs
from src.engine.bybit_rest import BybitRest

logger = get_logger(logging.getLogger(__name__), 'logs/skalpit.log', logging.DEBUG)

class Skalpit(Engine):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('testmode'):
            super().__init__(strategy =  kwargs.get('strategy'), symbol = kwargs.get('symbol'))

            api_key = kwargs.get('api_key')
            secret = kwargs.get('secret')
            
            try:
                self.restclient = BybitRest(api_key = api_key, secret = secret, symbol = self.symbol)
                self.account = self._create_account()
                self.ws_ready = False
                self.bybitws = BybitWs(api_key = api_key, secret = secret, symbol = self.symbol, callback = self.callback, restclient = self.restclient)            
            except Exception as err:
                import traceback
                traceback.print_exc()

            logger.info("done")

    def callback(self, **kwargs):
        topic = kwargs.get("topic")
        data = kwargs.get("data")
        try:
            if "auth" in topic:
                self.ws_ready = data.get('success')
            if "kline" in topic:
                self._parse_kline(topic, data)
            if "position" in topic:
                self._parse_position(topic, data)
            if "execution" in topic:
                self._parse_execution(topic, data)
            if "order" in topic:
                self._parse_order(topic, data)
        except Exception as err:
            import traceback
            traceback.print_exc()
            logger.error(f"callback: {data}")
            sys.exit()

    def _parse_order(self, topic, data):
        self.account.new_order(data)

    def _parse_execution(self, topic, data):
        self.account.order_executed(data)

    def _parse_position(self, topic, data):
        size = data.get('size')
        if size == 0 and not self.account.trade == None and int(time.time()) - self.account.lasttradeopened > 5:
            logger.debug("_parse_position: position is 0, cancelling all orders")
            self.restclient.cancel_active_orders_all()
        elif size == 0 and not self.account.trade == None and int(time.time()) - self.account.lasttradeopened <= 5:
            logger.debug("_parse_position: position is 0 too soon, ignoring...")
        self.account.position_update(data)

    def _parse_kline(self, topic, data):
        logger.debug(f"_parse_kline: {topic}")
        interval = topic.split('.')[1]
        column_data = [i[1:] for i in data]
        index = [int(i[0]) for i in data]
        self.klines[interval] = pd.DataFrame(column_data, index = index, columns=['Open', 'High', 'Low', 'Close', 'Volume', 'TurnOver'])

        if interval == '1m' and self.ws_ready:
            table = self._get_indis()
            self.process_kline(table.iloc[-1], self.signals)
            
    def process_kline(self, row, signals):
        logger.debug(f"process_kline")
        logger.debug(row)
        if self._check_risk_management():
            if self._check_time(row):
                signal = self._check_signal(row, signals)
                logger.debug(f"process_kline: signal = {signal}")

                if signal == "long":
                    sl = round(row['Open'] - self.strategy.get('sl-atr') * row['atr'], 2)
                    tp = round(row['Open'] + self.strategy.get('tp-atr') * row['atr'], 2)
                    size = self.account.open(self.risk, row['Open'], sl)
                    logger.info(f"LONG {size} @ {row['Open']} - SL {sl} - TP {tp}")
                    self.restclient.place_active_order(symbol = "BTCUSD", side = "Buy", order_type = "Market", qty = size, stop_loss = sl)
                    time.sleep(1)
                    self.restclient.place_active_order(symbol = "BTCUSD", side = "Sell", order_type = "Limit", qty = size, price = tp, reduce_only = "True", time_in_force = "GoodTillCancel")

                if signal == "short":
                    sl = round(row['Open'] + self.strategy.get('sl-atr') * row['atr'], 2)
                    tp = round(row['Open'] - self.strategy.get('tp-atr') * row['atr'], 2)
                    size = self.account.open(self.risk, row['Open'], sl)
                    logger.info(f"SHORT {size} @ {row['Open']} - SL {sl} - TP {tp}")
                    self.restclient.place_active_order(symbol = "BTCUSD", side = "Sell", order_type = "Market", qty = size, stop_loss = sl)
                    time.sleep(1)
                    self.restclient.place_active_order(symbol = "BTCUSD", side = "Buy", order_type = "Limit", qty = size, price = tp, reduce_only = "True", time_in_force = "GoodTillCancel")

            self.account.update(row.name, row)

    def _create_account(self):
        coin = self.symbol[:3]
        response = self.restclient.get_balance(coin)
        balance = response.get("result", {}).get(coin, {}).get("available_balance",{})
        logger.info(f"_create_account: balance = {balance}")
        return LiveAccount(startbalance=balance)

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv()
    symbol = os.getenv("SYMBOL")
    api_key = os.getenv("BYBIT_PUBLIC_TRADE")
    secret = os.getenv("BYBIT_SECRET_TRADE")

    from src.engine.strategy import strategy
    sk = Skalpit(api_key = api_key, secret = secret, symbol = symbol, strategy = strategy)

    mkt = 58000
    sl = 55000
    tp = 75000
    sk.account.open('long', mkt, stop = sl, tp = tp, risk = 4, is_maker = True, timestamp = int(time.time()))
    sk.bybitws.place_active_order(symbol = "BTCUSD", side = "Buy", order_type = "Market", qty = sk.account.trade['size'], stop_loss = sl)
    sk.bybitws.place_active_order(symbol = "BTCUSD", side = "Sell", order_type = "Limit", qty = sk.account.trade['size'], price = tp, reduce_only = "True", time_in_force = "GoodTillCancel")

    time.sleep(2000)

    oid = sk.account.get_limit_order_id()
    print(oid)

    # bb.cancel_active_order_v2(order_id=oid)
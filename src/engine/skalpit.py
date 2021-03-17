import logging
import time
import numpy as np
import pandas as pd
import pandas_ta as ta
from datetime import datetime

from src.utils.indicators import calc_indi
from src.utils.utils import get_logger, start_of_min15, start_of_hour, start_of_hour4, start_of_day, date_to_seconds
from src.account.live_account import LiveAccount
from src.engine.engine import Engine

logger = get_logger(logging.getLogger(__name__), 'logs/skalpit.log', logging.DEBUG)

class Skalpit(Engine):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('testmode'):
            api_key = kwargs.get('api_key')
            secret = kwargs.get('secret')
            strategy = kwargs.get('strategy')
            symbol = kwargs.get('symbol')
            super().__init__(api_key = api_key, secret = secret, ws = True, symbol = symbol, strategy = strategy, callback = self.callback)


            self.account = self._create_account()

            # time.sleep(5)
            # mkt = 60000
            # sl = 55000
            # tp = 75000
            # self.account.open('long', mkt, stop = sl, tp = tp, risk = self.risk, is_maker = False, timestamp = int(time.time()))
            # self.bybit.place_active_order(symbol = "BTCUSD", side = "Buy", order_type = "Market", qty = self.account.trade['size'], stop_loss = sl)
            # self.bybit.place_active_order(symbol = "BTCUSD", side = "Sell", order_type = "Limit", qty = self.account.trade['size'], price = tp, reduce_only = "True", time_in_force = "GoodTillCancel")

            # while True:
                # time.sleep(2000)
            # import threading
            # bb = threading.Thread(target=self.bybit.ws.run_forever, daemon=True)

            # bb.start()
            # bbclose = threading.Timer(20, self.bybit.ws.close).start()
            # bb.join()

            # print("done1")

            # bb.start()
            # bbclose = threading.Timer(20, self.bybit.ws.close).start()
            # bb.join()

            # print("done2")

            #If I got here, the websocket died, so we have to reset
            
            logger.info("done")
    
    def reconnect(self, ws):
        while ws.run_forever():
            pass

    def callback(self, **kwargs):
        topic = kwargs.get("topic")
        data = kwargs.get("data")

        if "kline" in topic:
            self._parse_kline(topic, data)
        if "position" in topic:
            self._parse_position(topic, data)
        if "execution" in topic:
            self._parse_execution(topic, data)
        if "order" in topic:
            self._parse_order(topic, data)

    def _parse_order(self, topic, data):
        self.account.new_order(data)

    def _parse_execution(self, topic, data):
        self.account.order_executed(data)

    def _parse_position(self, topic, data):
        size = data.get('size')
        if size == 0:
            logger.debug("_parse_position: position is 0, cancelling all orders")
            self.bybit.cancel_active_orders_all()
        self.account.position_update(data)

    def _parse_kline(self, topic, data):
        logger.debug(f"_parse_kline: {topic}")
        interval = topic.split('.')[1]
        column_data = [i[1:] for i in data]
        index = [int(i[0]) for i in data]
        # convert to data frame
        self.klines[interval] = pd.DataFrame(column_data, index = index, columns=['Open', 'High', 'Low', 'Close', 'Volume', 'TurnOver'])

        if not hasattr(self, 'bybit'):
            return

        if not self.klines['1m'].empty and not self.klines['1h'].empty and not self.klines['15m'].empty:
            table = self._get_indis()
            # self.process_kline(table.iloc[-1], self.signals)
            
    def process_kline(self, row, signals):
        try:
            if self._check_risk_management():
                if self._check_time(row):
                    signal = self._check_signal(row, signals)

                    if signal == "long":
                        sl = round(row['Open'] - self.strategy.get('sl-atr') * row['atr'], 2)
                        tp = round(row['Open'] + self.strategy.get('tp-atr') * row['atr'], 2)
                        logger.info(f"LONG {row['Open']} SL {sl} TP {tp}")
                        logger.info(row)
                        self.account.open('long', row['Open'], stop = sl, tp = tp, risk = self.risk, is_maker = False, timestamp = row.name)
                        self.bybit.place_active_order(symbol = "BTCUSD", side = "Buy", order_type = "Market", qty = self.account.trade['size'], stop_loss = sl)
                        self.bybit.place_active_order(symbol = "BTCUSD", side = "Sell", order_type = "Limit", qty = self.account.trade['size'], price = tp, reduce_only = "True", time_in_force = "GoodTillCancel")

                    if signal == "short":
                        sl = round(row['Open'] + self.strategy.get('sl-atr') * row['atr'], 2)
                        tp = round(row['Open'] - self.strategy.get('tp-atr') * row['atr'], 2)
                        logger.info(f"SHORT {row['Open']} SL {sl} TP {tp}")
                        logger.info(row)
                        self.account.open('short', row['Open'], stop = sl, tp = tp, risk = self.risk, is_maker = False, timestamp = row.name)
                        self.bybit.place_active_order(symbol = "BTCUSD", side = "Sell", order_type = "Market", qty = self.account.trade['size'], stop_loss = sl)
                        self.bybit.place_active_order(symbol = "BTCUSD", side = "Buy", order_type = "Limit", qty = self.account.trade['size'], price = tp, reduce_only = "True", time_in_force = "GoodTillCancel")

            self.account.update(row.name, row)

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"error at {row.name}: {e} ")

    def _create_account(self):
        coin = self.symbol[:3]
        response = self.bybit.get_balance(coin)
        balance = response.get("result", {}).get(coin, {}).get("available_balance",{})
        return LiveAccount(startbalance=balance)

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv()
    symbol = os.getenv("SYMBOL")
    api_key = os.getenv("BYBIT_PUBLIC_TRADE")
    secret = os.getenv("BYBIT_SECRET_TRADE")

    from strategy import strategy
    sk = Skalpit(api_key = api_key, secret = secret, symbol = symbol, strategy = strategy)

    mkt = 58000
    sl = 55000
    tp = 75000
    sk.account.open('long', mkt, stop = sl, tp = tp, risk = 4, is_maker = True, timestamp = int(time.time()))
    sk.bybit.place_active_order(symbol = "BTCUSD", side = "Buy", order_type = "Market", qty = self.account.trade['size'], stop_loss = sl)
    sk.bybit.place_active_order(symbol = "BTCUSD", side = "Sell", order_type = "Limit", qty = self.account.trade['size'], price = tp, reduce_only = "True", time_in_force = "GoodTillCancel")

    time.sleep(2000)

    oid = sk.account.get_limit_order_id()
    print(oid)

    # bb.cancel_active_order_v2(order_id=oid)
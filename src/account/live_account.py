import logging
import json
import time

from src.account.account import Account
from src.utils.utils import get_logger, timestamp_to_date, sameday, percent, date_to_seconds

logger = get_logger(logging.getLogger(__name__), 'logs/live-account.log', logging.DEBUG)

class LiveAccount(Account):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orders = {}

        self.lasttradeclosed = 1500000000 #random time in the past
        self.lasttradeopened = None

    def new_order(self, data):
        logger.debug(f"new_order: {data}")
        oid = data.get('order_id')
        self.orders[oid] = data

    def position_update(self, data):
        logger.debug(f"position_update: {data}")
        size = data.get('size')
        if size == 0 and not self.trade == None and int(time.time()) - self.lasttradeopened > 5:
            self._close(data)
            self.export_position()
            self.trades.append(self.trade)
            self.trade = None
        else:
            self.trade = data
        logger.info(f"position_update: balance {self.balance}, daily won {self.dailywon}, dailylost = {self.dailylost}, dailytrades = {self.dailytrades}")

    def export_position(self):
        logger.debug(f"export_position")
        timestamp = int(time.time())
        try:
            with open(f'trades/trade-{timestamp}', 'w') as outfile:
                json.dump({
                    "trade": dict(self.trade),
                    "orders": dict(self.orders)
                }, outfile)
        except Exception as e:
            logger.error(f"""
                export_position: {e} 
                export_position: trade: {self.trade}
                export_position: orders: {self.orders}
                """)

    def order_executed(self, data):
        logger.debug(f"order_executed: {data}")        
        oid = data.get('order_id')
        self.orders[oid] = data

    def open(self, risk, price, stop):
        self.dailytrades += 1
        self.closed = False
        self.lasttradeopened = int(time.time())
        return int(self._size_by_stop_risk( risk, price, stop ))

    def _close(self, data):                
        if not self.trade:
            logger.debug("_close: nothing to close")
            return

        self.closed = True

        startbal = self.balance
        self.balance = float(data.get('wallet_balance'))
        pnl = self.balance - startbal
        
        won = pnl > 0
        lost = pnl < 0
        even = pnl == 0

        self.maxbalance = max(self.balance, self.maxbalance)
        self.maxdrawdown = min(self.maxdrawdown, percent(self.maxbalance, self.balance))        

        if won:
            self.dailywon+=1
            self.totalwon+=1
        if lost: 
            self.dailylost+=1
            self.totallost+=1
        if even:
            self.dailyeven+=1
            self.totaleven+=1

        self.lasttradeclosed = int(time.time())
        self.trade["closetimestamp"] = int(time.time())
        self.trade["result"] = {
            "profit": f"{pnl:.8f}",
            "percent": f"{percent( startbal, self.balance ):.2f}",
            "balance": { "before": startbal, "after": self.balance }
        }
        logger.info(f"_close: closed {self.trade}")


    def update( self, timestamp, kline ):
        #  Test if self is new day to reset intraday statistics
        if self.lastbardate:
            if  not sameday( self.lastbardate, timestamp ):
                self.dailywon = 0
                self.dailylost = 0
                self.dailytrades = 0
                self.dailyeven = 0

        self.lastbardate = timestamp

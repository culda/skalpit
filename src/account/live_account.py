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

    def new_order(self, data):
        logger.debug(f"new_order: {data}")
        try:
            oid = data.get('order_id')
            self.orders[oid] = {
                'status': 'open',
                'leaves': data.get('leaves_qty'),
                'details': data
            }
        except Exception as e:
            logger.error(f"""
                new_order: {e}
                new_order: {data}
                """)        

    def position_update(self, data):
        logger.debug(f"position_update: {data}")
        size = data.get('size')
        if size == 0 and not self.trade == None:
            self._close(data)            
            self.export_position()
            self.trades.append(self.trade)
            self.trade = None
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
            import traceback
            traceback.print_exc()
            logger.error(f"""
                export_position: {e} 
                export_position: trade: {self.trade}
                export_position: orders: {self.orders}
                """)            


    def order_executed(self, data):
        print("order_executed")
        print(data)
        try:
            oid = data.get('order_id')
            leaves = int(data.get('leaves_qty'))

            if oid in self.orders:
                logger.info(f"order_executed: order {oid} executed; leaves = {leaves}")
                self.orders[oid]['leaves'] = leaves
                if leaves == 0 and self.orders[oid]['status'] == 'open':
                    logger.info(f"order_executed: order {oid} filled")
                    self.orders[oid]['status'] = 'filled'
            else:                
                logger.info(f"order_executed: new order {oid} executed; leaves = {leaves}")
                self.orders[oid] = {
                    'status': 'filled',
                    'leaves': data.get('leaves_qty'),
                    'details': data
                 }

        except Exception as e:
            import traceback
            traceback.print_exc()            
            logger.error(f"""
                order_executed: {e} 
                order_executed: {data}
                """)

    def open(self, side, price, stop = None, tp = None, risk = 5, is_maker = False, timestamp = None ):

        self.dailytrades += 1

        size = self._size_by_stop_risk( risk, price, stop )
        
        self.trade = {
            "side": side,
            "entry": price,
            "stop": stop,
            "tp": tp,
            "risk": risk,
            "size": size,
            "takeprofits": [],
            "opentimestamp": timestamp,
            "closetimestamp": None,
            "result": {},
            "meta": { "initialstop": stop }
        }

    def _close(self, data):
        logger.info(f"_close: active trade: {self.trade}")
        
        if not self.trade:
            logger.debug("_close: nothing to close")
            return

        startbal = self.balance
        self.balance = float(data.get('wallet_balance'))

        pnl = startbal - self.balance

        self.trade['pnl'] = pnl
        self.trade["closetimestamp"] = int(time.time())

        self.closed = True
        self.won = pnl > 0
        self.lost = pnl < 0
        self.even = pnl == 0

        self.maxbalance = max(self.balance, self.maxbalance)
        self.maxdrawdown = min(self.maxdrawdown, percent(self.maxbalance, self.balance))        

        if self.won:
            self.dailywon+=1
            self.totalwon+=1
        if self.lost: 
            self.dailylost+=1
            self.totallost+=1
        if self.even:
            self.dailyeven+=1
            self.totaleven+=1

        self.trade["result"] = {
            "profit": pnl,
            "percent": percent( startbal, self.balance ),
            "balance": { "before": startbal, "after": self.balance }
        }


    def update( self, timestamp, kline ):
        #  Test if self is new day to reset intraday statistics
        if self.lastbardate:
            if  not sameday( self.lastbardate, timestamp ):
                self.dailywon = 0
                self.dailylost = 0
                self.dailytrades = 0
                self.dailyeven = 0

        self.lastbardate = timestamp

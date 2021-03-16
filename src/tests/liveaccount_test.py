import unittest

class TestLiveAccount(unittest.TestCase):
    def setUp(self):
        from src.account.live_account import LiveAccount
        self.account = LiveAccount(startbalance=1)

    def test_new_order(self):
        data = {'order_id': '7dbad481-177e-4e65-9725-ce1dc3fbc46e', 'order_link_id': '', 'symbol': 'BTCUSD', 'side': 'Sell', 'order_type': 'Limit', 'price': '75000', 'qty': 72, 'time_in_force': 'GoodTillCancel', 'create_type': 'CreateByUser', 'cancel_type': '', 'order_status': 'New', 'leaves_qty': 72, 'cum_exec_qty': 0, 'cum_exec_value': '0', 'cum_exec_fee': '0', 'timestamp': '2021-03-13T18:55:11.074Z', 'take_profit': '0', 'stop_loss': '0', 'trailing_stop': '0', 'last_exec_price': '0', 'reduce_only': False, 'close_on_trigger': False}
        self.account.new_order(data)

    def test_position_update(self):
        import time
        mkt = 58000
        sl = 55000
        tp = 75000
        self.account.open('long', mkt, stop = sl, tp = tp, risk = 4, is_maker = True, timestamp = int(time.time()))
        # received position 0 from bybit, meaning the position has been closed
        data = {'user_id': 2476367, 'symbol': 'BTCUSD', 'size': 0, 'side': 'None', 'position_value': '0', 'entry_price': '0', 'liq_price': '0', 'bust_price': '0', 'leverage': '100', 'order_margin': '0', 'position_margin': '0', 'available_balance': '0.00275322', 'take_profit': '0', 'stop_loss': '0', 'realised_pnl': '0.00008028', 'trailing_stop': '0', 'trailing_active': '0', 'wallet_balance': '0.00275322', 'risk_id': 1, 'occ_closing_fee': '0', 'occ_funding_fee': '0', 'auto_add_margin': 1, 'cum_realised_pnl': '-0.00078426', 'position_status': 'Normal', 'position_seq': 0, 'Isolated': False, 'mode': 0, 'position_idx': 0}
        self.account.position_update(data)

        self.assertEqual(self.account.trade, None)

    def test_order_executed(self):
        import time
        self.account.open('long', 59750, stop = 55000, tp = 60456, risk = 4, is_maker = True, timestamp = int(time.time()))
        ord1 = {'symbol': 'BTCUSD', 'side': 'Buy', 'order_id': '1d7e99c3-63ac-426a-9913-2229de86ca01', 'exec_id': 'b3dbdca4-0784-585d-831e-5f3993873fde', 'order_link_id': '', 'price': '59750', 'order_qty': 504, 'exec_type': 'Trade', 'exec_qty': 504, 'exec_fee': '0.00000633', 'leaves_qty': 0, 'is_maker': False, 'trade_time': '2021-03-13T15:45:01.617Z'}
        ord2 = {'symbol': 'BTCUSD', 'side': 'Sell', 'order_id': '5d21b3f2-09cd-49c2-b96d-1ffb6a8e53d7', 'exec_id': '31903b7d-6328-5834-bc9e-050d2bdfab88', 'order_link_id': '', 'price': '60456.5', 'order_qty': 504, 'exec_type': 'Trade', 'exec_qty': 504, 'exec_fee': '-0.00000208', 'leaves_qty': 0, 'is_maker': True, 'trade_time': '2021-03-13T17:57:08.196Z'}
        self.account.order_executed(ord1) # opens a position
        self.account.order_executed(ord2) # closes the position
        self.assertEqual(self.account.trade['stop'], 55000)

    def test_export_position(self):
        self.account.trade =  {'side': 'short', 'entry': 59844.5, 'stop': 60516.3, 'tp': 59206.29, 'risk': 4, 'size': 579.4961175295489, 'takeprofits': [], 'opentimestamp': 1615738260, 'closetimestamp': 1615755695, 'result': {'profit': 6.329999999999704e-06, 'percent': -0.23554277166490056, 'balance': {'before': 0.00268741, 'after': 0.00268108}}, 'meta': {'initialstop': 60516.3}, 'pnl': 6.329999999999704e-06}
        self.account.orders = {'ec7ef202-03c9-4101-a951-17e9e573c7e1': {'status': 'filled', 'leaves': 0, 'details': {'order_id': 'ec7ef202-03c9-4101-a951-17e9e573c7e1', 'order_link_id': '', 'symbol': 'BTCUSD', 'side': 'Sell', 'order_type': 'Market', 'price': '58050', 'qty': 579, 'time_in_force': 'ImmediateOrCancel', 'create_type': 'CreateByUser', 'cancel_type': '', 'order_status': 'Filled', 'leaves_qty': 0, 'cum_exec_qty': 579, 'cum_exec_value': '0.00967507', 'cum_exec_fee': '0.00000726', 'timestamp': '2021-03-14T16:11:00.495Z', 'take_profit': '0', 'stop_loss': '60516', 'sl_trigger_by': 'LastPrice', 'trailing_stop': '0', 'last_exec_price': '59844.5', 'reduce_only': False, 'close_on_trigger': False}}, 'e70b910a-4ec4-425d-b880-10a77edeb9e7': {'status': 'filled', 'leaves': 0, 'details': {'order_id': 'e70b910a-4ec4-425d-b880-10a77edeb9e7', 'order_link_id': '', 'symbol': 'BTCUSD', 'side': 'Buy', 'order_type': 'Market', 'price': '62331', 'qty': 579, 'time_in_force': 'ImmediateOrCancel', 'create_type': 'CreateByStopLoss', 'cancel_type': '', 'order_status': 'Filled', 'leaves_qty': 0, 'cum_exec_qty': 579, 'cum_exec_value': '0.00956629', 'cum_exec_fee': '0.00000718', 'timestamp': '2021-03-14T21:01:34.753Z', 'take_profit': '0', 'stop_loss': '0', 'trailing_stop': '0', 'last_exec_price': '60525', 'reduce_only': True, 'close_on_trigger': True}}, '1e37000b-ae7e-4283-9458-485e5238c773': {'status': 'open', 'leaves': 579, 'details': {'order_id': '1e37000b-ae7e-4283-9458-485e5238c773', 'order_link_id': '', 'symbol': 'BTCUSD', 'side': 'Buy', 'order_type': 'Limit', 'price': '59206', 'qty': 579, 'time_in_force': 'GoodTillCancel', 'create_type': 'CreateByUser', 'cancel_type': '', 'order_status': 'New', 'leaves_qty': 579, 'cum_exec_qty': 0, 'cum_exec_value': '0', 'cum_exec_fee': '0', 'timestamp': '2021-03-14T16:11:00.731Z', 'take_profit': '0', 'stop_loss': '0', 'trailing_stop': '0', 'last_exec_price': '0', 'reduce_only': False, 'close_on_trigger': False}}}
        self.account.export_position()
        
    def test_scenario1(self):
        import time
        self.account.open('long', 59750, stop = 55000, tp = 60456, risk = 4, is_maker = True, timestamp = int(time.time()))
        data = {'order_id': '7dbad481-177e-4e65-9725-ce1dc3fbc46e', 'order_link_id': '', 'symbol': 'BTCUSD', 'side': 'Sell', 'order_type': 'Limit', 'price': '75000', 'qty': 72, 'time_in_force': 'GoodTillCancel', 'create_type': 'CreateByUser', 'cancel_type': '', 'order_status': 'New', 'leaves_qty': 72, 'cum_exec_qty': 0, 'cum_exec_value': '0', 'cum_exec_fee': '0', 'timestamp': '2021-03-13T18:55:11.074Z', 'take_profit': '0', 'stop_loss': '0', 'trailing_stop': '0', 'last_exec_price': '0', 'reduce_only': False, 'close_on_trigger': False}
        self.account.new_order(data)
        exec1 = {'symbol': 'BTCUSD', 'side': 'Buy', 'order_id': '1d7e99c3-63ac-426a-9913-2229de86ca01', 'exec_id': 'b3dbdca4-0784-585d-831e-5f3993873fde', 'order_link_id': '', 'price': '59750', 'order_qty': 504, 'exec_type': 'Trade', 'exec_qty': 504, 'exec_fee': '0.00000633', 'leaves_qty': 0, 'is_maker': False, 'trade_time': '2021-03-13T15:45:01.617Z'}
        exec2 = {'symbol': 'BTCUSD', 'side': 'Sell', 'order_id': '5d21b3f2-09cd-49c2-b96d-1ffb6a8e53d7', 'exec_id': '31903b7d-6328-5834-bc9e-050d2bdfab88', 'order_link_id': '', 'price': '60456.5', 'order_qty': 504, 'exec_type': 'Trade', 'exec_qty': 504, 'exec_fee': '-0.00000208', 'leaves_qty': 0, 'is_maker': True, 'trade_time': '2021-03-13T17:57:08.196Z'}
        self.account.order_executed(exec1) # opens a position
        self.account.order_executed(exec2) # closes the position        

        # received position 0 from bybit, meaning the position has been closed
        data = {'user_id': 2476367, 'symbol': 'BTCUSD', 'size': 0, 'side': 'None', 'position_value': '0', 'entry_price': '0', 'liq_price': '0', 'bust_price': '0', 'leverage': '100', 'order_margin': '0', 'position_margin': '0', 'available_balance': '0.00275322', 'take_profit': '0', 'stop_loss': '0', 'realised_pnl': '0.00008028', 'trailing_stop': '0', 'trailing_active': '0', 'wallet_balance': '0.00275322', 'risk_id': 1, 'occ_closing_fee': '0', 'occ_funding_fee': '0', 'auto_add_margin': 1, 'cum_realised_pnl': '-0.00078426', 'position_status': 'Normal', 'position_seq': 0, 'Isolated': False, 'mode': 0, 'position_idx': 0}
        self.account.position_update(data)

        self.assertEqual(self.account.trade, None)

if __name__ == '__main__':
    unittest.main()
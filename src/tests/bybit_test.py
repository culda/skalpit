import unittest

class TestBybit(unittest.TestCase):
    def setUp(self):
        from src.engine.bybit import Bybit
        from collections import deque
        from dotenv import load_dotenv
        import os
        load_dotenv()
        symbol = os.getenv("SYMBOL")
        api_key = os.getenv("BYBIT_PUBLIC_TRADE")
        secret = os.getenv("BYBIT_SECRET_TRADE")

        self.bybit = Bybit(api_key, secret, symbol, ws = True, test = True, callback = lambda topic , data: None)
        self.bybit.ws_data['klines']['1m'] = deque([[1615124640, 50812.0, 50832.0, 50811.5, 50831.5, 1587620.0, 31.239394730000036], [1615124700, 50831.5, 50832, 50811, 50811, 2138495, 42.07930721000005], [1615124760, 50811, 50811.5, 50811, 50811.5, 1365, 0.026863989999999997]])

    def test_on_ws_kline1(self):
        self.bybit._on_ws_kline('klineV2.1.BTCUSD', [{'start': 1615124820, 'end': 1615124880, 'open': 50718, 'close': 50744.5, 'high': 50744.5, 'low': 50718, 'volume': 787337, 'turnover': 15.522308040000008, 'timestamp': 1615124115066243, 'confirm': False, 'cross_seq': 5071793950}])
        self.assertEqual(len(self.bybit.ws_data['klines']['1m']), 4)
        self.assertEqual(self.bybit.ws_data['klines']['1m'].pop()[0], 1615124820)
        self.assertEqual(self.bybit.ws_data['klines']['1m'].popleft()[0], 1615124640)

    def test_on_ws_kline2(self):
        self.bybit._on_ws_kline('klineV2.1.BTCUSD', [{'start': 1615124760, 'end': 1615124820, 'open': 50718, 'close': 50744.5, 'high': 50744.5, 'low': 50718, 'volume': 787337, 'turnover': 15.522308040000008, 'timestamp': 1615124115066243, 'confirm': False, 'cross_seq': 5071793950}])
        self.assertEqual(len(self.bybit.ws_data['klines']['1m']), 3)
        self.assertEqual(self.bybit.ws_data['klines']['1m'].pop()[0], 1615124760)
        self.assertEqual(self.bybit.ws_data['klines']['1m'].popleft()[0], 1615124640)    

if __name__ == '__main__':
    unittest.main()
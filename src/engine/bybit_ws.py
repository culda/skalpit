import hashlib
import hmac
import time
import threading
import asyncio
import pandas as pd
import json
from collections import deque
import websockets
import logging

from src.engine.bybit_rest import BybitRest
from src.utils.utils import get_logger, date_to_seconds

logger = get_logger(logging.getLogger(__name__), 'logs/bybit-ws.log', logging.DEBUG)

class BybitWs():
    ws_url_main = 'wss://stream.bybit.com/realtime'
    ws_url_test = 'wss://stream-testnet.bybit.com/realtime'

    def __init__(self, api_key, secret, symbol, callback = None, restclient = None, ws=True, test=False):
        self.api_key = api_key
        self.secret = secret

        self.symbol = symbol
        self.callback = callback
        self.restclient = restclient

        self.ping_timeout = 10
        self.sleep_time = 5
    
        self.ws_url = self.ws_url_main if not test else self.ws_url_test        

        if ws:
            self.ws_data = {f'trade.{self.symbol}': deque(maxlen=200), 
                f'instrument_info.100ms.{self.symbol}': {},
                f'orderBookL2_25.{self.symbol}': pd.DataFrame(),
                'position': {},
                'execution': deque(maxlen=200),
                'order': deque(maxlen=200),
                'klines': {
                    '1m': deque(maxlen=2000),
                    '15m': deque(maxlen=2000),
                    '1h': deque(maxlen=2000)
                }
                }

            self._connect()
            
    def _connect(self):
        logger.info("_connect: init WebSocketApp")

        async def listen_forever():
            while True:
                try:
                    logger.debug("listen_forever: connecting")
                    async with websockets.connect(self.ws_url) as ws:
                        logger.debug("listen_forever: connection established")
                        self._setup_klines()
                        await self._on_open(ws)
                        while True:
                            try:
                                message = await asyncio.wait_for(ws.recv(), timeout=self.ping_timeout)
                                await self._on_message(message)
                            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as err:
                                print('listen_forever: ws.recv() timeout')
                                logger.debug(f"listen_forever: ws.recv() timeout, {err}")                                
                                try:
                                    logger.debug('listen_forever: sending ping')
                                    pong = await ws.ping()
                                    await asyncio.wait_for(pong, timeout=self.ping_timeout)
                                    logger.debug('listen_forever: Ping OK, keeping connection alive...')
                                    continue
                                except:
                                    print('listen_forever: ping timeout')
                                    logger.debug(f"listen_forever: ping timeout, {err}")
                                    await asyncio.sleep(self.sleep_time)
                                    break                     
                except ConnectionRefusedError:
                    logger.error(f"listen_forever: ConnectionRefusedError error, {err}")
                    continue
                except Exception as err:
                    logger.error(f"listen_forever: error, {err}")
                    continue

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(listen_forever())
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

        # asyncio.get_event_loop().run_until_complete(listen_forever())
        print("run_until_complete is done")
        logger.info("_connect: run_until_complete is done")
    
    def _on_error(self):
        logger.error("_on_error")

    def _on_close(self):
        logger.info("_on_close: websocket is closed")

    async def _on_open(self, websocket):
        logger.info("_on_open: websocket is open")
        timestamp = int((time.time()+1000) * 1000)
        param_str = 'GET/realtime' + str(timestamp)
        sign = hmac.new(self.secret.encode('utf-8'),
                        param_str.encode('utf-8'), hashlib.sha256).hexdigest()

        logger.debug("authenticating...")
        await websocket.send(json.dumps(
            {'op': 'auth', 'args': [self.api_key, timestamp, sign]}))                    

        await websocket.send(json.dumps(
            {'op': 'subscribe', 'args': ['position',
                                         'execution',
                                         'order',
                                         'stop_order',
                                         f'klineV2.1.{self.symbol}',
                                         f'klineV2.15.{self.symbol}',
                                         f'klineV2.60.{self.symbol}',
                                         ]}))
        # self.send_ping(websocket)

    def send_ping(self, websocket):
        websocket.send('{"op":"ping"}')
        threading.Timer(60, self.send_ping()).start()

    async def _on_message(self, message):
        logger.debug(f"_on_message: {message}")
        try:
            message = json.loads(message)
            if message.get('topic'):
                topic = message.get('topic')

                if 'orderBookL2_25' in topic:
                    self._on_ws_orderbook(message)            
                elif 'execution' in topic:
                    self._on_ws_execution(message)
                elif 'order' in topic:
                    self._on_ws_order(message)
                elif 'instrument_info' in topic:
                    self._on_ws_instrumentinfo(message)
                elif 'trade' in topic:
                    self._on_ws_trade(message)
                elif 'position' in topic:
                    self._on_ws_position(message)
                elif 'kline' in topic:
                    self._on_ws_kline(topic, message['data'])
        except Exception as err:
            import traceback
            traceback.print_exc()
            logger.error(f"_on_message: {err}")

    def _on_ws_execution(self, message):
        self.ws_data['execution'].append(message['data'][0])     
        self.callback(topic = f"execution", data = message.get('data')[0])

    def _on_ws_order(self, message):
        self.ws_data['order'].append(message['data'][0])
        self.callback(topic = f"order", data = message.get('data')[0])

    def _on_ws_instrumentinfo(self, message):
        self.ws_data['position'].append(message)
        self.ws_data[f'instrument_info.100ms.{self.symbol}'].append(message['data'][0])            

    def _on_ws_trade(self, message):
        self.ws_data['trade'].append(message)
        self.ws_data[f'trade.{self.symbol}'].append(message['data'][0])        

    def _on_ws_position(self, message):
        self.ws_data['position'].append(message)
        self.callback(topic = f"position", data = message.get('data')[0])

    def _on_ws_kline(self, topic, data):
        try:
            data = data[0]
            def get_interval(s):
                return {
                    '1': '1m',
                    '15': '15m',
                    '60': '1h'
                }[s]
            
            interval = get_interval(topic.split('.')[1])
            
            tick = [
                data['start'],
                data['open'],
                data['high'],
                data['low'],
                data['close'],
                data['volume'],
                data['turnover']]

            last = self.ws_data['klines'][interval].pop()
            if last[0] == tick[0]:
                self.ws_data['klines'][interval].append(tick)
            else:
                self.ws_data['klines'][interval].append(last)
                self.ws_data['klines'][interval].append(tick)
                self.callback(topic = f"kline.{interval}", data = self.ws_data['klines'][interval])

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"_on_ws_kline: {e}")


    def _on_ws_orderbook(self, message):
        topic = message.get('topic')
        if message['type'] == 'snapshot':
            self.ws_data[topic] = pd.io.json.json_normalize(message['data']).set_index('id').sort_index(ascending=False)
        else: # message['type'] == 'delta'
            # delete or update or insert
            if len(message['data']['delete']) != 0:
                drop_list = [x['id'] for x in message['data']['delete']]
                self.ws_data[topic].drop(index=drop_list)
            elif len(message['data']['update']) != 0:
                update_list = pd.io.json.json_normalize(message['data']['update']).set_index('id')
                self.ws_data[topic].update(update_list)
                self.ws_data[topic] = self.ws_data[topic].sort_index(ascending=False)
            elif len(message['data']['insert']) != 0:
                insert_list = pd.io.json.json_normalize(message['data']['insert']).set_index('id')
                self.ws_data[topic].update(insert_list)
                self.ws_data[topic] = self.ws_data[topic].sort_index(ascending=False)        

    def subscribe(self, topic):
        self.ws.send(json.dumps(
            {'op': 'subscribe', 'args': [f'${topic}.${self.symbol}']}))

    def get_trade(self):
        if not self.ws: return None
        
        return self.ws_data['trade.' + str(self.symbol)]

    def get_instrument(self):
        if not self.ws: return None

        while len(self.ws_data['instrument_info.' + str(self.symbol)]) != 4:
            time.sleep(1.0)
        
        return self.ws_data['instrument_info.' + str(self.symbol)]

    def get_orderbook(self, side=None):
        if not self.ws: return None

        while self.ws_data['orderBookL2_25.' + str(self.symbol)].empty:
            time.sleep(1.0)

        if side == 'Sell':
            orderbook = self.ws_data['orderBookL2_25.' + str(self.symbol)].query('side.str.contains("Sell")', engine='python')
        elif side == 'Buy':
            orderbook = self.ws_data['orderBookL2_25.' + str(self.symbol)].query('side.str.contains("Buy")', engine='python')
        else:
            orderbook = self.ws_data['orderBookL2_25.' + str(self.symbol)]
        return orderbook

    def get_position(self):
        if not self.ws: return None
        
        return self.ws_data['position']

    def get_my_executions(self):
        if not self.ws: return None
        
        return self.ws_data['execution']

    def get_order(self):
        if not self.ws: return None
        
        return self.ws_data['order']

    def _setup_klines(self):
        start_ts_1 = int(time.time()) - 86400
        start_ts_15 = int(time.time()) - 225000
        start_ts_60 = int(time.time()) - 300000
        
        self.ws_data['klines']['1m'] = deque(self.restclient.get_hist_klines(self.symbol, 1, str(start_ts_1)))
        self.ws_data['klines']['15m'] = deque(self.restclient.get_hist_klines(self.symbol, 15, str(start_ts_15)))
        self.ws_data['klines']['1h'] = deque(self.restclient.get_hist_klines(self.symbol, 60, str(start_ts_60)))

        self.callback(topic = "kline.1h", data = self.ws_data['klines']['1h'])
        self.callback(topic = "kline.15m", data = self.ws_data['klines']['15m'])
        self.callback(topic = "kline.1m", data = self.ws_data['klines']['1m'])        
import hashlib
import hmac
import json
import time
import urllib.parse
import threading
from collections import deque
import pandas as pd
from requests import Request, Session
from requests.exceptions import HTTPError
import websocket
import logging

from src.utils.utils import get_logger, date_to_seconds

logger = get_logger(logging.getLogger(__name__), 'logs/bybit.log', logging.DEBUG)

class Bybit():
    url_main = 'https://api.bybit.com'
    url_test = 'https://api-testnet.bybit.com'
    ws_url_main = 'wss://stream.bybit.com/realtime'
    ws_url_test = 'wss://stream-testnet.bybit.com/realtime'
    headers = {'Content-Type': 'application/json'}

    def __init__(self, api_key, secret, symbol, ws=True, callback = None, test=False):
        self.api_key = api_key
        self.secret = secret

        self.symbol = symbol
        self.callback = callback
    
        self.s = Session()
        self.s.headers.update(self.headers)

        self.url = self.url_main if not test else self.url_test
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

            self._setup_klines()

            if not test:
                self._connect()

    #
    # WebSocket
    #

    def _connect(self):
        logger.info("_connect: init WebSocketApp")
        self.ws = websocket.WebSocketApp(url=self.ws_url,
                               on_open=self._on_open,
                               on_message=self._on_message,
                               on_close=self._on_close,
                               on_error=self._on_error)


        # threading.Thread(target=self.ws.run_forever, daemon=False).start()
        self.ws.run_forever()
    
    def _on_error(self):
        logger.error("_on_error")

    def _on_close(self):
        logger.info("_on_close: websocket is closed")

    def _on_open(self):
        logger.info("_on_open: websocket is open")
        timestamp = int((time.time()+1000) * 1000)
        param_str = 'GET/realtime' + str(timestamp)
        sign = hmac.new(self.secret.encode('utf-8'),
                        param_str.encode('utf-8'), hashlib.sha256).hexdigest()

        logger.debug("authenticating...")
        self.ws.send(json.dumps(
            {'op': 'auth', 'args': [self.api_key, timestamp, sign]}))                    

        self.ws.send(json.dumps(
            {'op': 'subscribe', 'args': ['position',
                                         'execution',
                                         'order',
                                         'stop_order',
                                         f'klineV2.1.{self.symbol}',
                                         f'klineV2.15.{self.symbol}',
                                         f'klineV2.60.{self.symbol}',
                                         ]}))
        self.send_ping()

    def send_ping(self):
        self.ws.send('{"op":"ping"}')
        threading.Timer(60, self.send_ping).start()

    def _on_message(self, message):
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
        self.ws_data['position'].append(position)
        self.ws_data[f'instrument_info.100ms.{self.symbol}'].append(message['data'][0])            

    def _on_ws_trade(self, message):
        self.ws_data['trade'].append(position)
        self.ws_data[f'trade.{self.symbol}'].append(message['data'][0])        

    def _on_ws_position(self, message):
        self.ws_data['position'].append(position)
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
    
    #
    # Http Apis
    #

    def _request(self, method, path, payload):
        payload['api_key'] = self.api_key
        payload['timestamp'] = int(time.time() * 1000)
        payload = dict(sorted(payload.items()))
        for k, v in list(payload.items()):
            if v is None:
                del payload[k]

        param_str = urllib.parse.urlencode(payload)
        sign = hmac.new(self.secret.encode('utf-8'),
                        param_str.encode('utf-8'), hashlib.sha256).hexdigest()
        payload['sign'] = sign

        if method == 'GET':
            query = payload
            body = None
        else:
            query = None
            body = json.dumps(payload)


        req = Request(method, self.url + path, data=body, params=query)
        prepped = self.s.prepare_request(req)

        resp = None
        try:
            resp = self.s.send(prepped)
            resp.raise_for_status()
        except HTTPError as e:
            print(e)

        try:
            return resp.json()
        except json.decoder.JSONDecodeError as e:
            print('json.decoder.JSONDecodeError: ' + str(e))
            return resp.text

    def _setup_klines(self):
        start_ts_1 = int(time.time()) - 86400
        start_ts_15 = int(time.time()) - 225000
        start_ts_60 = int(time.time()) - 300000
        
        self.ws_data['klines']['1m'] = deque(self.get_hist_klines(self.symbol, 1, str(start_ts_1)))
        self.ws_data['klines']['15m'] = deque(self.get_hist_klines(self.symbol, 15, str(start_ts_15)))
        self.ws_data['klines']['1h'] = deque(self.get_hist_klines(self.symbol, 60, str(start_ts_60)))

        self.callback(topic = "kline.1h", data = self.ws_data['klines']['1h'])
        self.callback(topic = "kline.15m", data = self.ws_data['klines']['15m'])
        self.callback(topic = "kline.1m", data = self.ws_data['klines']['1m'])



    def get_hist_klines(self, symbol, interval, start_str, end_str=None):
        """Get Historical Klines from Bybit 
        :param symbol: Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD 
        :type symbol: str
        :param interval: Bybit Kline interval -- 1 3 5 15 30 60 120 240 360 720 "D" "M" "W" "Y"
        :type interval: str
        :param start_str: Start date string in UTC format
        :type start_str: str
        :param end_str: optional - end date string in UTC format
        :type end_str: str
        :return: list of OHLCV values
        """

        limit = 200
        start_ts = int(date_to_seconds(start_str))
        end_ts = None
        if end_str:
            end_ts = int(date_to_seconds(end_str))
        else: 
            end_ts = int(date_to_seconds('now'))

        output_data = []
        indexes = []

        idx = 0
        symbol_existed = False
        while True:
            # fetch the klines from start_ts up to max 200 entries 
            temp_dict = self.kline(symbol=symbol, interval=str(interval), _from=start_ts, limit=limit)

            # handle the case where our start date is before the symbol pair listed on Binance
            if not symbol_existed and len(temp_dict):
                symbol_existed = True

            if symbol_existed and len(temp_dict) > 0:
                # extract data and convert to list 
                temp_data = []
                for i in temp_dict['result']:
                    l = list(i.values())[2:]
                    temp_data += [list(float(k) for k in l)]

                output_data += temp_data

                # add timestamps to a different list to create indexes later
                # temp_data = [int(list(i.values())[2]) for i in temp_dict['result']]
                # indexes += temp_data

                # move start_ts over by one interval atter the last value in the array
                # NOTE: current implementation does not support inteval of D/W/M/Y
                start_ts = temp_dict['result'][len(temp_dict['result'])-1]['open_time'] + interval

            else:
                # try every interval until data is found
                start_ts += interval

            idx += 1
            # if we received less than the required limit, we reached present time, so exit the loop
            if len(temp_data) < limit:
                break

            # sleep after every 3rd call to be kind to the API
            if idx % 3 == 0:
                time.sleep(0.2)

        return output_data

    def get_active_order(self, order_id=None, order_link_id=None, symbol=None,
                         sort=None, order=None, page=None, limit=None,
                         order_status=None):
        payload = {
            'order_id': order_id,
            'order_link_id': order_link_id,
            'symbol': symbol if symbol else self.symbol,
            'sort': sort,
            'order': order,
            'page': page,
            'limit': limit,
            'order_status': order_status
        }
        return self._request('GET', '/open-api/order/list', payload=payload)

    def cancel_active_order(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('POST', '/open-api/order/cancel', payload=payload)

    def place_conditional_order(self, side=None, symbol=None, order_type=None,
                                qty=None, price=None, base_price=None,
                                stop_px=None, time_in_force='GoodTillCancel',
                                close_on_trigger=None, reduce_only=None,
                                order_link_id=None):
        payload = {
            'side': side,
            'symbol': symbol if symbol else self.symbol,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'base_price': base_price,
            'stop_px': stop_px,
            'time_in_force': time_in_force,
            'close_on_trigger': close_on_trigger,
            'reduce_only': reduce_only,
            'order_link_id': order_link_id
        }
        return self._request('POST', '/open-api/stop-order/create', payload=payload)

    def get_conditional_order(self, stop_order_id=None, order_link_id=None,
                              symbol=None, sort=None, order=None, page=None,
                              limit=None):
        payload = {
            'stop_order_id': stop_order_id,
            'order_link_id': order_link_id,
            'symbol': symbol if symbol else self.symbol,
            'sort': sort,
            'order': order,
            'page': page,
            'limit': limit
        }
        return self._request('GET', '/open-api/stop-order/list', payload=payload)

    def cancel_conditional_order(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('POST', '/open-api/stop-order/cancel', payload=payload)

    def get_leverage(self):
        payload = {}
        return self._request('GET', '/user/leverage', payload=payload)

    def change_leverage(self, symbol=None, leverage=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'leverage': leverage
        }
        return self._request('POST', '/user/leverage/save', payload=payload)

    def get_position_http(self):
        payload = {}
        return self._request('GET', '/position/list', payload=payload)

    def change_position_margin(self, symbol=None, margin=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'margin': margin
        }
        return self._request('POST', '/position/change-position-margin', payload=payload)

    def get_prev_funding_rate(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/open-api/funding/prev-funding-rate', payload=payload)

    def get_prev_funding(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/open-api/funding/prev-funding', payload=payload)

    def get_predicted_funding(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/open-api/funding/predicted-funding', payload=payload)

    def get_my_execution(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('GET', '/v2/private/execution/list', payload=payload)


    def get_balance(self, symbol = 'BTC'):
        payload = {
            'coin': symbol
        }
        return self._request('GET', '/v2/private/wallet/balance', payload=payload)        
    #
    # New Http Apis (developing)
    #

    def symbols(self):
        payload = {}
        return self._request('GET', '/v2/public/symbols', payload=payload)

    def kline(self, symbol=None, interval=None, _from=None, limit=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'interval': interval,
            'from': _from,
            'limit': limit
        }
        return self._request('GET', '/v2/public/kline/list', payload=payload)

    def place_active_order(self, symbol=None, side=None, order_type=None,
                              qty=None, price=None, stop_loss = None, reduce_only = "False",
                              time_in_force='GoodTillCancel',
                              order_link_id=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
            'side': side,
            'order_type': order_type,
            'qty': qty,
            'price': price,
            'time_in_force': time_in_force,
            'stop_loss': stop_loss,
            # 'reduce_only': reduce_only, #not working
            'order_link_id': order_link_id
        }
        return self._request('POST', '/v2/private/order/create', payload=payload)

    def cancel_active_order(self, order_id=None):
        payload = {
            'order_id': order_id
        }
        return self._request('POST', '/v2/private/order/cancel', payload=payload)

    def cancel_active_orders_all(self):
        payload = {
            'symbol': self.symbol
        }
        return self._request('POST', '/v2/private/order/cancelAll', payload=payload)

    #
    # New Http Apis added by ST 
    #

    def get_ticker(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/v2/public/tickers', payload=payload)

    def get_orderbook_http(self, symbol=None):
        payload = {
            'symbol': symbol if symbol else self.symbol,
        }
        return self._request('GET', '/v2/public/orderBook/L2', payload=payload)


if __name__ == '__main__':

    bybit = Bybit(api_key='xxxxxxxxx',
                  secret='yyyyyyyyyyyyyyyyyyy', symbol='BTCUSD', test=True, ws=True)

    position = bybit.get_position()
    print('Position ----------------------------------------------------------')
    print(json.dumps(position, indent=2))

    orderbook_buy = bybit.get_orderbook(side='Buy')
    print('Orderbook (Buy) ---------------------------------------------------')
    print(orderbook_buy.head(5))
    best_buy = float(orderbook_buy.iloc[0]['price'])

    print('Sending Order... --------------------------------------------------')
    ### NOTE: price needs to be converted to STRING! (float will give you signature error)
    order_resp = bybit.place_active_order(side='Buy', order_type='Limit', qty=100, price=str(best_buy - 100), time_in_force='PostOnly')
    print(json.dumps(order_resp, indent=2))
    order_id = order_resp['result']['order_id'] if order_resp['result'] else None

    time.sleep(5.0)

    print('Cancel Order... ---------------------------------------------------')
    cancel_resp = bybit.cancel_active_order(order_id=order_id)
    print(json.dumps(cancel_resp, indent=2))
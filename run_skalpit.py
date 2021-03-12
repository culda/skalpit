import os
from dotenv import load_dotenv
from skalpit import Skalpit

import time

def main():
    load_dotenv()
    symbol = os.getenv("SYMBOL")
    api_key = os.getenv("BYBIT_PUBLIC_TRADE")
    secret = os.getenv("BYBIT_SECRET_TRADE")

    from strategy import strategy
    Skalpit(api_key = api_key, secret = secret, symbol = symbol, strategy = strategy)

if __name__ == '__main__':
    main()

# Skalpit - a directional trading bot

Docker
```
docker build -f dockerfile.skalpit -t skalpit:latest .
docker run -d skalpit:latest
```


```
sudo apt-get update
sudo apt-get -y upgrade
```
```
>>> python3 -V
3.7+
```
Install Python 3.9:
https://tecadmin.net/install-python-3-9-on-centos-8/

if using apt
```
sudo apt-get install -y python3-pip
sudo apt-get install build-essential libssl-dev libffi-dev python3-dev python3-venv
```
```
git clone git@github.com:culda/skalpit.git
cd skalpit
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p logs trades hist_data
```

You need to create a .env file and fill in your API keys
```
SYMBOL=BTCUSD
BYBIT_PUBLIC_TRADE=
BYBIT_SECRET_TRADE=

```

To run the backtester

```
python main.py backtester 2021-03-05 2021-03-10
```

To run skalpit

```
python main.py skalpit
```

Running tests
```
python -m unittest discover -s src/tests -p '*_test.py'
```
#! /bin/bash

sudo apt-get update
sudo apt-get -y upgrade

sudo apt-get install -y python3-pip
sudo apt-get install build-essential libssl-dev libffi-dev python3-dev python3-venv

git clone git@github.com:culda/skalpit.git
cd skalpit
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p logs
mkdir -p trades
mkdir -p hist_data
from __future__ import print_function

import pymongo
import threading
import datetime
from ast import literal_eval
import redis

from lxml import html
import os
import sys
import datetime as dt
import json
import requests
from time import sleep
from bittrex import Bittrex

import pymongo
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# from common import get_arg
# Update Python Path to be able to load custom modules. Do not change line position.

# number = 0


class Subscriber:
    def __init__(self, name=None):
        if not name:
            self.name = str(self.__class__).split(' ')[1].split("'")[1]
        else:
            self.name = name

    def update(self, message):
        # start new Thread in here to handle any task
        print('\n\n {} got message "{}"'.format(self.name, message))


class MyMongoClient(Subscriber):

    def __init__(self, db_name, collection_name, host='localhost', is_exchange_data=False, port=27017, *args, **kwargs):
        self._c = pymongo.MongoClient(host, port)
        self.set_database(db_name)
        self.set_collection(collection_name)
        self.collection_name = collection_name
        self.db_name = db_name
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.is_exchange_data = is_exchange_data

    def is_duplicate_data(self, msg):
        return self.collection.find_one(msg)

    def insert_one(self, data):
        self.collection.insert_one(data)
        print('------table name-----')
        print(self.collection)
        print('Inserted: \n{}'.format(data))

    def insert_many(self, msg):
        self.collection.insert_many(msg)

    def update(self, msg):
        # msg = literal_eval(msg)
        if not self.is_exchange_data:
            t = threading.Thread(target=self.check_duplicity_and_update_record, args=(msg,))
        else:
            t = threading.Thread(target=self.set_in_redis, args=(msg,))
        t.start()

    def check_duplicity_and_update_record(self, msg):
        if not self.is_duplicate_data(msg):
            t = threading.Thread(target=self.insert_many, args=(msg,)) if type(msg) == list else threading.Thread(
                target=self.insert_one, args=(msg,))
            t.start()

    def set_in_redis(self, msg):
        key = datetime.datetime.now().replace(second=0, microsecond=0)
        data = {self.db_name: {self.collection_name: [msg]}}

        if self.redis.exists(key):
            data = literal_eval(self.redis.get(key))
            print(data)
            if data.has_key(self.db_name) and data[self.db_name].has_key(self.collection_name):

                if type(msg) == list:
                    data[self.db_name][self.collection_name].extend(msg)
                else:
                    data[self.db_name][self.collection_name].append(msg)
            elif data.has_key(self.db_name):
                data[self.db_name].update({self.collection_name: [msg]})
        self.redis.set(key, data)

    def set_collection(self, collection_name):
        self.collection = self.database[collection_name]

    def set_database(self, db_name):
        self.database = self._c[db_name]


def get_arg(index, default=None):
    """
    Grabs a value from the command line or returns the default one.
    """
    try:
        return sys.argv[index]
    except IndexError:
        return default


def get_data(number):

    db_name = 'BB_coins'
    with open('accountkey.json') as data_file:
        keydata = json.load(data_file)
        tradernumbers = len(keydata)
    markets_data = []
    collection_names = []
    for traderindex in keydata:
        # print(traderindex)

        trader_name = traderindex['name']
        trader_key = traderindex['Key']
        trader_secret = traderindex['Secret']

        trader = get_arg(1, trader_name)  # 'LANDON', 'CHRISTIAN' OR 'VIVEK.
        collection_names.append('{}_bittrex_account'.format(trader))
        # try:
        #     # db_user = 'Writeuser'
        #     # db_password = os.environ['MONGO-WRITE-PASSWORD']
        #     # db_password = 'TYHJ8ttfZ6JPRvSZbqcW'
        #     # host = 'mongodb://{}:{}@127.0.0.1'.format(db_user, db_password)
        #     # host = 'mongodb://{}:{}@10.8.0.2'.format(db_user, db_password)
        #
        #     mongoserver_uri = "mongodb://Writeuser:TYHJ8ttfZ6JPRvSZbqcW@10.8.0.2:27017/admin"
        #     connection = MongoClient(host=mongoserver_uri)
        #     db = connection['BB_coins']
        #     db_collection = db[collection_name]
        #
        # except KeyError:
        #     host = 'localhost'
        #     db_collection = MyMongoClient(db_name, collection_name=collection_name, host=host)

        api = Bittrex(api_key=trader_key, api_secret=trader_secret)
        market = api.get_markets()["result"]
        markets_data.append(market)

    balance_curr_codes = []

    for i in range(len(markets_data)):
        balance_curr_codes.append([])
        for data in markets_data[i]:
            if data["BaseCurrency"] == 'BTC':
                balance_curr_codes[i].append(data["MarketCurrency"])
    print(balance_curr_codes)

    for i in range(len(balance_curr_codes)):
        for balance_curr_code in balance_curr_codes[i]:
            market_history_data = api.get_market_history('BTC-' + balance_curr_code, count=1)["result"][0]
            json_data = ({
                'Number': number,
                'balance_curr_code': balance_curr_code,
                'last_price': market_history_data['Price'],
                'TimeStamp': market_history_data['TimeStamp']})

            try:
                # db_user = 'Writeuser'
                # db_password = os.environ['MONGO-WRITE-PASSWORD']
                # db_password = 'TYHJ8ttfZ6JPRvSZbqcW'
                # host = 'mongodb://{}:{}@127.0.0.1'.format(db_user, db_password)
                # host = 'mongodb://{}:{}@10.8.0.2'.format(db_user, db_password)

                mongoserver_uri = "mongodb://Writeuser:TYHJ8ttfZ6JPRvSZbqcW@10.8.0.2:27017/admin"
                connection = MongoClient(host=mongoserver_uri)
                db = connection['BB_coins']
                db_collection = db[collection_names[i]]

            except KeyError:
                host = 'localhost'
                db_collection = MyMongoClient(db_name, collection_name=collection_names[i], host=host)

            db_collection.insert_one(json_data)
            print(collection_names[i])
            print('Inserted: \n{}'.format(json_data))



    # for balance_curr_code in balance_curr_codes:
    #     market_history_data = api.get_market_history('BTC-' + balance_curr_code, count=1)["result"][0]
    #     json_data = ({
    #         'Number': number,
    #         'balance_curr_code': balance_curr_code,
    #         'last_price': market_history_data['Price'],
    #         'TimeStamp': market_history_data['TimeStamp']})

        # db_collection.insert_one(json_data)
        # print('------table name-----')
        # print(collection_name)
        # print('Inserted: \n{}'.format(json_data))
    # return print(collection_name)

if __name__ == "__main__":

        # Time setting.
        number = 0
        next_call = dt.datetime.now()
        time_between_calls = dt.timedelta(seconds=int(get_arg(2, 3000)))
        # Main loop.
        while True:
            now = dt.datetime.now()
            if now >= next_call:
                try:
                    next_call = now + time_between_calls
                    number += 1
                    get_data(number)
                except:
                    continue


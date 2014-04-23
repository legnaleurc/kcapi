#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Wei-Cheng Pan (潘韋成) <legnaleurc@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import logging
import sys
import threading

import tornado.ioloop
import tornado.web

import client


def setup_logger():
    # setup logger
    logger = logging.getLogger('kcapi')
    logger.setLevel(logging.DEBUG)
    formater = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # add file handler
    handler = logging.FileHandler('/tmp/kcapi.log')
    handler.setFormatter(formater)
    logger.addHandler(handler)
    # add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formater)
    logger.addHandler(handler)


class APIHandler(tornado.web.RequestHandler):

    def initialize(self, api, *args, **kwargs):
        super().initialize(*args, **kwargs)

        self._api = api


class APIShip2Handler(APIHandler):

    def get(self):
        table = {
            'level': 1,
            'type': 2,
            'new': 3,
            'health': 4,
        }
        sort_by = self.get_query_argument('sort_by')
        sort_by = table.get(sort_by)
        if not sort_by:
            self.write(None)
            return
        response = self._api.ship2(api_sort_key=sort_by)
        self.write(response)


class APIShipHandler(APIHandler):

    def get(self):
        response = self._api.ship()
        self.write(response)


class APIDeckHandler(APIHandler):

    def get(self):
        response = self._api.deck()
        self.write(response)


class ChargeHandler(APIHandler):

    def get(self):
        id_ = self.get_query_argument('id')
        id_ = int(id_) - 1

        response = self._api.deck()
        if response['api_result'] != 1:
            self.write(None)
            return
        team = response['api_data'][id_]['api_ship']

        response = self._api.charge(api_id_items=team, api_kind=3)
        self.write(response)


def main(args=None):
    if args is None:
        args = sys.argv

    api_token = args[1]

    setup_logger()

    client_ = client.Client(api_token)
    event_loop = tornado.ioloop.IOLoop()
    # event_loop = task.EventLoop()

    mission = client.Mission(client=client_, event_loop=event_loop)
    mission.start(api_deck_id=2, api_mission_id=2)
    mission.start(api_deck_id=3, api_mission_id=5)
    mission.start(api_deck_id=4, api_mission_id=6)

    nyukyo = client.Nyukyo(client=client_, event_loop=event_loop)
    nyukyo.start()

    event_loop.start()
    # t = threading.Thread(target=lambda: event_loop.start())
    # t.start()

    # app = tornado.web.Application([
    #     (r'/api/ship', APIShipHandler, {'api': api}),
    #     (r'/api/ship2', APIShip2Handler, {'api': api}),
    #     (r'/api/deck', APIDeckHandler, {'api': api}),
    #     (r'/charge', ChargeHandler, {'api': api}),
    # ])

    # app.listen(8000)
    # tornado.ioloop.IOLoop.instance().start()

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

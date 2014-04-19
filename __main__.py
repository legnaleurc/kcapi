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


import time
import sys

import tornado.ioloop
import tornado.web

from api import API
import db


# create session class
Session = db.initialize(echo=True)


class Client(object):

    def __init__(self, api_token):
        self._api = API(api_token)

        # get all ship model
        self._master_ship()
        # get deck and ships
        self._ship2()

    def _master_ship(self):
        data = self._api.master_ship()
        if data['api_result'] != 1:
            return

        data = data['api_data']
        session = Session()
        for ship in data:
            row = db.ShipType(
                api_id=ship['api_id'],
                api_sortno=ship['api_sortno'],
                api_name=ship['api_name'],
                api_yomi=ship['api_yomi'],
                api_stype=ship['api_stype'],
                api_ctype=ship['api_ctype'],
                api_cnum=ship['api_cnum'],
                api_enqflg=ship['api_enqflg'],
                api_afterlv=ship['api_afterlv'],
                api_aftershipid=ship['api_aftershipid'],
                api_fuel_max=ship['api_fuel_max'],
                api_bull_max=ship['api_bull_max'])
            session.add(row)
        session.commit()

    def _ship2(self):
        data = self._api.ship2(api_sort_key=1)
        if data['api_result'] != 1:
            return

        session = Session()

        ship_data = data['api_data']
        for ship in ship_data:
            row = db.Ship(
                api_id=ship['api_id'],
                api_sortno=ship['api_sortno'],
                api_ship_id=ship['api_ship_id'],
                api_lv=ship['api_lv'],
                api_nowhp=ship['api_nowhp'],
                api_maxhp=ship['api_maxhp'],
                api_ndock_time=ship['api_ndock_time'],
                api_fuel=ship['api_fuel'],
                api_bull=ship['api_bull'])
            session.add(row)
        session.commit()

        deck_data = data['api_data_deck']
        for deck in deck_data:
            row = db.Deck(
                api_id=deck['api_id'],
                api_name=deck['api_name'],
                mission_id=deck['api_mission'][1],
                mission_time=deck['api_mission'][2])

            ships = deck['api_ship']
            for ship in ships:
                if ship == -1:
                    continue
                s = (session.query(db.Ship)
                     .filter(db.Ship.api_id == ship)
                     .first())
                row.api_ship.append(s)

            session.add(row)
        session.commit()


    def update(self):
        session = Session()
        session.query(db.Deck).delete()
        session.query(db.Ship).delete()
        session.commit()
        self._ship2()


    def start_mission(self, api_deck_id, api_mission_id):
        # update data
        self.update()

        # hokyu
        session = Session()
        ships_id = [x for x, in session.query(db.Ship.api_id).join(db.ShipType).filter((db.Ship.api_fuel < db.ShipType.api_fuel_max) | (db.Ship.api_bull < db.ShipType.api_bull_max))]
        data = self._api.charge(api_id_items=ships_id, api_kind=3)
        if data['api_result'] != 1:
            # TODO print error
            print(data['api_result_msg'])
            return

        # start mission
        data = self._api.mission(api_deck_id=api_deck_id, api_mission_id=api_mission_id)
        if data['api_result'] != 1:
            # TODO print error
            print(data['api_result_msg'])
            return

        # update cache
        deck = (session.query(db.Deck)
                .filter(db.Deck.api_id == api_deck_id)
                .first())
        deck.mission_id = api_mission_id
        deck.mission_time = data['api_data']['api_complatetime']
        session.commit()

    def test(self):
        self.start_mission(api_deck_id=2, api_mission_id=3)


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


class Mission(object):

    def __init__(self, client):
        self._client = client
        self._jobs = set()

    def start(self, api_deck_id, api_mission_id):
        self._jobs.add(api_deck_id)

        delta = self._client.start_mission(api_deck_id, api_mission_id)
        self._timer.setTimeout(delta, lambda: self._on_done(api_deck_id, api_mission_id))

    def stop(self, api_deck_id):
        self._timer.clearTimeout()
        self.remove(api_deck_id)

    def _on_done(self, api_deck_id, api_mission_id):
        if api_deck_id not in self._jobs:
            return

        delta = self._client.start_mission(api_deck_id, api_mission_id)
        self._timer.setTimeout(delta, lambda: self._on_done(api_deck_id, api_mission_id))


def main(args=None):
    if args is None:
        args = sys.argv

    api_token = args[1]

    client = Client(api_token)
    client.test()

    # mission = Mission(client=client)
    # mission.start(api_deck_id=2, api_mission_id=3)

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

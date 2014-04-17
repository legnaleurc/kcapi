#! /usr/bin/env python


from api import API
import db

import tornado.ioloop
import tornado.web

import sys


# create session class
Session = db.initialize()


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
                api_aftershipid=ship['api_aftershipid'])
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
                api_ndock_time=ship['api_ndock_time'])
            session.add(row)
        session.commit()

        deck_data = data['api_data_deck']
        for deck in deck_data:
            row = db.Deck(
                api_id=deck['api_id'],
                api_name=deck['api_name'])

            ships = deck['api_ship']
            for ship in ships:
                if ship == -1:
                    continue
                s = session.query(db.Ship).filter(db.Ship.api_id==ship).first()
                row.api_ship.append(s)

            session.add(row)
        session.commit()

    def test(self):
        session = Session()
        for deck in session.query(db.Deck).all():
            name = deck.api_name
            print(name)
            for ship in deck.api_ship:
                print(ship.ship_type.api_name)


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

    client = Client('__API_TOKEN__')
    client.test()
    # api = API('__API_TOKEN__')

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

#! /usr/bin/env python


from api import API
import db

import tornado.ioloop
import tornado.web

import sys


# create session class
Session = db.initialize()


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

    api = API('__API_TOKEN__')

    app = tornado.web.Application([
        (r'/api/ship', APIShipHandler, {'api': api}),
        (r'/api/ship2', APIShip2Handler, {'api': api}),
        (r'/api/deck', APIDeckHandler, {'api': api}),
        (r'/charge', ChargeHandler, {'api': api}),
    ])

    app.listen(8000)
    tornado.ioloop.IOLoop.instance().start()

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

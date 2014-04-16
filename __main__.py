#! /usr/bin/env python


import requests
import tornado.ioloop
import tornado.web

import json
import sys


class API(object):

    def __init__(self, api_token):
        self._api_token = api_token
        self._api_verno = 1
        self._server_prefix = 'http://125.6.189.135'
        self._referer_port = '{0}/kcs/port.swf?version={1}'.format(self._server_prefix, '1.7.1')
        self._referer_battle = '{0}/kcs/battle.swf?version={1}'.format(self._server_prefix, '1.4.4')

        self._user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:28.0) Gecko/20100101 Firefox/28.0'

    def _do_request(self, path, data=None):
        headers = {
            'User-Agent': self._user_agent,
            'DNT': 1,
            'Referer': self._referer_port,
        }
        data_ = {
            'api_verno': self._api_verno,
            'api_token': self._api_token,
        }
        if data:
            data_.update(data)

        response = requests.post(self._server_prefix + path, data=data_, headers=headers)
        if response.status_code != 200:
            return None

        json_text = response.text[7:]
        response = json.loads(json_text)
        return response

    def ship(self):
        return self._do_request('/kcsapi/api_get_member/ship')

    def ship2(self, api_sort_key):
        return self._do_request('/kcsapi/api_get_member/ship2', {
            'api_sort_order': 2,
            'api_sort_key': api_sort_key,
        })

    def deck(self):
        return self._do_request('/kcsapi/api_get_member/deck')

    def charge(self, api_id_items, api_kind):
        return self._do_request('/kcsapi/api_req_hokyu/charge', {
            'api_id_items': ','.join(map(str, api_id_items)),
            'api_kind': api_kind,
        })


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

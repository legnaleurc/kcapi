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


import json

import requests


class API(object):

    def __init__(self, api_token):
        self._api_token = api_token
        self._api_verno = 1
        self._server_prefix = 'http://125.6.189.135'
        self._referer_port = '{0}/kcs/port.swf?version={1}'.format(
            self._server_prefix,
            '1.7.1')
        self._referer_battle = '{0}/kcs/battle.swf?version={1}'.format(
            self._server_prefix,
            '1.4.4')

        self._user_agent = ('Mozilla/5.0'
                            ' (Macintosh; Intel Mac OS X 10.9; rv:28.0)'
                            ' Gecko/20100101 Firefox/28.0')

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

        response = requests.post(
            self._server_prefix + path,
            data=data_,
            headers=headers)
        if response.status_code != 200:
            return None

        json_text = response.text[7:]
        response = json.loads(json_text)
        return response

    def master_ship(self):
        return self._do_request('/kcsapi/api_get_master/ship')

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

    def mission_start(self, api_deck_id, api_mission_id):
        return self._do_request('/kcsapi/api_req_mission/start', {
            'api_deck_id': api_deck_id,
            'api_mission_id': api_mission_id,
        })

    def nyukyo_start(self, api_ship_id, api_ndock_id, api_highspeed):
        return self._do_request('/kcsapi/api_req_nyukyo/start', {
            'api_ship_id': api_ship_id,
            'api_ndock_id': api_ndock_id,
            'api_highspeed': api_highspeed,
        })

    def ndock(self):
        return self._do_request('/kcsapi/api_get_member/ndock')

import requests

import json


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

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
import math
import random
import time
import re

from tornado.util import ObjectDict

from api import API
import db
import event


# create session class
Session = db.initialize()


class Client(object):

    def __init__(self):
        self._log = logging.getLogger('kcapi')
        self._api = None

    @property
    def is_ready(self):
        return not not self._api

    def set_api_token(self, api_token):
        self._api = API(api_token)
        # get all information
        self._api_start()
        # get deck and ships
        self._create_port()

    def _api_start(self):
        data = self._api.api_start2()
        if data['api_result'] != 1:
            self._log.error(data['api_result_msg'])
            raise Exception('api_start2 error')

        self._master_data = data['api_data']
        event.api_started.emit(data=data['api_data'])
        self._create_ship_type(self._master_data['api_mst_ship'])

        data = self._api.basic()
        if data['api_result'] != 1:
            self._log.error(data['api_result_msg'])
            raise Exception('basic error')

        self._member_id = int(data['api_data']['api_member_id'])

    def _create_ship_type(self, ship_data):
        session = Session()
        for ship in ship_data:
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

    def _create_port(self):
        api_port = _api_port(self._member_id)
        data = self._api.port(api_port)
        if data['api_result'] != 1:
            self._log.error(data['api_result_msg'])
            return

        data = data['api_data']
        deck_port = data['api_deck_port']
        ndock = data['api_ndock']
        ship = data['api_ship']
        self._create_ship(ship)
        self._create_deck(deck_port)
        self._create_ndock(ndock)
        need_refresh = self._check_mission_result(deck_port)
        if need_refresh:
            self._update_all()

    def _create_ship(self, ship_data):
        session = Session()
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

    def _create_deck(self, deck_data):
        session = Session()
        for deck in deck_data:
            row = db.Deck(
                api_id=deck['api_id'],
                api_name=deck['api_name'],
                mission_status=deck['api_mission'][0],
                mission_id=deck['api_mission'][1],
                mission_time=deck['api_mission'][2])

            ships = deck['api_ship']
            ships = filter(lambda x: x > 0, ships)
            ships = session.query(db.Ship).filter(db.Ship.api_id.in_(ships))
            row.api_ship.extend(ships)

            session.add(row)
            self._log.info('api_id: {0}, mission_id: {1}, mission_time: {2}'.format(row.api_id, row.mission_id, row.mission_time))
        session.commit()

    def _create_ndock(self, ndock_data):
        session = Session()
        for ndock in ndock_data:
            row = db.NDock(
                api_id=ndock['api_id'],
                api_state=ndock['api_state'],
                api_ship_id=ndock['api_ship_id'],
                api_complete_time=ndock['api_complete_time'])
            session.add(row)
        session.commit()

    def _check_mission_result(self, decks_data):
        need_refresh = False
        session = Session()
        for deck_data in decks_data:
            if deck_data['api_mission'][0] == 2:
                deck = session.query(db.Deck).filter(db.Deck.api_id == deck_data['api_id']).first()
                self._log.info('deck {0} returned from mission {1}'.format(deck.api_id, deck.mission_id))

                data = self._api.result(api_deck_id=deck.api_id)
                if data['api_result'] != 1:
                    self._log.error(data['api_result_msg'])
                    continue
                data = data['api_data']
                self._log.info('mission result: {0}'.format(data['api_clear_result']))
                event.mission_result.emit(api_deck_id=deck.api_id, api_clear_result=data['api_clear_result'])

                deck.mission_status = 0
                deck.mission_id = 0
                deck.mission_time = 0

                # NOTE nop, just simulate flash client
                api_port = _api_port(self._member_id)
                self._api.port(api_port)
                self._api.useitem()

                need_refresh = True
        session.commit()
        return need_refresh

    def _update_all(self):
        # FIXME should do lazy update
        session = Session()
        session.query(db.Deck).delete()
        session.query(db.NDock).delete()
        session.query(db.Ship).delete()
        session.commit()
        self._create_port()

    def start_mission(self, api_deck_id, api_mission_id):
        # update data
        self._update_all()

        # hokyu
        session = Session()
        ships_id = [x for x, in session.query(db.Ship.api_id).join(db.ShipType).filter((db.Ship.api_fuel < db.ShipType.api_fuel_max) | (db.Ship.api_bull < db.ShipType.api_bull_max))]
        if ships_id:
            data = self._api.charge(api_id_items=ships_id, api_kind=3)
            if data['api_result'] != 1:
                self._log.error('response error: {0}'.format(data['api_result_msg']))
                return False

        # NOTE nop, just simulate flash client
        self._api.get_missions()

        # start mission
        data = self._api.mission(api_deck_id=api_deck_id, api_mission_id=api_mission_id)
        if data['api_result'] != 1:
            self._log.error('response error: {0}'.format(data['api_result_msg']))
            return False

        # NOTE nop, just simulate flash client
        self._api.deck()

        # update cache
        deck = (session.query(db.Deck)
                .filter(db.Deck.api_id == api_deck_id)
                .first())
        deck.mission_id = api_mission_id
        deck.mission_time = data['api_data']['api_complatetime']
        session.commit()

        return True

    def nyukyo(self, api_ship_id, api_ndock_id, api_highspeed):
        # update data
        self._update_all()

        # NOTE nop, just simulate flash client
        self._api.ndock()

        data = self._api.nyukyo(api_ship_id=api_ship_id, api_ndock_id=api_ndock_id, api_highspeed=api_highspeed)
        if data['api_result'] != 1:
            self._log.error('response error: {0}'.format(data['api_result_msg']))
            return False

        # NOTE nop, just simulate flash client
        self._api.ndock()

        self._update_all()

        return True

    def get_wounded_ships(self):
        session = Session()
        # may order by api_ndock_time
        # note that some ships may in a mission
        ships = (session
                 .query(db.Ship.api_id)
                 .outerjoin(db.Deck)
                 .filter(
                    # query hp
                    (db.Ship.api_nowhp < db.Ship.api_maxhp)
                    &
                    # not in a ndock
                    (~db.Ship.ndock.has())
                    &
                    (
                        # not in a deck
                        (~db.Ship.deck.has())
                        |
                        # not in a mission
                        (db.Deck.mission_status == 0)
                    )
                 )
                 # order by emergency
                 .order_by(db.Ship.api_nowhp * 100 / db.Ship.api_maxhp))
        return [ship for ship, in ships]


_Il = [1623, 5727, 9278, 3527, 4976, 7180734, 6632, 3708, 4796, 9675, 13, 6631, 2987, 10, 1901, 9881, 1000, 3527]


def _api_port(ll):
    lI = _create_key()
    return lI.t(
        lI.s(
            lI.u(
                lI.z(
                    _Il[16],
                    lI.u(
                        lI.i(9),
                        1)),
                lI.p(
                    _Il[16],
                    ll))),
        lI.s(
            lI.z(
                lI.m(
                    lI.z(
                        _Il[5],
                        lI.l(
                            lI.s(ll),
                            0,
                            4)),
                    lI.u(
                        lI.n(),
                        ll)),
                _Il[_I1(lI.p(10,ll),lI)])),
        lI.s(
            lI.u(
                lI.i(
                    lI.z(
                        9,
                        _Il[16])),
                _Il[16])))


def _create_key():
    is_int = re.compile(r'\d+')
    key = ObjectDict()
    key.r = math.floor
    key.i = lambda a: key.r(random.random() * a)
    key.l = lambda a, b, c: int(a[b:b+c]) if is_int.match(a[b:b+c]) else None
    key.m = lambda a, b: a - b
    key.n = lambda: key.r(time.time())
    key.p = lambda a, b: b % a
    key.s = str
    key.t = lambda *args: ''.join(args)
    key.u = lambda a, b: a + b
    key.y = math.sqrt
    key.z = lambda a, b: a * b
    return key


def _I1(II, lI):
    ll = 0
    while II != lI.l(lI.s(lI.y(_Il[_Il[13]])),ll,1):
        ll += 1
    return ll

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

from api import API
import db
import task


# create session class
Session = db.initialize()


class Client(object):

    def __init__(self, api_token):
        self._log = logging.getLogger('kcapi')
        self._api = API(api_token)

        # get all information
        self._api_start()
        # get deck and ships
        self._port()

    def _api_start(self):
        data = self._api.api_start2()
        if data['api_result'] != 1:
            self._log.error(data['api_result_msg'])
            raise Exception('api_start2 error')

        self._master_data = data['api_data']
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

    def _port(self):
        api_port = _api_port(self._member_id)
        data = self._api.port(api_port)
        if data['api_result'] != 1:
            self._log.error(data['api_result_msg'])
            return

        data = data['api_data']
        deck_port = data['api_deck_port']
        ndock = data['api_ndock']
        ship = data['api_ship']
        self._update_ship(ship)
        self._update_deck(deck_port)
        self._update_ndock(ndock)

    def _update_ship(self, ship_data):
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

    def _update_deck(self, deck_data):
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

    def _update_ndock(self, ndock_data):
        session = Session()
        for ndock in ndock_data:
            row = db.NDock(
                api_id=ndock['api_id'],
                api_state=ndock['api_state'],
                api_ship_id=ndock['api_ship_id'],
                api_complete_time=ndock['api_complete_time'])
            session.add(row)
        session.commit()

    def _deck_port(self):
        # check any mission completed
        data = self._api.deck_port()
        if data['api_result'] != 1:
            self._log.error(data['api_result_msg'])
            return

        session = Session()
        decks_data = data['api_data']
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

                deck.mission_status = 0
                deck.mission_id = 0
                deck.mission_time = 0
        session.commit()

    def _update_all(self):
        self._deck_port()
        # FIXME should do lazy update
        session = Session()
        session.query(db.Deck).delete()
        session.query(db.NDock).delete()
        session.query(db.Ship).delete()
        session.commit()
        self._member_ship()

    def _update_ndock(self):
        session = Session()
        session.query(db.NDock).delete()
        session.commit()
        self._ndock()

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

        # start mission
        data = self._api.mission(api_deck_id=api_deck_id, api_mission_id=api_mission_id)
        if data['api_result'] != 1:
            self._log.error('response error: {0}'.format(data['api_result_msg']))
            return False

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
        self._update_ndock()

        data = self._api.nyukyo(api_ship_id=api_ship_id, api_ndock_id=api_ndock_id, api_highspeed=api_highspeed)
        if data['api_result'] != 1:
            self._log.error('response error: {0}'.format(data['api_result_msg']))
            return False

        self._update_ndock()

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


class Mission(object):

    def __init__(self, client, event_loop):
        self._log = logging.getLogger('kcapi')
        self._client = client
        self._event_loop = event_loop
        self._decks = {}

    def start(self, api_deck_id, api_mission_id):
        if api_deck_id in self._decks:
            return

        self._log.debug('deck {0} start mission {1}'.format(api_deck_id, api_mission_id))

        # check if this deck is ready
        session = Session()
        deck = session.query(db.Deck).filter(db.Deck.api_id == api_deck_id).first()
        ms_complete_time = deck.mission_time
        if deck.mission_status <= 0:
            self._log.info('deck {0} is ready, start mission {1}'.format(api_deck_id, api_mission_id))
            ms_complete_time = self._start_mission(api_deck_id, api_mission_id)
            if ms_complete_time <= 0:
                return

        # do same work on done
        self._queue_next(ms_complete_time, api_deck_id, api_mission_id)

        self._log.debug('deck {0} start mission {1} ok'.format(api_deck_id, api_mission_id))

    def stop(self, api_deck_id):
        if api_deck_id not in self._decks:
            return

        token = self._decks[api_deck_id]
        del self._decks[api_deck_id]
        self._event_loop.remove_timeout(token)

    def _start_mission(self, api_deck_id, api_mission_id):
        # start next mission
        ok = self._client.start_mission(api_deck_id, api_mission_id)
        if not ok:
            self._log.error('deck {0} failed to start mission {1}'.format(api_deck_id, api_mission_id))
            return 0

        session = Session()
        deck = session.query(db.Deck).filter(db.Deck.api_id == api_deck_id).first()
        return deck.mission_time

    def _queue_next(self, ms_complete_time, api_deck_id, api_mission_id):
        # calculate time interval
        complete_time = ms_complete_time / 1000
        # queue next action
        token = self._event_loop.add_timeout(complete_time, lambda: self._on_done(api_deck_id, api_mission_id))
        self._decks[api_deck_id] = token

    def _on_done(self, api_deck_id, api_mission_id):
        if api_deck_id not in self._decks:
            return

        self._log.debug('deck {0} start mission {1}'.format(api_deck_id, api_mission_id))

        # start mission
        ms_complete_time = self._start_mission(api_deck_id, api_mission_id)
        if ms_complete_time <= 0:
            return
        # do same work on done
        self._queue_next(ms_complete_time, api_deck_id, api_mission_id)

        self._log.debug('deck {0} start mission {1} ok'.format(api_deck_id, api_mission_id))


class Nyukyo(object):

    def __init__(self, client, event_loop):
        self._log = logging.getLogger('kcapi')
        self._client = client
        self._event_loop = event_loop
        self._ndocks = {}

    def start(self):
        ships = self._client.get_wounded_ships()
        self._log.debug('nyukyo: {0}'.format(ships))

        session = Session()
        # query all ndocks
        ndocks = session.query(db.NDock)
        ships_index = 0
        for ndock in ndocks:
            if ships_index >= len(ships):
                break
            # if it is ready, repair a ship
            if ndock.api_complete_time == 0:
                # query all ships that need to repair
                ship_id = ships[ships_index]
                ships_index += 1
                ndock = self._nyukyo(api_ship_id=ship_id, api_ndock_id=ndock.api_id)

            # queue next ship if any
            self._queue_next(ndock.api_complete_time, ndock.api_id)

    def stop(self):
        for ndock_id, token in self._ndocks.iteritems():
            self._event_loop.remove_timeout(token)
        self._ndocks = {}

    def _nyukyo(self, api_ship_id, api_ndock_id):
        self._log.debug('nyukyo: ship {0}, ndock {1}'.format(api_ship_id, api_ndock_id))
        ok = self._client.nyukyo(api_ship_id=api_ship_id, api_ndock_id=api_ndock_id, api_highspeed=0)
        if not ok:
            return
        session = Session()
        ndock = session.query(db.NDock).filter(db.NDock.api_id == api_ndock_id).first()
        return ndock

    def _queue_next(self, ms_complete_time, api_ndock_id):
        # calculate time interval
        complete_time = ms_complete_time / 1000
        # queue next action
        token = self._event_loop.add_timeout(complete_time, lambda: self._on_done(api_ndock_id))
        self._ndocks[api_ndock_id] = token

    def _on_done(self, api_ndock_id):
        if api_ndock_id not in self._ndocks:
            return
        del self._ndocks[api_ndock_id]

        ships = self._client.get_wounded_ships()
        self._log.debug('nyukyo: {0}'.format(ships))
        if not ships:
            return

        ship_id = ships[0]
        ndock = self._nyukyo(api_ship_id=ship_id, api_ndock_id=api_ndock_id)
        if not ndock:
            return

        self._queue_next(ndock.api_complete_time, ndock.api_id)


def _api_port(member_id):
    seed = [1171, 1841, 2517, 3101, 4819, 5233, 6311, 7977, 8103, 9377, 1000]
    a = seed[10] + member_id % seed[10]
    b = (9999999999 - math.floor(_unix_time() / seed[10]) - member_id) * seed[member_id % 10]
    c = ''.join([str(_salt()) for i in range(4)])
    return '{}{}{}'.format(a, b, c)


def _unix_time():
    return math.floor(time.time() * 1000)


def _salt():
    return math.floor(random.random() * 10)

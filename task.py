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

import client
from client import Session
import db
import event


class Task(object):

    def __init__(self, io_loop):
        self._io_loop = io_loop
        self._client = client.Client()
        self._mission = _Mission(self._client, self._io_loop)
        self._nyukyo = _Nyukyo(self._client, self._io_loop)

    def setup_api(self, api_token, api_starttime):
        self._io_loop.add_callback(lambda: self._client.setup_api(api_token, api_starttime))

    def start_mission(self, api_deck_id, api_mission_id):
        self._io_loop.add_callback(lambda: self._mission.start(api_deck_id, api_mission_id))

    def stop_mission(self, api_deck_id):
        self._io_loop.add_callback(lambda: self._mission.stop(api_deck_id))

    def start_nyukyo(self):
        self._io_loop.add_callback(lambda: self._nyukyo.start())

    def stop_nyukyo(self):
        self._io_loop.add_callback(lambda: self._nyukyo.stop())


class _Mission(object):

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

        event.mission_started.emit('deck {0} start mission {1}'.format(api_deck_id, api_mission_id))

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

        # self._client.check_mission_result(api_deck_id)

        self._log.debug('deck {0} start mission {1}'.format(api_deck_id, api_mission_id))

        # start mission
        ms_complete_time = self._start_mission(api_deck_id, api_mission_id)
        if ms_complete_time <= 0:
            return
        # do same work on done
        self._queue_next(ms_complete_time, api_deck_id, api_mission_id)

        self._log.debug('deck {0} start mission {1} ok'.format(api_deck_id, api_mission_id))


class _Nyukyo(object):

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

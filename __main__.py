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
import random
import sys
from threading import Thread

from tornado.ioloop import IOLoop
# from tornado.web import Application, RequestHandler
# from tornadio2 import SocketConnection, TornadioRouter
# import tornado

import event
import task
import client


def setup_logger():
    # setup logger
    logger = logging.getLogger('kcapi')
    logger.setLevel(logging.DEBUG)
    formater = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add file handler
    handler = logging.FileHandler('/tmp/kcapi.log')
    handler.setFormatter(formater)
    logger.addHandler(handler)
    # add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formater)
    logger.addHandler(handler)


# class RouterConnection(SocketConnection):

#     @classmethod
#     def on_api_started(cls, *args, **kwargs):
#         cls.emit_to_all('api_started', **kwargs['data'])

#     @classmethod
#     def on_mission_started(cls, msg):
#         cls.send_to_all(msg)

#     @classmethod
#     def on_mission_result(cls, api_deck_id, api_clear_result):
#         cls.emit_to_all('mission_result', api_deck_id=api_deck_id, api_clear_result=api_clear_result)


# class IndexHandler(RequestHandler):

#     def get(self):
#         self.render('index.html')


# class StartHandler(RequestHandler):

#     triggered = event.Signal()

#     def post(self):
#         api_token = self.get_argument('api_token')
#         api_starttime = self.get_argument('api_starttime')
#         self.triggered.emit(api_token, api_starttime)


# class StartMissionHandler(RequestHandler):

#     triggered = event.Signal()

#     def post(self):
#         api_deck_id = self.get_argument('api_deck_id')
#         api_mission_id = self.get_argument('api_mission_id')
#         self.triggered.emit(api_deck_id, api_mission_id)


def main(args=None):
    if args is None:
        args = sys.argv

    setup_logger()

    # router = TornadioRouter(RouterConnection)

    # bg_loop = IOLoop()
    # bg_thread = Thread(target=lambda: bg_loop.start())
    # bg_task = task.Task(bg_loop)

    # application = Application(
    #     router.apply_routes([
    #         (r"/", IndexHandler),
    #         (r"/start", StartHandler),
    #         (r"/start_mission", StartMissionHandler),
    #     ]),
    #     debug=True,
    # )

    # application.listen(8000)

    # StartHandler.triggered.connect(bg_task.setup_api)
    # StartMissionHandler.triggered.connect(bg_task.start_mission)
    # event.api_started.connect(RouterConnection.on_api_started)
    # event.mission_started.connect(RouterConnection.on_mission_started)
    # event.mission_result.connect(RouterConnection.on_mission_result)

    # try:
    #     bg_thread.start()
    #     IOLoop.instance().start()
    # except KeyboardInterrupt:
    #     bg_loop.stop()
    #     IOLoop.instance().stop()

    # api_token = args[1]

    client_ = client.Client()
    client_.setup_api()
    event_loop = IOLoop()
    # event_loop = task.EventLoop()

    mission = task._Mission(client=client_, event_loop=event_loop)
    mission.start(api_deck_id=2, api_mission_id=5)
    mission.start(api_deck_id=3, api_mission_id=21)
    mission.start(api_deck_id=4, api_mission_id=38)

    nyukyo = task._Nyukyo(client=client_, event_loop=event_loop)
    nyukyo.start()

    event_loop.start()

    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

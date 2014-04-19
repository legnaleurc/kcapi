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


import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


_Base = declarative_base()


# 艦娘カテログ
class ShipType(_Base):

    __tablename__ = 'ship_type'

    api_id = sql.Column(sql.Integer, primary_key=True)
    api_sortno = sql.Column(sql.Integer)
    api_name = sql.Column(sql.String)
    api_yomi = sql.Column(sql.String)
    api_stype = sql.Column(sql.Integer)
    api_ctype = sql.Column(sql.Integer)
    api_cnum = sql.Column(sql.Integer)
    api_enqflg = sql.Column(sql.String)
    api_afterlv = sql.Column(sql.Integer)
    api_aftershipid = sql.Column(sql.String)
    api_fuel_max = sql.Column(sql.Integer)
    api_bull_max = sql.Column(sql.Integer)
    # 以下略。戦闘や建造はやらない

    ships = relationship('Ship', backref='ship_type')


class Deck(_Base):

    __tablename__ = 'deck'

    api_id = sql.Column(sql.Integer, primary_key=True)
    api_name = sql.Column(sql.String)
    api_ship = relationship('Ship', backref='deck')

    mission_id = sql.Column(sql.Integer)
    mission_time = sql.Column(sql.Integer)


class Ship(_Base):

    __tablename__ = 'ship'

    api_id = sql.Column(sql.Integer, primary_key=True)
    api_sortno = sql.Column(sql.Integer)
    api_ship_id = sql.Column(
        sql.Integer,
        sql.ForeignKey('ship_type.api_id'),
        nullable=False)
    api_lv = sql.Column(sql.Integer)
    api_nowhp = sql.Column(sql.Integer)
    api_maxhp = sql.Column(sql.Integer)
    api_ndock_time = sql.Column(sql.Integer)
    api_fuel = sql.Column(sql.Integer)
    api_bull = sql.Column(sql.Integer)

    deck_id = sql.Column(sql.Integer, sql.ForeignKey('deck.api_id'))


def initialize(echo=False):
    engine = sql.create_engine('sqlite:///:memory:', echo=echo)
    _Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

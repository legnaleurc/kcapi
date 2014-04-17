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
    # 以下略。戦闘や建造はやらない


class Deck(_Base):

    __tablename__ = 'deck'

    api_id = sql.Column(sql.Integer, primary_key=True)
    api_name = sql.Column(sql.String)
    api_ship = relationship('Ship', backref='deck')


class Ship(_Base):

    __tablename__ = 'ship'

    api_id = sql.Column(sql.Integer, primary_key=True)
    api_sortno = sql.Column(sql.Integer)
    api_ship_id = sql.Column(sql.Integer, sql.ForeignKey('ship_type.api_id'), nullable=False)
    api_lv = sql.Column(sql.Integer)
    api_nowhp = sql.Column(sql.Integer)
    api_maxhp = sql.Column(sql.Integer)
    api_ndock_time = sql.Column(sql.Integer)


def initialize():
    engine = sql.create_engine('sqlite:///:memory:', echo=True)
    _Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

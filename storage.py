import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine('sqlite:///storage.db?check_same_thread=False')
Session = sessionmaker(bind=engine)
session = Session()

BaseTableClass = declarative_base(bind=engine)


class Storage(BaseTableClass):
    __tablename__ = 'storage'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    user_message = Column(String)
    bot_message = Column(String)
    sending_time = Column(DateTime, default=datetime.datetime.now())

    @classmethod
    def get_history_by_user_id(cls, us_id):
        return session.query(Storage).filter(
            us_id == Storage.user_id
        ).order_by(Storage.sending_time).all()

    @classmethod
    def create_history(cls, us_id, us_mess, bot_mess):
        session.add(Storage(
            user_id=us_id,
            user_message=us_mess,
            bot_message=bot_mess
        ))
        session.commit()

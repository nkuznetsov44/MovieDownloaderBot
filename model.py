from sqlalchemy import Column, ForeignKey, Integer, Boolean, String, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class CardFill(Base):
    __tablename__ = 'card_fill'

    fill_id = Column('fill_id', Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('telegram_user.user_id'))
    user = relationship("TelegramUser", back_populates="card_fills")
    fill_date = Column('fill_date', DateTime)
    amount = Column('amount', Float)

    def __repr__(self) -> str:
        return (
            f'{super().__repr__()}: '
            f'{{"fill_id": {self.fill_id}, "user": {self.user}, '
            f'"fill_date": {self.fill_date}, "amount": {self.amount}}}'
        )


class TelegramUser(Base):
    __tablename__ = 'telegram_user'

    user_id = Column('user_id', Integer, primary_key=True)
    is_bot = Column('is_bot', Boolean)
    first_name = Column('first_name', String, nullable=True)
    last_name = Column('last_name', String, nullable=True)
    username = Column('username', String, nullable=True)
    language_code = Column('language_code', String, nullable=True)
    card_fills = relationship("CardFill")

    def __repr__(self) -> str:
        return (
            f'{super().__repr__()}: '
            f'{{"user_id": {self.user_id}, "username": {self.username}}}'
        )

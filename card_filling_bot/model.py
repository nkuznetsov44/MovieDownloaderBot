from typing import List
import re
from sqlalchemy import Column, ForeignKey, Integer, Boolean, String, DateTime, Float, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class CardFill(Base):
    __tablename__ = 'card_fill'

    fill_id = Column('fill_id', Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('telegram_user.user_id'))
    user = relationship('TelegramUser', back_populates='card_fills')
    fill_date = Column('fill_date', DateTime)
    amount = Column('amount', Float)
    description = Column('description', String, nullable=True)
    category_code = Column(String, ForeignKey('category.code'))
    category = relationship('Category', back_populates='card_fills', lazy='subquery')

    def __repr__(self) -> str:
        return (
            f'{super().__repr__()}: '
            f'<"fill_id": {self.fill_id}, "user": {self.user}, '
            f'"fill_date": {self.fill_date}, "amount": {self.amount}, '
            f'"description": {self.description}, "category": {self.category}>'
        )


class TelegramUser(Base):
    __tablename__ = 'telegram_user'

    user_id = Column('user_id', Integer, primary_key=True)
    is_bot = Column('is_bot', Boolean)
    first_name = Column('first_name', String, nullable=True)
    last_name = Column('last_name', String, nullable=True)
    username = Column('username', String, nullable=True)
    language_code = Column('language_code', String, nullable=True)
    card_fills = relationship('CardFill')

    def __repr__(self) -> str:
        return (
            f'{super().__repr__()}: '
            f'<"user_id": {self.user_id}, "username": {self.username}>'
        )


class Category(Base):
    __tablename__ = 'category'

    code = Column('code', String, primary_key=True)
    name = Column('name', String)
    aliases = Column('aliases', String)
    proportion = Column('proportion', Numeric)
    card_fills = relationship('CardFill')

    def __repr__(self) -> str:
        return f'{super().__repr__()}: <"name": {self.name}>'

    def get_aliases(self) -> List[str]:
        return self.aliases.split(',')

    def add_alias(self, alias: str) -> None:
        aliases = self.get_aliases()
        aliases.append(alias)
        self.aliases = ','.join(aliases)

    def fill_fits_category(self, fill_description: str) -> bool:
        if self.code == 'OTHER':
            return False
        aliases_re = [re.compile(alias, re.IGNORECASE) for alias in self.get_aliases()]
        return any(pattern.match(fill_description) for pattern in aliases_re)

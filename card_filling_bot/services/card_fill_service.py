from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from model import CardFill, Category
from dto.dto import FillDto

if TYPE_CHECKING:
    from datetime import datetime


class CardFillServiceSettings:
    def __init__(
        self,
        mysql_user: str,
        mysql_password: str,
        mysql_host: str,
        mysql_database: str,
        logger: Any
    ) -> None:
        self._mysql_user = mysql_user
        self._mysql_password = mysql_password
        self._mysql_host = mysql_host
        self._mysql_database = mysql_database
        self._logger = logger

    @property
    def mysql_user(self) -> str:
        return self._mysql_user

    @property
    def mysql_password(self) -> str:
        return self._mysql_password

    @property
    def mysql_host(self) -> str:
        return self._mysql_host

    @property
    def mysql_database(self) -> str:
        return self._mysql_database

    @property
    def logger(self) -> Any:
        return self._logger


class CardFillService:
    def __init__(self, settings: CardFillServiceSettings):
        self.logger = settings.logger
        database_uri = (
            f'mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}'
            f'@{settings.mysql_host}/{settings.mysql_database}'
        )
        self.logger.info(
            f'Creating database engine {settings.mysql_database}@{settings.mysql_host} as {settings.mysql_user}'
        )
        self._db_engine = create_engine(database_uri, pool_recycle=3600)
        self.DbSession = scoped_session(sessionmaker(bind=self._db_engine))

    def handle_new_fill(self, fill: FillDto, from_user_id: int, fill_date: 'datetime') -> FillDto:
        db_session = self.DbSession()
        try:
            fill_category = db_session.query(Category).get('OTHER')
            try:
                fill_category: Category = next(
                    filter(lambda cat: cat.fill_fits_category(fill.description), db_session.query(Category).all())
                )
            except StopIteration:
                pass
            fill.category_name = fill_category.name

            # TODO: BEGIN TRAN
            card_fill = CardFill(
                user_id=from_user_id,
                fill_date=fill_date,
                amount=float(fill.amount),
                description=fill.description,
                category_code=fill_category.code,
            )
            db_session.add(card_fill)
            db_session.commit()
            fill.id = card_fill.fill_id
            return fill
            # TODO: END TRAN
        finally:
            self.DbSession.remove()

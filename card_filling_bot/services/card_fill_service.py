from typing import Any, List, Dict, TYPE_CHECKING
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from model import CardFill, Category, TelegramUser
from dto.dto import Month, FillDto, CategoryDto, UserDto, UserSumOverPeriodDto

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

    def handle_new_fill(self, fill: FillDto, from_user: UserDto) -> FillDto:
        db_session = self.DbSession()
        try:
            user = db_session.query(TelegramUser).get(from_user.id)
            if not user:
                new_user = TelegramUser(
                    user_id=from_user.id,
                    is_bot=from_user.is_bot,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                    username=from_user.username,
                    language_code=from_user.language_code,
                )
                db_session.add(new_user)
                user = new_user
                self.logger.info(f'Create new user {user}')

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
                user_id=user.user_id,
                fill_date=fill.fill_date,
                amount=float(fill.amount),
                description=fill.description,
                category_code=fill_category.code,
            )
            db_session.add(card_fill)
            db_session.commit()
            fill.id = card_fill.fill_id
            self.logger.info(f'Save fill {fill}')
            return fill
            # TODO: END TRAN
        finally:
            self.DbSession.remove()

    def get_fill_by_id(self, fill_id: int) -> FillDto:
        db_session = self.DbSession()
        try:
            return FillDto.from_model(db_session.query(CardFill).get(fill_id))
        finally:
            self.DbSession.remove()

    def list_categories(self) -> List[CategoryDto]:
        db_session = self.DbSession()
        try:
            return [CategoryDto(cat.code, cat.name, cat.get_aliases()) for cat in db_session.query(Category).all()]
        finally:
            self.DbSession.remove()

    def change_category_for_fill(self, fill_id: int, target_category_code: str) -> FillDto:
        db_session = self.DbSession()
        try:
            fill = db_session.query(CardFill).get(fill_id)
            category = db_session.query(Category).get(target_category_code)
            old_category = fill.category
            fill.category_code = category.code
            if old_category.code == 'OTHER' and fill.description:
                category.add_alias(fill.description.lower())
                self.logger.info(f'Add alias {fill.description} to category {category}')
            db_session.commit()
            self.logger.info(f'Change category for fill {fill} to {category}')
            return FillDto.from_model(fill)
        finally:
            self.DbSession.remove()

    def get_monthly_report(self, months: List[Month], year: int) -> Dict[Month, List[UserSumOverPeriodDto]]:
        db_session = self.DbSession()
        try:
            per_month_data: Dict[Month, List[UserSumOverPeriodDto]] = {}
            for month in months:
                res = db_session.execute(
                    'select username, category_name, amount from monthly_report_by_category '
                    f'where month_num = {month.value} and fill_year = {year}'
                ).fetchall()
                per_month_data[month] = UserSumOverPeriodDto.from_rows(res)
            return per_month_data
        finally:
            self.DbSession.remove()

    def get_user_fills_in_months(self, user: UserDto, months: List[Month], year: int) -> List[FillDto]:
        db_session = self.DbSession()
        try:
            user_fills = [FillDto.from_model(fill) for fill in db_session.query(TelegramUser).get(user.id).card_fills]
            month_numbers = [month.value for month in months]
            return list(
                filter(
                    lambda cf: cf.fill_date.month in month_numbers and cf.fill_date.year == year,
                    user_fills
                )
            )
        finally:
            self.DbSession.remove()

    def get_total_report(self) -> List[UserSumOverPeriodDto]:
        db_session = self.DbSession()
        try:
            query = db_session.execute(
                'select u.username, cat.name, sum(amount) as total_amount '
                'from card_fill cf '
                'join telegram_user u on cf.user_id = u.user_id'
                'join category cat on cf.category_code = cat.code '
                'group by u.username, cat.name'
            ).fetchall()
            res = db_session.execute(query)
            return UserSumOverPeriodDto.from_rows(res)
        finally:
            self.DbSession.remove()

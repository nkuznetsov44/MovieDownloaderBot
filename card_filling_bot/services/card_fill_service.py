from typing import Any, List, Dict, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from model import CardFill, Category, TelegramUser
from dto.dto import Month, FillDto, CategoryDto, UserDto, UserSumOverPeriodDto, ProportionOverPeriodDto

if TYPE_CHECKING:
    from datetime import datetime
    from logging import Logger


@dataclass(frozen=True)
class CardFillServiceSettings:
    mysql_user: str
    mysql_password: str
    mysql_host: str
    mysql_database: str
    minor_proportion_user_id: int
    major_proportion_user_id: int
    logger: 'Logger'


def proportion_to_fraction(proportion: float) -> float:
    """Considering total consists of two parts.
    Proportion is the proportion of two parts.
    Fraction is the fraction of the minor part in total.

    """
    return proportion / (1 + proportion)


def fraction_to_proportion(fraction: float) -> float:
    """Considering total consists of two parts.
    Proportion is the proportion of two parts.
    Fraction is the fraction of the minor part in total.

    """
    return fraction / (1 - fraction)


def merge_dicts_sum(*dicts: Dict[Any, float]) -> Dict[Any, float]:
    ret = defaultdict(float)
    for d in dicts:
        for k, v in d.items():
            ret[k] += v
    return dict(ret)


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

        db_session = self.DbSession()
        try:
            self.minor_proportion_user = db_session.query(TelegramUser).get(settings.minor_proportion_user_id)
            self.major_proportion_user = db_session.query(TelegramUser).get(settings.major_proportion_user_id)
        finally:
            self.DbSession.remove()

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

    def get_monthly_report(
        self, months: List[Month], year: int
    ) -> Dict[Month, Tuple[List[UserSumOverPeriodDto], ProportionOverPeriodDto]]:
        db_session = self.DbSession()
        try:
            per_month_data: Dict[Month, Tuple[List[UserSumOverPeriodDto], ProportionOverPeriodDto]] = {}
            for month in months:
                res = db_session.execute(
                    'select username, category_name, amount, proportion from monthly_report_by_category '
                    f'where month_num = {month.value} and fill_year = {year}'
                ).fetchall()
                sums_over_period = UserSumOverPeriodDto.from_rows(res)

                try:
                    minor_user_data = next(filter(
                        lambda usop: usop.username == self.minor_proportion_user.username, sums_over_period
                    ))
                except StopIteration:
                    minor_user_data = None

                try:
                    major_user_data = next(filter(
                        lambda usop: usop.username == self.major_proportion_user.username, sums_over_period
                    ))
                except StopIteration:
                    major_user_data = None

                if minor_user_data is None or major_user_data is None:
                    per_month_data[month] = (sums_over_period, ProportionOverPeriodDto(None, None))
                else:
                    proportion_actual = self._calc_proportion_actual(minor_user_data, major_user_data)
                    proportion_target = self._calc_proportion_target(minor_user_data, major_user_data)
                    per_month_data[month] = (
                        sums_over_period, ProportionOverPeriodDto(proportion_target, proportion_actual)
                    )

            return per_month_data
        finally:
            self.DbSession.remove()

    @staticmethod
    def _calc_proportion_actual(minor_user_data: UserSumOverPeriodDto, major_user_data: UserSumOverPeriodDto) -> float:
        """fraction_actual = sum(categories for minor_user) / sum(total)"""
        return fraction_to_proportion(minor_user_data.amount / (minor_user_data.amount + major_user_data.amount))

    @staticmethod
    def _calc_proportion_target(minor_user_data: UserSumOverPeriodDto, major_user_data: UserSumOverPeriodDto) -> float:
        """fraction_target = sum(category_i * fraction_i) / sum(category_i)"""
        minor_user_by_category_weighted = {
            category: amount * proportion_to_fraction(proportion)
            for category, (amount, proportion) in minor_user_data.by_category.items()
        }
        major_user_by_category_weighted = {
            category: amount * proportion_to_fraction(proportion)
            for category, (amount, proportion) in major_user_data.by_category.items()
        }
        total_by_category_weighted = merge_dicts_sum(minor_user_by_category_weighted, major_user_by_category_weighted)

        minor_user_by_category = {category: amount for category, (amount, _) in minor_user_data.by_category.items()}
        major_user_by_category = {category: amount for category, (amount, _) in major_user_data.by_category.items()}
        total_by_category = merge_dicts_sum(minor_user_by_category, major_user_by_category)

        return fraction_to_proportion(sum(total_by_category_weighted.values()) / sum(total_by_category.values()))

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
            res = db_session.execute(
                'select u.username, cat.name, sum(amount), cat.proportion as total_amount '
                'from card_fill cf '
                'join telegram_user u on cf.user_id = u.user_id '
                'join category cat on cf.category_code = cat.code '
                'group by u.username, cat.name, cat.proportion'
            ).fetchall()
            return UserSumOverPeriodDto.from_rows(res)
        finally:
            self.DbSession.remove()

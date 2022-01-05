from typing import Optional, List, Dict, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from telegramapi.types import User as TelegramapiUser
from model import CardFill

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


class Month(Enum):
    january = 1
    february = 2
    march = 3
    april = 4
    may = 5
    june = 6
    july = 7
    august = 8
    september = 9
    october = 10
    november = 11
    december = 12


@dataclass
class FillDto:
    id: Optional[int]
    user_id: int
    fill_date: 'datetime'
    amount: str
    description: Optional[str]
    category_name: Optional[str]

    @staticmethod
    def from_model(fill: CardFill) -> 'FillDto':
        return FillDto(
            id=fill.fill_id,
            user_id=fill.user_id,
            fill_date=fill.fill_date,
            amount=fill.amount,
            description=fill.description,
            category_name=fill.category.name
        )


@dataclass
class CategoryDto:
    code: str
    name: str
    aliases: List[str]


@dataclass
class UserDto:
    id: int
    is_bot: bool
    first_name: str
    last_name: str
    username: str
    language_code: str

    @staticmethod
    def from_telegramapi(telegramapi_user: TelegramapiUser) -> 'UserDto':
        return UserDto(
            id=telegramapi_user.user_id,
            is_bot=telegramapi_user.is_bot,
            first_name=telegramapi_user.first_name,
            last_name=telegramapi_user.last_name,
            username=telegramapi_user.username,
            language_code=telegramapi_user.language_code
        )


@dataclass
class UserSumOverPeriodDto:
    username: str
    amount: float
    by_category: Optional[Dict[str, Tuple[float, float]]]  # category -> (amount, proportion)

    @staticmethod
    def from_rows(rows: List[Tuple[str, str, float, 'Decimal']]) -> List['UserSumOverPeriodDto']:
        """[('kuznetsov_na', 'Ð´Ñ€ÑƒÐ³Ð¾Ðµ', 1000.0, 0.80), ('kuznetsov_na', 'ÐµÐ´Ð°', 102.0, 1.00)]"""
        tmp: Dict[str, Dict[str, Tuple[float, float]]] = {}  # username -> (category -> (amount, proportion))
        for username, category, amount, proportion in rows:
            by_category = tmp.get(username)
            if not by_category:
                tmp[username] = by_category = {}
            by_category[category] = (amount, float(proportion))

        res: List['UserSumOverPeriodDto'] = []
        for username, by_category in tmp.items():
            # by_category: Dict[str, Tuple[float, float]] category -> (amount, proportion)
            amount = sum([amount for amount, _ in by_category.values()])
            res.append(UserSumOverPeriodDto(username, amount, by_category))
        return res

    def __repr__(self):
        return (
            f'UserSumOverPeriodDto<username: {self.username}, amount: {self.amount}, by_category: {self.by_category}>'
        )


@dataclass
class ProportionOverPeriodDto:
    proportion_target: Optional[float]
    proportion_actual: Optional[float]

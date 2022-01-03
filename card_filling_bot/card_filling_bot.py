from typing import List, Dict, Any, Optional
from enum import Enum
import re
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import create_engine, func
from sqlalchemy.orm import scoped_session, sessionmaker
from telegramapi.bot import Bot, message_handler, callback_query_handler
from telegramapi.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, User as TelegramApiUser
from model import TelegramUser, CardFill, Category


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


months_regexps = {
    Month.january: r'январ[яеь]',
    Month.february: r'феврал[яеь]',
    Month.march: r'март[ае]?',
    Month.april: r'апрел[яеь]',
    Month.may: r'ма[йяе]',
    Month.june: r'июн[яеь]',
    Month.july: r'июл[яеь]',
    Month.august: r'август[ае]?',
    Month.september: r'сентябр[яеь]',
    Month.october: r'октябр[яеь]',
    Month.november: r'ноябр[яеь]',
    Month.december: r'декабр[яеь]',
}


months_names = {
    Month.january: 'Январь',
    Month.february: 'Февраль',
    Month.march: 'Март',
    Month.april: 'Апрель',
    Month.may: 'Май',
    Month.june: 'Июнь',
    Month.july: 'Июль',
    Month.august: 'Август',
    Month.september: 'Сентябрь',
    Month.october: 'Октябрь',
    Month.november: 'Ноябрь',
    Month.december: 'Декабрь'
}


class CardFillingBotSettings:
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

@dataclass
class UserSumOverPeriodDto:
    username: str
    amount: float


@dataclass
class FillDto:
    id: Optional[int]
    amount: str
    description: Optional[str]
    category_name: Optional[str]


class CardFillingBot(Bot):
    def __init__(self, token: str, settings: CardFillingBotSettings) -> None:
        super().__init__(token)
        self._settings = settings
        self.logger = settings.logger
        self.logger.info(f'Creating database engine {settings.mysql_database}@{settings.mysql_host} as {settings.mysql_user}')
        self._db_engine = create_engine(self._SQLALCHEMY_DATABASE_URI, pool_recycle=3600)
        self.DbSession = scoped_session(sessionmaker(bind=self._db_engine))
        self._numbers_regexp = re.compile(r'[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?')

    @property
    def _SQLALCHEMY_DATABASE_URI(self) -> str:
        return f'mysql+pymysql://{self._settings.mysql_user}:{self._settings.mysql_password}@{self._settings.mysql_host}/{self._settings.mysql_database}'

    def _try_parse_fill_message_text(self, message_text: str) -> Optional[FillDto]:
        """Returns FillDto on successful parse or None if no fill was found."""
        cnt = 0
        for number_match in re.finditer(self._numbers_regexp, message_text):
            cnt += 1
            amount = number_match.group()
            before_phrase = message_text[:number_match.start()].strip()
            after_phrase = message_text[number_match.end():].strip()
            if len(before_phrase) > 0 and len(after_phrase) > 0:
                description = ' '.join([before_phrase, after_phrase])
            else:
                description = before_phrase + after_phrase

        if cnt == 1:
            return FillDto(None, amount, description, None)
        return None

    def _try_parse_months_message_text(self, message_text: str) -> List[Month]:
        """Returns list of months on successful parse or empty list if no months were found."""
        results: List[Month] = []
        if message_text:
            for word in message_text.split(' '):
                for month, month_re in months_regexps.items():
                    result = re.search(month_re, word, re.IGNORECASE)
                    if result:
                        results.append(month)
        return results

    def _reply_to_fill_message(self, message: Message, fill: FillDto) -> None:
        reply_text = f'Принято {fill.amount}р. от @{message.from_user.username}'
        if fill.description:
            reply_text += f': {fill.description}'
        reply_text += f', категория: {fill.category_name}.'

        change_category = InlineKeyboardButton(text='Сменить категорию', callback_data=f'show_category{fill.id}')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[change_category]])

        self.send_message(
            chat_id=message.chat.chat_id,
            text=reply_text,
            reply_markup=keyboard
        )

    @callback_query_handler(accepted_data=['show_category'])
    def show_category(self, callback_query: CallbackQuery) -> None:
        fill_id = callback_query.data.replace('show_category', '')
        try:
            db_session = self.DbSession()
            fill = db_session.query(CardFill).get(fill_id)
            keyboard_buttons = []
            for cat in db_session.query(Category).all():
                keyboard_buttons.append([InlineKeyboardButton(text=cat.name, callback_data=f'change_category{cat.code}/{fill_id}')])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            reply_text = f'Выберите категорию для пополнения {fill.amount}р.'
            if fill.description:
                reply_text += f' ({fill.description})'
            self.send_message(
                chat_id=callback_query.message.chat.chat_id,
                text=reply_text,
                reply_markup=keyboard
            )
        finally:
            self.DbSession.remove()

    def _reply_to_change_category_request(self, callback_query: CallbackQuery, fill: FillDto) -> None:
        reply_text = f'Категория пополнения {fill.amount}р.'
        if fill.description:
            reply_text += f' ({fill.description})'
        reply_text += f' изменена на "{fill.category_name}".'

        change_category = InlineKeyboardButton(text='Сменить категорию', callback_data=f'show_category{fill.id}')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[change_category]])

        self.send_message(
            chat_id=callback_query.message.chat.chat_id,
            text=reply_text,
            reply_markup=keyboard
        )

    @callback_query_handler(accepted_data=['change_category'])
    def change_category(self, callback_query: CallbackQuery) -> None:
        category_code, fill_id = callback_query.data.replace('change_category', '').split('/')
        db_session = self.DbSession()
        try:
            fill = db_session.query(CardFill).get(int(fill_id))
            old_category = fill.category
            fill.category_code = category_code
            self.logger.info(f'Changed category for fill {fill_id} to {category_code}')
            # saving description as category alias if not defined
            if old_category.code == 'OTHER' and fill.description:
                category = db_session.query(Category).get(category_code)
                category.add_alias(fill.description)
                self.logger.info(f'Added alias {fill_dto.description} to category {category_code}')
            db_session.commit()
            fill_dto = FillDto(fill.fill_id, fill.amount, fill.description, fill.category.name)
        finally:
            self.DbSession.remove()
        self._reply_to_change_category_request(callback_query, fill_dto)

    def _reply_to_months_message(self, message: Message, months: List[Month]) -> None:
        my = InlineKeyboardButton(text='Мои пополнения', callback_data='my')
        stat = InlineKeyboardButton(text='Отчет за месяцы', callback_data='stat')
        total = InlineKeyboardButton(text='Сумма всех пополнений', callback_data='total')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[my], [stat], [total]])
        self.send_message(
            chat_id=message.chat.chat_id,
            text=f'Выбраны месяцы: {", ".join(map(months_names.get, months))}. Какая информация интересует?',
            reply_markup=keyboard
        )

    def _reply_error(self, message: Message) -> None:
        self.send_message(
            chat_id=message.chat.chat_id,
            text='Ошибка добавления суммы пополнения.'
        )

    @message_handler()
    def basic_message_handler(self, message: Message) -> None:
        if message.text:
            self.logger.info(f'Parsing text {message.text}')
            fill = self._try_parse_fill_message_text(message.text)
            months = self._try_parse_months_message_text(message.text)

            if fill:
                self.logger.info(f'Found fill {fill}')
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
                        user_id=message.from_user.user_id,
                        fill_date=datetime.fromtimestamp(message.date),
                        amount=float(fill.amount),
                        description=fill.description,
                        category_code=fill_category.code,
                    )
                    db_session.add(card_fill)
                    db_session.commit()
                    fill.id = card_fill.fill_id
                    self._reply_to_fill_message(message, fill)
                    # TODO: END TRAN
                except Exception:
                    self._reply_error(message)
                    raise
                finally:
                    self.DbSession.remove()
            elif months:
                self.logger.info(f'Found months {months}')
                self._reply_to_months_message(message, months)
            else:
                self._reply_error(message)

    def _reply_to_my_fills_request(
        self,
        callback_query: CallbackQuery,
        from_user: TelegramUser,
        months: List[Month],
        fills: List[CardFill]
    ) -> None:
        m_names = ', '.join(map(months_names.get, months))
        if len(fills) == 0:
            text = f'Не было пополнений в {m_names}.'
        else:
            text = (
                f'Пополнения @{from_user.username} за {m_names}:\n' +
                '\n'.join([f'{fill.fill_date}: {fill.amount} {fill.description} {fill.category.name}' for fill in fills])
            )
        self.send_message(chat_id=callback_query.message.chat.chat_id, text=text)

    def _create_new_user(self, telegramapi_user: TelegramApiUser, db_session: Any) -> TelegramUser:
        self.logger.info(f'Creating new user {telegramapi_user}')
        tg_user = TelegramUser(
            user_id=telegramapi_user.user_id,
            is_bot=telegramapi_user.is_bot,
            first_name=telegramapi_user.first_name,
            last_name=telegramapi_user.last_name,
            username=telegramapi_user.username,
            language_code=telegramapi_user.language_code
        )
        db_session.add(tg_user)
        db_session.commit()
        return tg_user

    @callback_query_handler(accepted_data=['my'])
    def my_fills(self, callback_query: CallbackQuery) -> None:
        months = self._try_parse_months_message_text(callback_query.message.text)

        db_session = self.DbSession()
        try:
            from_user = db_session.query(TelegramUser).get(callback_query.from_user.user_id)
            if not from_user:
                from_user = self._create_new_user(callback_query.from_user, db_session)
            m_values = [month.value for month in months]
            filtered_fills = list(filter(lambda cf: cf.fill_date.month in m_values and cf.fill_date.year == datetime.now().year, from_user.card_fills))
        finally:
            self.DbSession.remove()
        
        self._reply_to_my_fills_request(callback_query, from_user, months, filtered_fills)

    def _reply_to_per_month_request(self, callback_query: CallbackQuery, data: Dict[Month, List[UserSumOverPeriodDto]], year: int) -> None:
        message_text = ''
        for month, monthly_data in data.items():
            message_text = message_text + f'*{months_names[month]} {year}:*\n' + '\n'.join(f'@{user_sum_per_month.username}: {user_sum_per_month.amount}' for user_sum_per_month in monthly_data) + '\n\n'
        message_text = message_text.replace('_', '\\_').replace('.', '\\.')
        if year == datetime.now().year:
            previous_year = InlineKeyboardButton(text='Предыдущий год', callback_data='previous_year')
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[previous_year]])
            self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text, parse_mode=ParseMode.MarkdownV2, reply_markup=keyboard)
        else:
            self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text, parse_mode=ParseMode.MarkdownV2)

    @callback_query_handler(accepted_data=['stat'])
    def per_month_current_year(self, callback_query: CallbackQuery) -> None:
        self.per_month(callback_query)

    @callback_query_handler(accepted_data=['previous_year'])
    def per_month_previous_year(self, callback_query: CallbackQuery) -> None:
        previous_year = datetime.now().year - 1
        self.per_month(callback_query, year=previous_year)

    def per_month(self, callback_query: CallbackQuery, year: int = None) -> None:
        year = year or datetime.now().year
        months = self._try_parse_months_message_text(callback_query.message.text)
        
        db_session = self.DbSession()
        try:
            per_month_data: Dict[Month, List[UserSumOverPeriodDto]] = {}
            for month in months:
                res = db_session.execute(
                    f'select username, amount from monthly_report where month_num = {month.value} and fill_year = {year}'
                ).fetchall()
                per_month_data[month] = [UserSumOverPeriodDto(*row) for row in res]
        finally:
            self.DbSession.remove()
        
        self._reply_to_per_month_request(callback_query, per_month_data, year=year)

    def _reply_to_total_request(self, callback_query: CallbackQuery, data: List[UserSumOverPeriodDto]) -> None:
        message_text = '\n'.join(f'@{user_sum_total.username}: {user_sum_total.amount}' for user_sum_total in data)
        self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text)

    @callback_query_handler(accepted_data=['total'])
    def total(self, callback_query: CallbackQuery) -> None:
        db_session = self.DbSession()
        try:
            query = db_session.query(
                TelegramUser.username,
                func.sum(CardFill.amount).label('total_amount')
            ).join(CardFill).group_by(TelegramUser.username)
            res = db_session.execute(query)
            total_data = [UserSumOverPeriodDto(*row) for row in res]
        finally:
            self.DbSession.remove()

        self._reply_to_total_request(callback_query, total_data)

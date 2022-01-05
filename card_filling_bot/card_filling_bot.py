from typing import List, Dict, Any
from datetime import datetime
from telegramapi.bot import Bot, message_handler, callback_query_handler
from telegramapi.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from dto.dto import Month, FillDto, CategoryDto, UserDto, UserSumOverPeriodDto
from message_parsers import IParsedMessage
from message_parsers.month_message_parser import Month, MonthMessageParser
from message_parsers.fill_message_parser import FillMessageParser
from services.card_fill_service import CardFillService, CardFillServiceSettings


month_names = {
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


class CardFillingBot(Bot):
    def __init__(self, token: str, settings: CardFillingBotSettings) -> None:
        super().__init__(token)
        self.logger = settings.logger
        card_fill_service_settings = CardFillServiceSettings(
            settings.mysql_user, settings.mysql_password, settings.mysql_host, settings.mysql_database, settings.logger
        )
        self.card_fill_service = CardFillService(card_fill_service_settings)

    @callback_query_handler(accepted_data=['show_category'])
    def show_category(self, callback_query: CallbackQuery) -> None:
        fill_id = int(callback_query.data.replace('show_category', ''))
        fill = self.card_fill_service.get_fill_by_id(fill_id)
        keyboard_buttons = []
        for cat in self.card_fill_service.list_categories():
            keyboard_buttons.append(
                [InlineKeyboardButton(text=cat.name, callback_data=f'change_category{cat.code}/{fill_id}')]
            )
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        reply_text = f'Выберите категорию для пополнения {fill.amount}р.'
        if fill.description:
            reply_text += f' ({fill.description})'
        self.send_message(
            chat_id=callback_query.message.chat.chat_id,
            text=reply_text,
            reply_markup=keyboard
        )

    @callback_query_handler(accepted_data=['change_category'])
    def change_category(self, callback_query: CallbackQuery) -> None:
        category_code, fill_id = callback_query.data.replace('change_category', '').split('/')
        fill_id = int(fill_id)
        fill = self.card_fill_service.change_category_for_fill(fill_id, category_code)

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

    def handle_fill_parsed_message(self, parsed_message: IParsedMessage[FillDto]) -> None:
        fill = parsed_message.data
        from_user = UserDto.from_telegramapi(parsed_message.original_message.from_user)
        try:
            fill = self.card_fill_service.handle_new_fill(fill, from_user)
        except:
            self.send_message(
                chat_id=parsed_message.original_message.chat.chat_id,
                text='Ошибка добавления пополнения.'
            )
            raise

        reply_text = f'Принято {fill.amount}р. от @{parsed_message.original_message.from_user.username}'
        if fill.description:
            reply_text += f': {fill.description}'
        reply_text += f', категория: {fill.category_name}.'

        change_category = InlineKeyboardButton(text='Сменить категорию', callback_data=f'show_category{fill.id}')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[change_category]])

        self.send_message(
            chat_id=parsed_message.original_message.chat.chat_id,
            text=reply_text,
            reply_markup=keyboard
        )

    def handle_months_parsed_message(self, parsed_message: IParsedMessage[List[Month]]) -> None:
        months = parsed_message.data
        months_numbers = ','.join([str(m.value) for m in months])
        my = InlineKeyboardButton(text='Мои пополнения', callback_data=f'my{months_numbers}')
        stat = InlineKeyboardButton(text='Отчет за месяцы', callback_data=f'stat{months_numbers}')
        total = InlineKeyboardButton(text='Сумма всех пополнений', callback_data='total')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[my], [stat], [total]])
        self.send_message(
            chat_id=parsed_message.original_message.chat.chat_id,
            text=f'Выбраны месяцы: {", ".join(map(month_names.get, months))}. Какая информация интересует?',
            reply_markup=keyboard
        )

    @message_handler()
    def basic_message_handler(self, message: Message) -> None:
        if message.text:
            self.logger.info(f'Received message {message.text}')
            fill_message = FillMessageParser().parse(message)
            if fill_message:
                self.logger.info(f'Found fill {fill_message.data}')
                self.handle_fill_parsed_message(fill_message)
                return

            months_message = MonthMessageParser().parse(message)
            if months_message:
                self.logger.info(f'Found months {months_message.data}')
                self.handle_months_parsed_message(months_message)
                return

    def _format_user_fills(self, fills: List[FillDto], from_user: UserDto, months: List[Month], year: int) -> str:
        m_names = ', '.join(map(month_names.get, months))
        if len(fills) == 0:
            text = f'Не было пополнений в {m_names} {year}.'
        else:
            text = (
                    f'Пополнения @{from_user.username} за {m_names} {year}:\n' +
                    '\n'.join(
                        [f'{fill.fill_date}: {fill.amount} {fill.description} {fill.category_name}' for fill in fills]
                    )
            )
        return text

    @callback_query_handler(accepted_data=['my'])
    def my_fills_current_year(self, callback_query: CallbackQuery) -> None:
        months = [Month(int(val)) for val in callback_query.data.replace('my', '').split(',')]
        year = datetime.now().year
        from_user = UserDto.from_telegramapi(callback_query.from_user)
        fills = self.card_fill_service.get_user_fills_in_months(from_user, months, year)

        message_text = self._format_user_fills(fills, from_user, months, year)
        months_numbers = ','.join([str(m.value) for m in months])
        previous_year = InlineKeyboardButton(
            text='Предыдущий год', callback_data=f'fills_previous_year{months_numbers}'
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[previous_year]])
        self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text, reply_markup=keyboard)

    @callback_query_handler(accepted_data=['fills_previous_year'])
    def my_fills_previous_year(self, callback_query: CallbackQuery) -> None:
        months = [Month(int(val)) for val in callback_query.data.replace('fills_previous_year', '').split(',')]
        previous_year = datetime.now().year - 1
        from_user = UserDto.from_telegramapi(callback_query.from_user)
        fills = self.card_fill_service.get_user_fills_in_months(from_user, months, previous_year)
        message_text = self._format_user_fills(fills, from_user, months, previous_year)
        self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text)

    def _format_monthly_report(self, data: Dict[Month, List[UserSumOverPeriodDto]], year: int) -> str:
        message_text = ''
        for month, monthly_data in data.items():
            message_text += f'*{month_names[month]} {year}:*\n'
            for user_sum_per_month in monthly_data:
                message_text += f'@{user_sum_per_month.username}: {user_sum_per_month.amount}\n'
                for category, category_amount in user_sum_per_month.by_category.items():
                    message_text += f'  - {category}: {category_amount}\n'
        message_text = message_text.replace('_', '\\_').replace('.', '\\.').replace('-', '\\-')
        return message_text

    @callback_query_handler(accepted_data=['stat'])
    def per_month_current_year(self, callback_query: CallbackQuery) -> None:
        months = [Month(int(val)) for val in callback_query.data.replace('stat', '').split(',')]
        year = datetime.now().year
        data = self.card_fill_service.get_monthly_report(months, year)

        message_text = self._format_monthly_report(data, year)
        months_numbers = ','.join([str(m.value) for m in months])
        previous_year = InlineKeyboardButton(text='Предыдущий год', callback_data=f'previous_year{months_numbers}')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[previous_year]])

        self.send_message(
            chat_id=callback_query.message.chat.chat_id,
            text=message_text,
            parse_mode=ParseMode.MarkdownV2,
            reply_markup=keyboard
        )

    @callback_query_handler(accepted_data=['previous_year'])
    def per_month_previous_year(self, callback_query: CallbackQuery) -> None:
        months = [Month(int(val)) for val in callback_query.data.replace('previous_year', '').split(',')]
        previous_year = datetime.now().year - 1
        data = self.card_fill_service.get_monthly_report(months, previous_year)

        message_text = self._format_monthly_report(data, previous_year)
        self.send_message(
            chat_id=callback_query.message.chat.chat_id,
            text=message_text,
            parse_mode=ParseMode.MarkdownV2
        )

    @callback_query_handler(accepted_data=['total'])
    def total(self, callback_query: CallbackQuery) -> None:
        data = self.card_fill_service.get_total_report()
        message_text = '\n'.join(f'@{user_sum_total.username}: {user_sum_total.amount}' for user_sum_total in data)
        self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text)

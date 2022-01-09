from typing import List, Dict, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
from telegramapi.bot import Bot, message_handler, callback_query_handler
from telegramapi.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from dto import (
    Month, FillDto, CategoryDto, UserDto, SummaryOverPeriodDto,
    CategorySumOverPeriodDto, UserSumOverPeriodDto, FillScopeDto,
    ProportionOverPeriodDto
)
from message_parsers import IParsedMessage
from message_parsers.month_message_parser import Month, MonthMessageParser
from message_parsers.fill_message_parser import FillMessageParser
from services.card_fill_service import CardFillService, CardFillServiceSettings
from services.graph_service import GraphService

if TYPE_CHECKING:
    from logging import Logger


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


@dataclass(frozen=True)
class CardFillingBotSettings:
    mysql_user: str
    mysql_password: str
    mysql_host: str
    mysql_database: str
    minor_proportion_user_id: int
    major_proportion_user_id: int
    logger: 'Logger'


class CardFillingBot(Bot):
    def __init__(self, token: str, settings: CardFillingBotSettings) -> None:
        super().__init__(token)
        self.logger = settings.logger
        card_fill_service_settings = CardFillServiceSettings(
            mysql_user=settings.mysql_user,
            mysql_password=settings.mysql_password,
            mysql_host=settings.mysql_host,
            mysql_database=settings.mysql_database,
            minor_proportion_user_id=settings.minor_proportion_user_id,
            major_proportion_user_id=settings.major_proportion_user_id,
            logger=settings.logger,
        )
        self.card_fill_service = CardFillService(card_fill_service_settings)
        self.graph_service = GraphService()

    @message_handler()
    def basic_message_handler(self, message: Message) -> None:
        if message.text:
            self.logger.info(f'Received message {message.text}')
            fill_message = FillMessageParser(self.card_fill_service).parse(message)
            if fill_message:
                self.logger.info(f'Found fill {fill_message.data}')
                self.handle_fill_parsed_message(fill_message)
                return

            months_message = MonthMessageParser().parse(message)
            if months_message:
                self.logger.info(f'Found months {months_message.data}')
                self.handle_months_parsed_message(months_message)
                return
        self.handle_message_fallback(message)

    def handle_fill_parsed_message(self, parsed_message: IParsedMessage[FillDto]) -> None:
        fill = parsed_message.data
        try:
            fill = self.card_fill_service.handle_new_fill(fill)
            reply_text = f'Принято {fill.amount}р. от @{fill.user.username}'
            if fill.description:
                reply_text += f': {fill.description}'
            reply_text += f', категория: {fill.category.name}.'

            budget = self.card_fill_service.get_budget_for_category(fill.category, fill.scope)
            if budget:
                current_category_usage = self.card_fill_service.get_current_month_budget_usage_for_category(
                    fill.category, fill.scope
                )
                reply_text += (
                    f'\nИспользовано {current_category_usage.amount:.0f} из {current_category_usage.monthly_limit:.0f}.'
                )

            change_category = InlineKeyboardButton(text='Сменить категорию', callback_data=f'show_category{fill.id}')
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[change_category]])
            self.send_message(
                chat_id=parsed_message.original_message.chat.chat_id,
                text=reply_text,
                reply_markup=keyboard
            )
        except:
            self.send_message(
                chat_id=parsed_message.original_message.chat.chat_id,
                text='Ошибка добавления пополнения.'
            )
            raise

    def handle_months_parsed_message(self, parsed_message: IParsedMessage[List[Month]]) -> None:
        months = parsed_message.data
        months_numbers = ','.join([str(m.value) for m in months])
        my = InlineKeyboardButton(text='Мои пополнения', callback_data=f'my{months_numbers}')
        stat = InlineKeyboardButton(text='Отчет за месяцы', callback_data=f'stat{months_numbers}')
        yearly_stat = InlineKeyboardButton(text='С начала года', callback_data='yearly_stat')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[my], [stat], [yearly_stat]])
        self.send_message(
            chat_id=parsed_message.original_message.chat.chat_id,
            text=f'Выбраны месяцы: {", ".join(map(month_names.get, months))}. Какая информация интересует?',
            reply_markup=keyboard
        )

    def handle_message_fallback(self, message: Message) -> None:
        self.send_message(
            chat_id=message.chat.chat_id,
            text=(
                'Укажите сумму и комментарий в сообщении, например: "150 макдак", для добавления новой записи,'
                'или один или несколько месяцев, например, "январь февраль", для просмотра статистики.'
            )
        )

    @callback_query_handler(accepted_data=['show_category'])
    def show_category(self, callback_query: CallbackQuery) -> None:
        fill_id = int(callback_query.data.replace('show_category', ''))
        fill = self.card_fill_service.get_fill_by_id(fill_id)
        categories = self.card_fill_service.list_categories()

        keyboard_buttons = []
        buttons_per_row = 2
        for i in range (0, len(categories), buttons_per_row):
            buttons_group = []
            for cat in categories[i:i + buttons_per_row]:
                buttons_group.append(
                    InlineKeyboardButton(text=cat.name, callback_data=f'change_category{cat.code}/{fill_id}')
                )
            keyboard_buttons.append(buttons_group)
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        reply_text = f'Выберите категорию для пополнения {fill.amount} р.'
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

        reply_text = f'Категория пополнения {fill.amount} р.'
        if fill.description:
            reply_text += f' ({fill.description})'
        reply_text += f' изменена на "{fill.category.name}".'

        budget = self.card_fill_service.get_budget_for_category(fill.category, fill.scope)
        if budget:
            current_category_usage = self.card_fill_service.get_current_month_budget_usage_for_category(
                fill.category, fill.scope
            )
            reply_text += (
                f'\nИспользовано {current_category_usage.amount:.0f} из {current_category_usage.monthly_limit:.0f}.'
            )

        change_category = InlineKeyboardButton(text='Сменить категорию', callback_data=f'show_category{fill.id}')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[change_category]])

        self.send_message(
            chat_id=callback_query.message.chat.chat_id,
            text=reply_text,
            reply_markup=keyboard
        )

    @staticmethod
    def _format_user_fills(fills: List[FillDto], from_user: UserDto, months: List[Month], year: int) -> str:
        m_names = ', '.join(map(month_names.get, months))
        if len(fills) == 0:
            text = f'Не было пополнений в {m_names} {year}.'
        else:
            text = (
                f'Пополнения @{from_user.username} за {m_names} {year}:\n' +
                '\n'.join(
                    [f'{fill.fill_date}: {fill.amount} {fill.description} {fill.category.name}' for fill in fills]
                )
            )
        return text

    @callback_query_handler(accepted_data=['my'])
    def my_fills_current_year(self, callback_query: CallbackQuery) -> None:
        months = [Month(int(val)) for val in callback_query.data.replace('my', '').split(',')]
        year = datetime.now().year
        from_user = UserDto.from_telegramapi(callback_query.from_user)
        scope = self.card_fill_service.get_scope(callback_query.message.chat.chat_id)
        fills = self.card_fill_service.get_user_fills_in_months(from_user, months, year, scope)

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
        scope = self.card_fill_service.get_scope(callback_query.message.chat.chat_id)
        fills = self.card_fill_service.get_user_fills_in_months(from_user, months, previous_year, scope)
        message_text = self._format_user_fills(fills, from_user, months, previous_year)
        self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text)

    def _format_by_user_block(self, data: List[UserSumOverPeriodDto], scope: FillScopeDto) -> str:
        if scope.scope_type == 'PRIVATE':
            return '\n'.join([f'{user_sum.amount:.0f}' for user_sum in data])
        return (
            '\n'.join([f'@{user_sum.username}: {user_sum.amount:.0f}' for user_sum in data])
            .replace('_', '\\_')
        )

    def _format_by_category_block(self, data: List[CategorySumOverPeriodDto], display_limits: bool) -> str:
        rows = []
        for category_sum in data:
            text = f'  - {category_sum.category_name}: {category_sum.amount:.0f}'
            if display_limits and category_sum.monthly_limit:
                text += f' (из {category_sum.monthly_limit:.0f})'
            rows.append(text)
        return '_Категории:_\n' + '\n'.join(rows)

    def _format_proportions_block(self, data: ProportionOverPeriodDto) -> str:
        return (
            f'_Пропорции:_\n  - текущая: {data.proportion_actual:.2f}\n'
            f'  - ожидаемая: {data.proportion_target:.2f}'
        ).replace('.', '\\.')

    def _format_monthly_report(self, data: Dict[Month, SummaryOverPeriodDto], year: int, scope: FillScopeDto) -> str:
        message_text = ''
        for month, data_month in data.items():
            message_text += f'*{month_names[month]} {year}:*\n'
            message_text += self._format_by_user_block(data_month.by_user, scope) + '\n\n'
            message_text += self._format_by_category_block(data_month.by_category, display_limits=True)
            if scope.scope_type == 'GROUP':
                message_text += '\n\n' + self._format_proportions_block(data_month.proportions)
            message_text += '\n\n'
        return (
            message_text
            .replace('-', '\\-')
            .replace('(', '\\(')
            .replace(')', '\\)')
        )

    @callback_query_handler(accepted_data=['stat'])
    def per_month_current_year(self, callback_query: CallbackQuery) -> None:
        months = [Month(int(val)) for val in callback_query.data.replace('stat', '').split(',')]
        year = datetime.now().year
        scope = self.card_fill_service.get_scope(callback_query.message.chat.chat_id)
        data = self.card_fill_service.get_monthly_report(months, year, scope)

        message_text = self._format_monthly_report(data, year, scope)
        months_numbers = ','.join([str(m.value) for m in months])
        previous_year = InlineKeyboardButton(text='Предыдущий год', callback_data=f'previous_year{months_numbers}')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[previous_year]])

        if len(months) == 1:
            month = months[0]
            diagram = self.graph_service.create_by_category_diagram(
                data[month].by_category, name=f'{month_names[month]} {year}'
            )
            if diagram:
                self.send_photo(
                    callback_query.message.chat.chat_id,
                    photo=diagram,
                    caption=message_text,
                    parse_mode=ParseMode.MarkdownV2,
                    reply_markup=keyboard
                )
                return
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
        scope = self.card_fill_service.get_scope(callback_query.message.chat.chat_id)
        data = self.card_fill_service.get_monthly_report(months, previous_year, scope)

        message_text = self._format_monthly_report(data, previous_year, scope)
        if len(months) == 1:
            month = months[0]
            diagram = self.graph_service.create_by_category_diagram(
                data[month].by_category, name=f'{month_names[month]} {previous_year}'
            )
            if diagram:
                self.send_photo(
                    callback_query.message.chat.chat_id,
                    photo=diagram,
                    caption=message_text,
                    parse_mode=ParseMode.MarkdownV2
                )
                return
        self.send_message(
            chat_id=callback_query.message.chat.chat_id,
            text=message_text,
            parse_mode=ParseMode.MarkdownV2
        )

    @callback_query_handler(accepted_data=['yearly_stat'])
    def per_year(self, callback_query: CallbackQuery) -> None:
        year = datetime.now().year
        scope = self.card_fill_service.get_scope(callback_query.message.chat.chat_id)
        data = self.card_fill_service.get_yearly_report(year, scope)
        diagram = self.graph_service.create_by_category_diagram(data.by_category, name=str(year))

        caption = f'*За {year} год:*\n'
        caption += self._format_by_user_block(data.by_user, scope) + '\n\n'
        caption += self._format_by_category_block(data.by_category, display_limits=False)
        if scope.scope_type == 'GROUP':
            caption += '\n\n' + self._format_proportions_block(data.proportions)
        caption = caption.replace('-', '\\-')
        self.send_photo(
            callback_query.message.chat.chat_id, photo=diagram, caption=caption, parse_mode=ParseMode.MarkdownV2
        )

from typing import List
from enum import Enum
import re
import logging
import sys
import time
from datetime import datetime
from sqlalchemy import create_engine, extract, func
from sqlalchemy.orm import scoped_session, sessionmaker
from telegramapi.bot import Bot, message_handler, callback_query_handler
from telegramapi.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from model import TelegramUser, CardFill
from config import test_token, mysql_user, mysql_password, mysql_host, mysql_database, webhook_url
from flask import Flask, request


NEED_RESET_WEBHOOK = False


SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_database}'
engine = create_engine(SQLALCHEMY_DATABASE_URI, pool_recycle=3600)
Session = scoped_session(sessionmaker(bind=engine))


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


numbers_regexp = re.compile(r'[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?')


def find_months(text: str) -> List[Month]:
    results: List[Month] = []
    if text:
        for word in text.split(' '):
            for month, month_re in months_regexps.items():
                result = re.search(month_re, word, re.IGNORECASE)
                if result:
                    results.append(month)
    return results


def find_numbers(text: str) -> List[float]:
    return re.findall(numbers_regexp, text)


class CardFillingBot(Bot):
    @message_handler()
    def add_new_fill(self, message: Message) -> None:
        if message.text:
            numbers = list(find_numbers(message.text))
            months = find_months(message.text)
            if numbers:
                if len(numbers) > 1:
                    self.send_message(
                        chat_id=message.chat.chat_id,
                        text='Отправьте суммы пополнения по одной в каждом сообщении.'
                    )
                else:
                    db_session = Session()
                    try:
                        card_fill = CardFill(
                            user_id=message.from_user.user_id,
                            fill_date=datetime.fromtimestamp(message.date),
                            amount=float(numbers[0])
                        )
                        db_session.add(card_fill)
                        db_session.commit()
                        self.send_message(
                            chat_id=message.chat.chat_id,
                            text=f'Принято {numbers[0]}р. от @{message.from_user.username}.'
                        )
                    except Exception:
                        self.send_message(
                            chat_id=message.chat.chat_id,
                            text='Ошибка добавления суммы пополнения. Попробуйте еще раз позже.'
                        )
                        raise
                    finally:
                        Session.remove()
            elif months:
                my = InlineKeyboardButton(text='Мои пополнения', callback_data='my')
                stat = InlineKeyboardButton(text='Отчет за месяцы', callback_data='stat')
                total = InlineKeyboardButton(text='Сумма всех пополнений', callback_data='total')
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[my], [stat], [total]])
                self.send_message(
                    chat_id=message.chat.chat_id,
                    text=f'Выбраны месяцы: {", ".join(map(months_names.get, months))}. Какая информация интересует?',
                    reply_markup=keyboard
                )

    @callback_query_handler(accepted_data=['my'])
    def my_fills(self, callback_query: CallbackQuery) -> None:
        months = find_months(callback_query.message.text)
        m_values = [month.value for month in months]
        m_names = ', '.join(map(months_names.get, months))
        chat_id = callback_query.message.chat.chat_id
        db_session = Session()
        try:
            from_user = db_session.query(TelegramUser).get(callback_query.from_user.user_id)
            if not from_user:
                print(f'Adding unknown user {callback_query.from_user}')
                tg_user = TelegramUser(
                    user_id=callback_query.from_user.user_id,
                    is_bot=callback_query.from_user.is_bot,
                    first_name=callback_query.from_user.first_name,
                    last_name=callback_query.from_user.last_name,
                    username=callback_query.from_user.username,
                    language_code=callback_query.from_user.language_code
                )
                db_session.add(tg_user)
                db_session.commit()
            print([cf.fill_date.month for cf in from_user.card_fills])
            filtered_fills = list(filter(lambda cf: cf.fill_date.month in m_values and cf.fill_date.year == datetime.now().year, from_user.card_fills))
            if len(filtered_fills) == 0:
                text = f'Не было пополнений в {m_names}.'
            else:
                text = (
                    f'Пополнения @{from_user.username} за {m_names}:\n' +
                    '\n'.join([f'{fill.fill_date}: {fill.amount}' for fill in filtered_fills])
                )
            self.send_message(chat_id=chat_id, text=text)
        finally:
            Session.remove()

    @callback_query_handler(accepted_data=['stat'])
    def per_month(self, callback_query: CallbackQuery) -> None:
        message_text = callback_query.message.text
        chat_id = callback_query.message.chat.chat_id
        months = find_months(message_text)
        if len(months) == 0:
            self.send_message(
                chat_id=chat_id,
                text='Не выбраны месяцы.'
            )
        else:
            db_session = Session()
            try:
                message_text = ''
                for month in months:
                    message_text = message_text + f'*{months_names[month]}:*\n'
                    res = db_session.execute(
                        f'select username, amount from monthly_report where month_num = {month.value} and fill_year = {datetime.now().year}'
                    ).fetchall()
                    if len(res) == 0:
                        message_text = message_text + 'Не было пополнений.\n\n'
                    else:
                        message_text = message_text + '\n'.join(f'@{row[0]}: {row[1]}' for row in res) + '\n\n'
                message_text = message_text.replace('_', '\\_').replace('.', '\\.')
                self.send_message(chat_id=chat_id, text=message_text, parse_mode=ParseMode.MarkdownV2)
            finally:
                Session.remove()

    @callback_query_handler(accepted_data=['total'])
    def total(self, callback_query: CallbackQuery) -> None:
        db_session = Session()
        try:
            query = db_session.query(
                TelegramUser.username,
                func.sum(CardFill.amount).label('total_amount')
            ).join(CardFill).group_by(TelegramUser.username)
            results = db_session.execute(query)
            message_text = '\n'.join(f'@{row[0]}: {row[1]}' for row in results)
            self.send_message(chat_id=callback_query.message.chat.chat_id, text=message_text)
        finally:
            Session.remove()


app = Flask(__name__)


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(logging.INFO)


@app.route('/cardFillingBot', methods=['POST'])
def receive_update():
    try:
        update = request.get_json()
        app.logger.info(f'Got update {update}')
        bot.handle_update_raw(update)
        return 'ok'
    except Exception:
        if update:
            app.logger.exception(f'Exception in processing update {update}')
        else:
            app.logger.exception('Unexpected error')
        return 'not ok'


bot = CardFillingBot(token=test_token)

webhook_info = bot.get_webhook_info()
app.logger.info(webhook_info)

need_reset_webhook = NEED_RESET_WEBHOOK or not webhook_info.url

if need_reset_webhook:
    if webhook_info.url:
        bot.delete_webhook()
    bot.set_webhook(url=webhook_url)

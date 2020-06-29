from typing import List
from enum import Enum
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from telegramapi.bot import Bot
from telegramapi.types import Message, ParseMode
from model import TelegramUser
from config import test_token, mysql_user, mysql_password, mysql_host, mysql_database


bot = Bot(token=test_token)

SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_database}'
engine = create_engine(SQLALCHEMY_DATABASE_URI)
Session = scoped_session(sessionmaker(bind=engine))


"""
@bot.message_handler(commands=['start', 'help'])
def dummy_handler(message: Message):
    bot.send_message(chat_id=message.chat.chat_id, text='Hello, world!')
"""


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
    Month.october: 'Октабрь',
    Month.november: 'Ноябрь',
    Month.december: 'Декабрь'
}


def find_months(text: str) -> List[Month]:
    results: List[Month] = []
    for month, month_re in months_regexps.items():
        result = re.search(month_re, text, re.IGNORECASE)
        if result:
            results.append(month)
    return results


@bot.message_handler(commands=['stat'])
def show_user_stat(message: Message):
    db_session = Session()
    try:
        from_user = db_session.query(TelegramUser).get(message.from_user.user_id)
        if not from_user:
            print(f'Adding unknown user {message.from_user}')
            tg_user = TelegramUser(
                user_id=message.from_user.user_id,
                is_bot=message.from_user.is_bot,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                username=message.from_user.username,
                language_code=message.from_user.language_code
            )
            db_session.add(tg_user)
            db_session.commit()
        reply = (
            f'Пополнения @{from_user.username}:\n' +
            '\n'.join([f'{fill.fill_date}: {fill.amount}' for fill in from_user.card_fills])
        )
        bot.send_message(chat_id=message.chat.chat_id, text=reply)
    finally:
        Session.remove()


@bot.message_handler()
def per_month(message: Message):
    months = find_months(message.text)
    if len(months) == 0:
        bot.send_message(
            chat_id=message.chat.chat_id,
            text='Укажите месяц после команды, например "/stat январь".'
        )
        return

    db_session = Session()
    try:
        message_text = ''
        for month in months:
            message_text = message_text + f'*{months_names[month]}:*\n'
            res = db_session.execute(
                f'select username, amount from monthly_report where month_num = {month.value}'
            ).fetchall()
            if len(res) == 0:
                message_text = message_text + 'Не было пополнений.\n\n'
            else:
                message_text = message_text + '\n'.join(f'@{row[0]}: {row[1]}' for row in res) + '\n\n'
        message_text = message_text.replace('_', '\\_').replace('.', '\\.')
        bot.send_message(chat_id=message.chat.chat_id, text=message_text, parse_mode=ParseMode.MarkdownV2)
    finally:
        Session.remove()


print(bot.get_me())
bot.long_polling()

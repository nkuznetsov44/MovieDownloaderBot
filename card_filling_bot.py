from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from telegramapi.bot import Bot
from telegramapi.types import Message
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


@bot.message_handler()
def dummy_handler(message: Message):
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
        print(f'Received message "{message.text}" from user {from_user}')
    finally:
        db_session.remove()


print(bot.get_me())
bot.long_polling()

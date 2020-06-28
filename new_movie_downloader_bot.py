from telegramapi.bot import Bot
from telegramapi.types import Message
from config import test_token


bot = Bot(token=test_token)


@bot.message_handler(commands=['start', 'help'])
def dummy_handler(message: Message):
    bot.send_message(chat_id=message.chat.chat_id, text='Hello, world!')


@bot.message_handler()
def dummy_handler(message: Message):
    print(message)


print(bot.get_me())
bot.long_polling()

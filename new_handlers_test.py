from telegramapi.bot import message_handler, Bot
from telegramapi.types import Message
from config import yet_another_testing_token


class DummyBot(Bot):
    def __init__(self, token: str) -> None:
        super().__init__(token)

    @message_handler(commands=['start'])
    def dummy_start_handler(self, message: Message) -> None:
        self.send_message(chat_id=message.chat.chat_id, text='Start handler called')

    @message_handler(commands=['help'])
    def dummy_help_handler(self, message: Message) -> None:
        self.send_message(chat_id=message.chat.chat_id, text='Help handler called')

    @message_handler()
    def dummy_all_handler(self, message: Message) -> None:
        self.send_message(chat_id=message.chat.chat_id, text=f'Other handler called. Echoing {message.text}')


dummy_bot = DummyBot(yet_another_testing_token)
dummy_bot.long_polling()

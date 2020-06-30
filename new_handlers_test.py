from telegramapi.bot import message_handler, callback_query_handler, Bot
from telegramapi.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config import yet_another_testing_token


class DummyBot(Bot):
    @message_handler(commands=['start'])
    def dummy_start_handler(self, message: Message) -> None:
        self.send_message(chat_id=message.chat.chat_id, text='Start handler called.')

    @message_handler(commands=['help'])
    def dummy_help_handler(self, message: Message) -> None:
        self.send_message(chat_id=message.chat.chat_id, text='Help handler called.')

    @message_handler()
    def dummy_all_handler(self, message: Message) -> None:
        self.send_message(chat_id=message.chat.chat_id, text=f'Other handler called. Echoing {message.text}.')

    @message_handler()
    def dummy_handler_with_callbacks(self, message: Message) -> None:
        button = InlineKeyboardButton(text='button', callback_data='test_callback_data')
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
        self.send_message(
            chat_id=message.chat.chat_id,
            text='Testing callback query',
            reply_markup=reply_markup
        )

    @callback_query_handler(accepted_data=['test_callback_data'])
    def dummy_callback_query_handler(self, callback_query: CallbackQuery) -> None:
        self.send_message(chat_id=callback_query.message.chat.chat_id, text='Callback query handler called.')


dummy_bot = DummyBot(yet_another_testing_token)
dummy_bot.long_polling()

import logging
import os
from flask import Flask, request
from card_filling_bot import CardFillingBot, CardFillingBotSettings


NEED_RESET_WEBHOOK = bool(os.getenv('NEED_RESET_WEBHOOK', False))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
if not WEBHOOK_URL:
    raise Exception('Environment variable WEBHOOK_URL is not set')


app = Flask(__name__)


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(logging.INFO)


bot_settings = CardFillingBotSettings(
    mysql_user=os.getenv('MYSQL_USER'),
    mysql_password=os.getenv('MYSQL_PASSWORD'),
    mysql_host=os.getenv('MYSQL_HOST'),
    mysql_database=os.getenv('MYSQL_DATABASE'),
    redis_host=os.getenv('REDIS_HOST'),
    redis_port=6379,
    redis_db=int(os.getenv('REDIS_DB')),
    redis_password=os.getenv('REDIS_PASSWORD'),
    minor_proportion_user_id=int(os.getenv('MINOR_PROPORTION_USER_ID')),
    major_proportion_user_id=int(os.getenv('MAJOR_PROPORTION_USER_ID')),
    logger=app.logger
)
bot = CardFillingBot(token=os.getenv('TELEGRAM_TOKEN'), settings=bot_settings)


webhook_info = bot.get_webhook_info()
app.logger.info(webhook_info)

need_reset_webhook = NEED_RESET_WEBHOOK or not webhook_info.url or webhook_info.url != WEBHOOK_URL

if need_reset_webhook:
    app.logger.info('Reseting webhook')
    if webhook_info.url:
        bot.delete_webhook()
    bot.set_webhook(url=WEBHOOK_URL)


@app.route('/', methods=['POST'])
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

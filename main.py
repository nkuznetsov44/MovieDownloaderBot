"""from movie_downloader_bot import MovieDownloaderBot
import config
import logging
import sys
import time

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)

params = {
    'telegram_token': config.telegram_token,
    'rutracker_user': config.rutracker_user,
    'rutracker_password': config.rutracker_password,
    'download_folder': config.download_folder,
    # 'proxy': config.proxy,
    'syno_api_url': config.synology_api_url,
    'syno_user': config.synology_user,
    'syno_password': config.synology_password,
    'allowed_users_id': config.allowed_telegram_users_id
}

if __name__ == '__main__':
    bot = MovieDownloaderBot(**params)
    while 1 == 1:
        try:
            response = bot.get_updates(timeout=30)
            bot.handle_response(response)
        except Exception as e:
            log.error('Error', exc_info=True)
            time.sleep(30)"""

import logging
from flask import Flask, request
from card_filling_bot import CardFillingBot, CardFillingBotSettings
from config import card_filling_bot_token, mysql_user, mysql_password, mysql_host, mysql_database, webhook_url


NEED_RESET_WEBHOOK = False


app = Flask(__name__)


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(logging.INFO)


bot_settings = CardFillingBotSettings(
    mysql_user=mysql_user,
    mysql_password=mysql_password,
    mysql_host=mysql_host,
    mysql_database=mysql_database,
    logger=app.logger
)
bot = CardFillingBot(token=card_filling_bot_token, settings=bot_settings)


webhook_info = bot.get_webhook_info()
app.logger.info(webhook_info)

need_reset_webhook = NEED_RESET_WEBHOOK or not webhook_info.url

if need_reset_webhook:
    if webhook_info.url:
        bot.delete_webhook()
    bot.set_webhook(url=webhook_url)


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


from movie_downloader_bot import MovieDownloaderBot
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
            time.sleep(30)

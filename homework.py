
import os
import requests
import time
from dotenv import load_dotenv
from telegram import Bot
import telegram
import logging
from logging import StreamHandler
import sys


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

# logger = logging.getLogger(__name__)
# handler = logging.StreamHandler(stream=None)
# logger.addHandler(handler)


def send_message(bot, message):
    """Функция отправляет сообщение."""
    bot = Bot(token=TELEGRAM_TOKEN)
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Функция отправляет API запрос."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = HEADERS
    response = requests.get(ENDPOINT, headers=headers, params=params)
    if response.status_code != 200:
        raise requests.ConnectionError(
            "Expected status code 200, but got {}".format(response.status_code)
        )
    response = response.json()
    return response


def check_response(response):
    """Функция проверяет получаемые в запросе данные."""
    homework = response['homeworks']
    if homework != list(homework):
        raise TypeError('Запрос не вернул список')
    return homework


def parse_status(homework):
    """Функция на основе полученных данных
    формирует сообщение о статусе работы.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return 'Изменился статус проверки работы "{0}". {1}'.format(
        homework_name, verdict
    )


def check_tokens():
    """
        Функция проверяет доступность глобальных переменных,
    необходимых для корректной работы бота.
    """
    if (
        PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
        or TELEGRAM_CHAT_ID is None
    ):
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
        handlers=[StreamHandler(stream=sys.stdout)]
    )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while check_tokens():
        try:
            logging.critical('All constant is not ok')
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                print(message)
                send_message(bot, message)
                current_timestamp = current_timestamp
                time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

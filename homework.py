import os
import requests
import time
from dotenv import load_dotenv
from telegram import Bot
import telegram
import logging
import logging.config
import copy


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
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('bot')


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
        logger.error(
            'Сбой в работе: URL {0} недоступен. Код ответа API: {1}'.format(
                ENDPOINT, response.status_code
            ))
        raise requests.ConnectionError(
            "Expected status code 200, but got {0}".format(
                response.status_code
            )
        )
    response = response.json()
    return response


def check_response(response):
    """Функция проверяет получаемые в запросе данные."""
    homework = response['homeworks']
    if homework is None:
        logger.info('Нет домашки.')
        raise Exception('Нет домашней работы')
    if homework != list(homework):
        logger.error('Запрос не вернул список')
        raise TypeError('Запрос не вернул список')
    return homework


def parse_status(homework):
    """Функция на основе полученных данных формирует сообщение."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return 'Изменился статус проверки работы "{0}". {1}'.format(
        homework_name, verdict
    )


def check_tokens():
    """Функция проверяет доступность глобальных переменных."""
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
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_s = ''
    message_f = copy.deepcopy(message_s)
    while check_tokens():
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message_f = parse_status(homework)
                if message_f != message_s:
                    send_message(bot, message_f)
                    logger.info('Сообщение успешно отправленно')
                    current_timestamp = current_timestamp
                    time.sleep(RETRY_TIME)
                message_s = copy.deepcopy(message_f)

        except Exception as error:
            logger.error('Сеть недоступна')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
    else:
        logger.critical('Переменные окружения недоступны.')
        message = 'Переменные недоступны.'
        send_message(bot, message)


if __name__ == '__main__':
    main()

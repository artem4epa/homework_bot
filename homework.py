import os
import sys
import requests
import time
from dotenv import load_dotenv
from telegram import Bot
import telegram
import logging
import logging.config
from http import HTTPStatus
from errors import ConnectionError, HTTPError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger('bot')


def send_message(bot, message):
    """Функция отправляет сообщение."""
    bot = Bot(token=TELEGRAM_TOKEN)
    response = bot.send_message(TELEGRAM_CHAT_ID, message)
    if response:
        logger.info('Сообщение успешно отправленно.')
        return response
    else:
        raise Exception('Сообщение не отправленно.')


def get_api_answer(current_timestamp):
    """Функция отправляет API запрос."""
    logger.info('Старт API запроса.')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = HEADERS
    try:
        response = requests.get(ENDPOINT, headers=headers, params=params)
        if response.status_code == HTTPStatus.OK:
            response = response.json()
            return response

        raise HTTPError(
            "Response: {0}, parameters: {1}".format(
                response.text, response.request
            )
        )
    except ConnectionError:
        raise ConnectionError('Соединение оборвалось')


def check_response(response):
    """Функция проверяет получаемые в запросе данные."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных.')
    if response.keys() & {'homeworks', 'current_date'}:
        homeworks = response.get('homeworks')
    else:
        raise ValueError('Ошибка')
    if not isinstance(homeworks, list):
        raise TypeError('Запрос не вернул список')
    return homeworks


def parse_status(homeworks):
    """Функция на основе полученных данных формирует сообщение."""
    if homeworks.keys() & {'homework_name', 'status'}:
        homework_name = homeworks.get('homework_name')
        homework_status = homeworks.get('status')
        verdict = HOMEWORK_VERDICTS[homework_status]
        return 'Изменился статус проверки работы "{0}". {1}'.format(
            homework_name, verdict
        )
    raise ValueError('Отсутствуют необходимые данные.')


def check_tokens():
    """Функция проверяет доступность глобальных переменных."""
    checking = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    return checking


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    MESSAGE = ''
    if not check_tokens():
        logger.critical('Переменные окружения недоступны.')
        message = 'Переменные недоступны.'
        send_message(bot, message)
        sys.exit()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks)
                if message != MESSAGE:
                    send_message(bot, message)
                    MESSAGE = message
                    current_timestamp = current_timestamp

        except Exception as error:
            logger.error(f'Сбой работы программы: {error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    main()

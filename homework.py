import os
import sys
import requests
import time
from dotenv import load_dotenv
from telegram import Bot
import telegram
import logging
import logging.config
import copy
from http import HTTPStatus
from errors import ConnectionError


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
        logger.error('Ошибка отправки сообщения.')


def get_api_answer(current_timestamp):
    """Функция отправляет API запрос."""
    try:
        logger.info('Старт API запроса.')
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        headers = HEADERS
        response = requests.get(ENDPOINT, headers=headers, params=params)
        if response.status_code == HTTPStatus.OK:
            response = response.json()
            return response
        else:
            raise ConnectionError(
                "Response: {0}, parameters: {1}".format(
                    response.text, response.request
                )
            )
    except ConnectionError:
        raise ConnectionError('Соединение оборвалось')


def check_response(response):
    """Функция проверяет получаемые в запросе данные."""
    if isinstance(response, dict):
        if response.keys() & {'homeworks', 'current_date'}:
            homeworks = response.get('homeworks')
        else:
            raise ValueError('Ошибка')
        if not isinstance(homeworks, list):
            raise TypeError('Запрос не вернул список')
        return homeworks
    else:
        raise TypeError('Некорректный тип данных')


def parse_status(homeworks):
    """Функция на основе полученных данных формирует сообщение."""
    if homeworks.keys() & {'homework_name', 'status'}:
        homework_name = homeworks.get('homework_name')
        homework_status = homeworks.get('status')
        verdict = HOMEWORK_VERDICTS[homework_status]
        return 'Изменился статус проверки работы "{0}". {1}'.format(
            homework_name, verdict
        )
    else:
        raise ValueError('Отсутствуют необходимые данные.')


def check_tokens():
    """Функция проверяет доступность глобальных переменных."""
    checking = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    return checking


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_s = ''
    message_f = copy.deepcopy(message_s)
    if check_tokens():
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if homeworks:
                    message_f = parse_status(homeworks)
                    if message_f != message_s:
                        send_message(bot, message_f)
                        current_timestamp = current_timestamp
                    message_s = copy.deepcopy(message_f)

            except Exception as error:
                logger.error(f'Сбой работы программы: {error}')
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
            finally:
                time.sleep(RETRY_TIME)
    else:
        logger.critical('Переменные окружения недоступны.')
        message = 'Переменные недоступны.'
        send_message(bot, message)
        sys.exit()


if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    main()

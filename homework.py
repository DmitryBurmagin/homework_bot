import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for name, value in tokens.items():
        if not value:
            logging.critical(f'Ошибка: Токен отсутсвует {name}')
            return False
    return True


def send_message(bot, message: str):
    """Отправка сообщений."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.debug('Сообщение отправлено')


def get_api_answer(timestamp: int) -> dict:
    """Запрос ответа API."""
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise logging.error(
                f'Ошибка: Статус HTTP {homework_statuses.status_code}'
            )
    except requests.RequestException as re:
        logging.error(f'Ошибка при запросе к API: {re}')
    return homework_statuses.json()


def check_response(response: dict) -> list:
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise logging.error(
            'Ошибка: Ответ API не является словарем'
        )
    if 'homeworks' not in response:
        raise logging.error(
            'Ошибка: В ответе API отсутствует ключ "homeworks"'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Ошибка: Данные под ключом "homeworks" не являются списком'
        )
    if 'current_date' not in response:
        raise logging.error(
            'Ошибка: В ответе API отсутствует ключ "current_date"'
        )
    return True


def parse_status(homework: dict) -> str:
    """Проверка статуса домашней работы."""
    try:
        if 'homework_name' not in homework:
            raise logging.error('Ключ homework_name отсутствует')
        homework_name = homework.get('homework_name')
        status = homework.get('status')
    except requests.RequestException as re:
        logging.error(f'Ошибка при запросе к API: {re}')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Ошибка: Неизвестный статус: {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise Exception("Токен не найден")

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time() - 2592000)

    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                homeworks = response['homeworks']
                if homeworks:
                    send_message(bot, parse_status(homeworks[0]))
                    timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

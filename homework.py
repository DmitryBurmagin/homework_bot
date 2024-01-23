import logging
import time
from http import HTTPStatus

import requests
import telegram

from config import PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from exceptions import (
    TokenNotFoundError,
    HttpStatusError,
    ResponseApiError,
    HomeworkStatusError
)


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


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
    logging.info('Отправка сообщения')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение отправлено')
    except requests.RequestException as re:
        logging.error(f'Ошибка при отправке сообщения: {re}')


def get_api_answer(timestamp: int) -> dict:
    """Запрос ответа API."""
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.RequestException as re:
        msg = f'Ошибка при запросе к API: {re}'
        logging.error(msg)
        raise ResponseApiError(msg)

    if homework_statuses.status_code != HTTPStatus.OK:
        raise HttpStatusError(
            f'Ошибка: Статус HTTP {homework_statuses.status_code}'
        )
    return homework_statuses.json()


def check_response(response: dict) -> list:
    """Проверка ответа API."""
    logging.info('Проверка ответа API')
    if not isinstance(response, dict):
        msg = 'Ошибка: Ответ API не является словарем'
        logging.error(msg)
        raise TypeError(msg)
    if 'homeworks' not in response:
        msg = 'Ошибка: В ответе API отсутствует ключ "homeworks"'
        logging.error(msg)
        raise ResponseApiError(msg)
    if not isinstance(response['homeworks'], list):
        msg = 'Ошибка: Данные под ключом "homeworks" не являются списком'
        logging.error(msg)
        raise TypeError(msg)
    if 'current_date' not in response:
        msg = 'Ошибка: В ответе API отсутствует ключ "current_date"'
        logging.error(msg)
        raise ResponseApiError(msg)


def parse_status(homework: dict) -> str:
    """Проверка статуса домашней работы."""
    logging.info('Проверка статуса домашней работы.')
    if 'homework_name' not in homework:
        msg = 'Ключ homework_name отсутствует'
        logging.error(msg)
        raise HomeworkStatusError(msg)
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        msg = f'Ошибка: Неизвестный статус: {status}'
        logging.error(msg)
        raise HomeworkStatusError(msg)
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise TokenNotFoundError("Токен не найден")

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    last_status = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if homeworks:
                current_status = parse_status(homeworks[0])
                if current_status != last_status:
                    send_message(bot, current_status)
                    timestamp = response.get('current_date')
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

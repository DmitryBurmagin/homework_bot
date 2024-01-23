class TokenNotFoundError(Exception):
    """Исключение, возникающее при отсутствии токена."""

    pass


class HttpStatusError(Exception):
    """Исключение, возникающее при статусе отличном от 200."""

    pass


class ResponseApiError(Exception):
    """Исключение, возникающее при неверном ответе от API."""

    pass


class HomeworkStatusError(Exception):
    """Исключение, возникающее при отсутствии токена."""

    pass

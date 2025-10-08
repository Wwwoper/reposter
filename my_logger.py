import logging
from logging.handlers import RotatingFileHandler


def setup_logger():
    """Настройка логгера с ротацией файлов"""
    logger = logging.getLogger('bot')
    logger.setLevel(logging.DEBUG)
    
    # Очистка существующих handlers (если есть)
    logger.handlers.clear()
    
    # Консоль - только INFO и выше для чистого вывода
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console.setFormatter(console_fmt)
    
    # Файл - все DEBUG сообщения с ротацией
    # Максимум 10MB на файл, храним 3 последних файла
    file_handler = RotatingFileHandler(
        'logs/bot.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    
    # Добавление handlers
    logger.addHandler(console)
    logger.addHandler(file_handler)
    
    # Отключаем propagation чтобы избежать дублирования
    logger.propagate = False
    
    return logger


# Создание глобального экземпляра логгера
logger = setup_logger()
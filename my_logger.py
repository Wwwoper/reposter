import logging
import os

if not os.path.exists('logs'):
    os.makedirs('logs')

# Создание экземпляра логгера
my_logger = logging.getLogger('my_logger')
my_logger.setLevel(logging.DEBUG)

# Установка обработчиков для логгера
debug_handler = logging.handlers.RotatingFileHandler(
    'logs/debug.log', maxBytes=1000000, backupCount=2
)
debug_handler.setLevel(logging.DEBUG)

info_handler = logging.handlers.RotatingFileHandler(
    'logs/info.log', maxBytes=1000000, backupCount=2
)
info_handler.setLevel(logging.INFO)

# Форматирование сообщений лога
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
debug_handler.setFormatter(formatter)
info_handler.setFormatter(formatter)

# Добавление обработчиков к логгеру
my_logger.addHandler(debug_handler)
my_logger.addHandler(info_handler)

# Экспорт логгера для использования в других файлах
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[debug_handler, info_handler],
)

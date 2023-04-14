import logging
import os
from logging.handlers import RotatingFileHandler


if not os.path.exists('logs'):
    os.makedirs('logs')
debug_handler = RotatingFileHandler(
    'logs/debug.log', maxBytes=500000, backupCount=3
)
debug_handler.setLevel(logging.DEBUG)

info_handler = RotatingFileHandler(
    'logs/info.log', maxBytes=100000, backupCount=2
)
info_handler.setLevel(logging.INFO)

# создаем обработчик, который будет записывать логи в файл


formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
debug_handler.setFormatter(formatter)
info_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(debug_handler)
logger.addHandler(info_handler)
logger.setLevel(logging.DEBUG)

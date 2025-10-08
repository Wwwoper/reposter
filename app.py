import asyncio
import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Tuple, Set

from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentTypes
from aiogram.utils import executor
from dotenv import load_dotenv

from my_logger import logger
from vk_api import VKAPI
from file_utils import prepare_file_for_upload


# Глобальные переменные для статистики и graceful shutdown
_stats = {'success': 0, 'errors': 0, 'start_time': None}
_is_shutting_down = False


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global _is_shutting_down
    logger.info(f"Получен сигнал {signum}, завершаем работу...")
    _is_shutting_down = True


def create_bot() -> Tuple[Bot, Dispatcher, VKAPI, Set[int]]:
    """Инициализация бота и необходимых компонентов"""
    load_dotenv()
    
    # Валидация переменных окружения
    required_vars = [
        'API_TOKEN', 'WHITE_LIST', 'ACCESS_TOKEN',
        'GROUP_TOKEN', 'GROUP_ID', 'V'
    ]
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Отсутствует обязательная переменная окружения: {var}")
    
    API_TOKEN: str = os.environ['API_TOKEN']
    WHITE_LIST: Set[int] = {
        int(x.strip()) for x in os.environ['WHITE_LIST'].split(',')
    }
    ACCESS_TOKEN: str = os.environ['ACCESS_TOKEN']
    GROUP_TOKEN: str = os.environ['GROUP_TOKEN']
    GROUP_ID: str = os.environ['GROUP_ID']
    V: str = os.environ['V']

    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(bot)
    vk = VKAPI(ACCESS_TOKEN, GROUP_TOKEN, GROUP_ID, V)
    
    logger.info(f"Бот инициализирован. White list: {WHITE_LIST}")
    
    return bot, dp, vk, WHITE_LIST


async def send_welcome(message: types.Message) -> None:
    """Обработчик команды /start"""
    await message.reply("Привет! Отправлю твои посты в ВК")
    logger.info(f"Получена команда /start от {message.chat.id}")


async def handle_photo(
    message: types.Message, bot: Bot, vk: VKAPI, WHITE_LIST: Set[int]
) -> None:
    """
    Обработчик фотографий из Telegram
    
    Args:
        message: сообщение с фото
        bot: экземпляр бота
        vk: экземпляр VK API
        WHITE_LIST: список разрешенных chat_id
    """
    chat_id = message.chat.id
    
    # Проверка white list
    if chat_id not in WHITE_LIST:
        logger.warning(f'Попытка отправки от неразрешенного чата: {chat_id}')
        await message.reply("❌ У вас нет доступа к этому боту")
        return
    
    try:
        # Получение данных о фото
        text = message.caption or ""
        photo = message.photo[-1]  # Берем фото максимального качества
        file_id = photo.file_id
        
        logger.info(f"Получено фото от {chat_id}, file_id: {file_id}")
        
        # Получение информации о файле
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Создание временной директории если не существует
        temp_dir = Path("temp_photos")
        temp_dir.mkdir(exist_ok=True)
        
        # Формирование локального пути
        local_filename = f"temp_photos/{file_id}.jpg"
        
        # КРИТИЧНО: ждем полной загрузки файла
        await file.download(destination=local_filename)
        logger.debug(f'Файл загружен: {local_filename}')
        
        # Комплексная проверка готовности файла
        if not await prepare_file_for_upload(local_filename):
            await message.reply("❌ Ошибка: файл не готов к загрузке")
            return
        
        # Отправка уведомления пользователю
        status_msg = await message.reply("⏳ Загружаю пост в ВК...")
        
        # Публикация в ВК (теперь ждем завершения)
        result = await vk.create_post_from_wall(local_filename, text)
        
        if result and 'response' in result:
            post_id = result['response'].get('post_id')
            await status_msg.edit_text(f"✅ Пост успешно опубликован! ID: {post_id}")
            logger.info(f"Успешная публикация поста {post_id} от {chat_id}")
        else:
            await status_msg.edit_text("❌ Ошибка при публикации поста")
            logger.error(f"Не удалось опубликовать пост от {chat_id}")
            
    except Exception as e:
        logger.error(f'Ошибка обработки фото от {chat_id}: {e}', exc_info=True)
        try:
            await message.reply(f"❌ Произошла ошибка: {str(e)}")
        except Exception:
            pass


async def on_startup(dp: Dispatcher) -> None:
    """Действия при запуске бота"""
    logger.info("Бот запущен и готов к работе")


async def on_shutdown(dp: Dispatcher) -> None:
    """Действия при остановке бота"""
    logger.info("Бот остановлен")
    await dp.storage.close()
    await dp.storage.wait_closed()


def main() -> None:
    """Основная функция запуска приложения"""
    try:
        logger.info('=' * 50)
        logger.info('Запуск приложения')
        logger.info('=' * 50)
        
        bot, dp, vk, WHITE_LIST = create_bot()
        
        # Регистрация обработчиков
        dp.register_message_handler(send_welcome, commands=['start', 'help'])
        dp.register_message_handler(
            lambda message: handle_photo(message, bot, vk, WHITE_LIST),
            content_types=ContentTypes.PHOTO,
        )
        
        # Запуск polling
        executor.start_polling(
            dp,
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.critical(f'Критическая ошибка: {e}', exc_info=True)
        raise
    finally:
        logger.info("Приложение завершено")


if __name__ == '__main__':
    main()
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
    
    # Инициализация статистики
    _stats['start_time'] = datetime.now()
    
    return bot, dp, vk, WHITE_LIST


async def send_welcome(message: types.Message) -> None:
    """Обработчик команды /start"""
    await message.reply(
        "👋 Привет! Я бот для публикации постов в ВК.\n\n"
        "Просто перешли мне фото с подписью, и я опубликую его на стене группы.\n\n"
        "Доступные команды:\n"
        "/start - это сообщение\n"
        "/stats - статистика работы бота"
    )
    logger.info(f"Получена команда /start от {message.chat.id}")


async def send_stats(message: types.Message) -> None:
    """Обработчик команды /stats"""
    # Проверка graceful shutdown
    if _is_shutting_down:
        await message.reply("⚠️ Бот завершает работу")
        logger.warning(f"Отклонен запрос статистики от {message.chat.id}: бот завершает работу")
        return
    
    if _stats['start_time'] is None:
        await message.reply("📊 Статистика еще не собрана")
        return
    
    uptime = datetime.now() - _stats['start_time']
    total = _stats['success'] + _stats['errors']
    rate = (_stats['success'] / total * 100) if total > 0 else 0
    
    # Форматирование времени работы
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = []
    if days > 0:
        uptime_str.append(f"{days}д")
    if hours > 0:
        uptime_str.append(f"{hours}ч")
    if minutes > 0:
        uptime_str.append(f"{minutes}м")
    if not uptime_str:  # Меньше минуты
        uptime_str.append(f"{seconds}с")
    
    stats_text = (
        f"📊 *Статистика бота*\n\n"
        f"⏱ Время работы: {' '.join(uptime_str)}\n"
        f"✅ Успешных постов: {_stats['success']}\n"
        f"❌ Ошибок: {_stats['errors']}\n"
        f"📈 Success rate: {rate:.1f}%\n"
        f"📝 Всего обработано: {total}"
    )
    
    await message.reply(stats_text, parse_mode='Markdown')
    logger.info(f"Запрос статистики от {message.chat.id}")


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
    # Проверка graceful shutdown
    if _is_shutting_down:
        await message.reply("⚠️ Бот завершает работу, попробуйте позже")
        logger.warning(f"Отклонен запрос от {message.chat.id}: бот завершает работу")
        return
    
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
            _stats['errors'] += 1
            return
        
        # Отправка уведомления пользователю
        status_msg = await message.reply("⏳ Загружаю пост в ВК...")
        
        # Публикация в ВК (теперь ждем завершения)
        result = await vk.create_post_from_wall(local_filename, text)
        
        if result and 'response' in result:
            post_id = result['response'].get('post_id')
            await status_msg.edit_text(f"✅ Пост успешно опубликован! ID: {post_id}")
            logger.info(f"Успешная публикация поста {post_id} от {chat_id}")
            
            # Статистика успеха
            _stats['success'] += 1
            
            # Каждые 10 успешных постов - выводим статистику
            if _stats['success'] % 10 == 0:
                uptime = datetime.now() - _stats['start_time']
                total = _stats['success'] + _stats['errors']
                rate = _stats['success'] / total if total > 0 else 0
                logger.info(
                    f"📊 Статистика: ✅{_stats['success']} ❌{_stats['errors']} "
                    f"({rate:.1%}) за {uptime}"
                )
        else:
            await status_msg.edit_text("❌ Ошибка при публикации поста")
            logger.error(f"Не удалось опубликовать пост от {chat_id}")
            _stats['errors'] += 1
            
    except Exception as e:
        logger.error(f'Ошибка обработки фото от {chat_id}: {e}', exc_info=True)
        _stats['errors'] += 1
        try:
            await message.reply(f"❌ Произошла ошибка: {str(e)}")
        except Exception:
            pass


async def cleanup_old_temp_files():
    """Удаляет временные файлы старше 1 часа"""
    temp_dir = Path("temp_photos")
    if not temp_dir.exists():
        return
    
    now = datetime.now().timestamp()
    removed = 0
    
    for file in temp_dir.glob("*.jpg"):
        try:
            age = now - file.stat().st_mtime
            if age > 3600:  # Старше часа
                file.unlink()
                removed += 1
        except Exception as e:
            logger.error(f"Ошибка удаления {file}: {e}")
    
    if removed > 0:
        logger.info(f"🧹 Очищено {removed} старых временных файлов")


async def on_startup(dp: Dispatcher) -> None:
    """Действия при запуске бота"""
    logger.info("Бот запущен и готов к работе")
    
    # Создание директории для логов
    Path("logs").mkdir(exist_ok=True)
    
    # Очистка старых файлов при запуске
    await cleanup_old_temp_files()
    
    # Запуск периодической очистки
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)  # Каждый час
            await cleanup_old_temp_files()
    
    asyncio.create_task(periodic_cleanup())


async def on_shutdown(dp: Dispatcher) -> None:
    """Действия при остановке бота"""
    logger.info("Завершение работы...")
    
    # Вывод финальной статистики
    if _stats['start_time']:
        uptime = datetime.now() - _stats['start_time']
        total = _stats['success'] + _stats['errors']
        rate = _stats['success'] / total if total > 0 else 0
        logger.info(
            f"📊 Финальная статистика: ✅{_stats['success']} ❌{_stats['errors']} "
            f"({rate:.1%}) за {uptime}"
        )
    
    # Очистка временных файлов
    temp_dir = Path("temp_photos")
    if temp_dir.exists():
        removed = 0
        for file in temp_dir.glob("*"):
            try:
                file.unlink()
                removed += 1
            except Exception as e:
                logger.error(f"Ошибка удаления {file}: {e}")
        if removed > 0:
            logger.info(f"🧹 Удалено {removed} временных файлов")
    
    await dp.storage.close()
    await dp.storage.wait_closed()
    logger.info("Graceful shutdown завершен")


def main() -> None:
    """Основная функция запуска приложения"""
    global _is_shutting_down
    
    def shutdown_handler(signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        global _is_shutting_down
        if not _is_shutting_down:  # Обрабатываем только первый сигнал
            _is_shutting_down = True
            logger.info(f"Получен сигнал {signum}, инициирую graceful shutdown...")
            # Даем время на завершение текущих операций
            import sys
            sys.exit(0)
    
    try:
        logger.info('=' * 50)
        logger.info('Запуск приложения')
        logger.info('=' * 50)
        
        # Регистрация обработчиков сигналов
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        
        bot, dp, vk, WHITE_LIST = create_bot()
        
        # Регистрация обработчиков команд
        dp.register_message_handler(send_welcome, commands=['start', 'help'])
        dp.register_message_handler(send_stats, commands=['stats'])
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
        
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки")
        _is_shutting_down = True
    except Exception as e:
        logger.critical(f'Критическая ошибка: {e}', exc_info=True)
        raise
    finally:
        if _is_shutting_down:
            logger.info("Завершение работы приложения...")
        logger.info("Приложение завершено")


if __name__ == '__main__':
    main()
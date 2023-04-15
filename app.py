import asyncio
import os

from typing import Tuple, Set

from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentTypes
from aiogram.utils import executor
from dotenv import load_dotenv

from my_logger import logger
from vk_api import VKAPI


def create_bot() -> Tuple[Bot, Dispatcher, VKAPI, Set[int]]:
    load_dotenv()
    API_TOKEN: str = os.environ['API_TOKEN']
    WHITE_LIST: Set[int] = {
        int(x) for x in os.environ['WHITE_LIST'].split(',')
    }
    ACCESS_TOKEN: str = os.environ['ACCESS_TOKEN']
    GROUP_TOKEN: str = os.environ['group_token']
    GROUP_ID: str = os.environ['group_id']
    V: str = os.environ['V']

    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(bot)
    vk = VKAPI(ACCESS_TOKEN, GROUP_TOKEN, GROUP_ID, V)

    return bot, dp, vk, WHITE_LIST


async def send_welcome(message: types.Message) -> None:
    await message.reply("Привет! Отправлю твои посты в ВК")


async def handle_photo(
    message: types.Message, bot: Bot, vk: VKAPI, WHITE_LIST: Set[int]
):
    if message.chat.id not in WHITE_LIST:
        logger.error(f'Сообщение от чата {message.chat.id} не разрешены')
        return
    text = message.caption
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    await file.download()
    logger.debug(f'Загружен файл {file_path}')
    task = asyncio.create_task(vk.create_post_from_wall(file_path, text))
    logger.debug(f'Задача завершена {task}')


def main() -> None:
    try:
        logger.info('Запуск приложения')
        bot, dp, vk, WHITE_LIST = create_bot()
        dp.register_message_handler(send_welcome, commands=['start'])
        dp.register_channel_post_handler(
            lambda message: handle_photo(message, bot, vk, WHITE_LIST),
            content_types=ContentTypes.PHOTO,
        )
        asyncio.run(executor.start_polling(dp, skip_updates=True))
    except Exception as e:
        logger.critical(f'Необработанная ошибка: {e}')


if __name__ == '__main__':
    main()

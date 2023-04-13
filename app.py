import asyncio
import os
from my_logger import logger
from vk_bot import create_post_from_wall
from aiogram.utils import executor
from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentTypes
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
WHITE_LIST = [int(x) for x in os.getenv('WHITE_LIST').split(',')]


def check_environment_variables():
    load_dotenv()
    api_token = os.getenv('API_TOKEN')
    white_list = os.getenv('WHITE_LIST')
    if not api_token:
        raise ValueError(
            'API_TOKEN is not defined in the environment variables'
        )
    if not white_list:
        raise ValueError(
            'WHITE_LIST is not defined in the environment variables'
        )
    return True


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Отправлю твои посты в ВК")


@dp.channel_post_handler(content_types=ContentTypes.PHOTO)
async def handle_photo(message: types.Message):
    if message.chat.id not in WHITE_LIST:
        return
    text = message.caption
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    await file.download()
    logger.info(f'Загружен файл {file_path}')
    create_post_from_wall(file_path, text)
    try:
        os.remove(file_path)
        logger.debug(f"File {file_path} was successfully removed")

    except OSError as e:
        logger.debug(f"Error while removing file {file_path}: {e.strerror}")


if __name__ == '__main__':
    if check_environment_variables():
        logger.info('Start App')
        loop = asyncio.get_event_loop()
        executor.start_polling(dp, loop=loop, skip_updates=True)
        logger.info('Finish App')
    logger.critical('Ошибка при запуске приложения')
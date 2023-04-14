import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentTypes
from aiogram.utils import executor
from dotenv import load_dotenv

from my_logger import logger
from vk_bot import create_post_from_wall

API_TOKEN = os.environ['API_TOKEN']
WHITE_LIST = {int(x) for x in os.environ['WHITE_LIST'].split(',')}

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Отправлю твои посты в ВК")


@dp.channel_post_handler(content_types=ContentTypes.PHOTO)
async def handle_photo(message: types.Message):
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
    await create_post_from_wall(file_path, text)


def main():
    load_dotenv()
    logger.info('Запуск приложения')
    asyncio.run(
        executor.start_polling(
            dp, loop=asyncio.get_event_loop(), skip_updates=True
        )
    )


if __name__ == '__main__':
    main()

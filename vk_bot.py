import asyncio
import os
from typing import Dict

from dotenv import load_dotenv
from requests import Session

from my_logger import logger

load_dotenv()


V = os.environ['V']
ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
GROUP_TOKEN = os.environ['GROUP_TOKEN']
GROUP_ID = os.environ['GROUP_ID']


session = Session()


def get_upload_url() -> str:
    upload_server_response = session.post(
        url='https://api.vk.com/method/photos.getWallUploadServer',
        params={
            'access_token': ACCESS_TOKEN,
            'group_id': GROUP_ID,
            'v': V,
        },
    ).json()
    logger.debug(f"get_upload_url response: {upload_server_response}")
    try:
        return upload_server_response['response']['upload_url']
    except KeyError as e:
        logger.error(f"Ошибка получения URL для загрузки: {str(e)}")
        raise


def upload_image(upload_url: str, file_path: str) -> Dict[str, str]:
    with open(file_path, 'rb') as file:
        files = {'file': file}
        upload_response = session.post(url=upload_url, files=files).json()
        logger.debug(f"upload_image response: {upload_response}")
    try:
        return (
            upload_response['server'],
            upload_response['photo'],
            upload_response['hash'],
        )
    except KeyError as e:
        logger.error(f"Ошибка загрузки изображения: {str(e)}")
        raise


def post_save_wall_photo(server: int, photo: str, hash: str) -> str:
    save_response = session.post(
        url='https://api.vk.com/method/photos.saveWallPhoto',
        params={
            'access_token': ACCESS_TOKEN,
            'group_id': GROUP_ID,
            'server': server,
            'photo': photo,
            'hash': hash,
            'v': V,
        },
    ).json()
    logger.debug(f"post_save_wall_photo response: {save_response}")
    try:
        photo_attachment = (
            f"photo{save_response['response'][0]['owner_id']}"
            f"_{save_response['response'][0]['id']}"
        )
        return photo_attachment
    except KeyError as e:
        logger.error(f"Ошибка сохранения изображения: {str(e)}")
        raise


def wall_post(photo_attachment: str, message: str) -> Dict[str, str]:
    post_response = session.post(
        url='https://api.vk.com/method/wall.post',
        params={
            'access_token': GROUP_TOKEN,
            'v': V,
        },
        data={
            'owner_id': -int(GROUP_ID),
            'message': message,
            'attachments': photo_attachment,
        },
    ).json()
    logger.debug(f"Публикация поста на стене : {post_response}")
    try:
        return post_response
    except KeyError as e:
        logger.error(f"Ошибка публикации поста на стене: {str(e)}")
        raise


async def create_post_from_wall(file_path, message):
    try:
        upload_url = get_upload_url()
        server, photo, hash = upload_image(upload_url, file_path)
        photo_attachment = post_save_wall_photo(server, photo, hash)
        result = wall_post(photo_attachment, message)
        logger.info(result)
        await asyncio.to_thread(os.remove, file_path)
        logger.debug(f"Файл {file_path} был удален")
        return result
    except KeyError as e:
        logger.error(f"Ошибка создания поста на стены: {str(e)}")

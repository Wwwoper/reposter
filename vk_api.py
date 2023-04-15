import asyncio
import os
from dataclasses import dataclass
from typing import Dict, Optional

from dotenv import load_dotenv
from requests import Session

from my_logger import logger

load_dotenv()


@dataclass
class VKAPI:
    ACCESS_TOKEN: str
    GROUP_TOKEN: str
    GROUP_ID: str
    V: str
    session: Session = Session()

    async def create_post_from_wall(
        self, file_path: str, message: str
    ) -> Optional[int]:
        try:
            upload_url = self._get_upload_url()
            server, photo, hash = self._upload_image(upload_url, file_path)
            photo_attachment = self._post_save_wall_photo(server, photo, hash)
            result = self._wall_post(photo_attachment, message)
            logger.info(result)
            await asyncio.to_thread(os.remove, file_path)
            logger.debug(
                f"Файл для поста {file_path} был удален после публикации"
            )
            return result
        except KeyError as e:
            logger.error(f"Ошибка создания поста на стены: {str(e)}")

    def _get_upload_url(self) -> str:
        upload_server_response: Dict[str, str] = self.session.post(
            url='https://api.vk.com/method/photos.getWallUploadServer',
            params={
                'access_token': self.ACCESS_TOKEN,
                'group_id': self.GROUP_ID,
                'v': self.V,
            },
        ).json()
        logger.debug(f"get_upload_url response: {upload_server_response}")
        try:
            return upload_server_response['response']['upload_url']
        except KeyError as e:
            logger.error(f"Ошибка получения URL для загрузки: {str(e)}")
            raise

    def _upload_image(self, upload_url: str, file_path: str) -> Dict[str, str]:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            upload_response = self.session.post(
                url=upload_url, files=files
            ).json()
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

    def _post_save_wall_photo(self, server: int, photo: str, hash: str) -> str:
        save_response = self.session.post(
            url='https://api.vk.com/method/photos.saveWallPhoto',
            params={
                'access_token': self.ACCESS_TOKEN,
                'group_id': self.GROUP_ID,
                'server': server,
                'photo': photo,
                'hash': hash,
                'v': self.V,
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

    def _wall_post(
        self, photo_attachment: str, message: str
    ) -> Dict[str, str]:
        post_response = self.session.post(
            url='https://api.vk.com/method/wall.post',
            params={
                'access_token': self.GROUP_TOKEN,
                'v': self.V,
            },
            data={
                'owner_id': -int(self.GROUP_ID),
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

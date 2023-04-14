import unittest
from unittest.mock import patch, Mock
from vk_bot import (
    get_upload_url,
    upload_image,
    post_save_wall_photo,
    wall_post,
    create_post_from_wall,
)


class MyTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock()

    @patch('vk_bot.session')
    def test_get_upload_url(self, mock_session):
        mock_session.post.return_value.json.return_value = {
            'response': {'upload_url': 'https://test.com'}
        }
        url = get_upload_url()
        self.assertEqual(url, 'https://test.com')

    @patch('vk_bot.session')
    def test_upload_image(self, mock_session):
        mock_session.post.return_value.json.return_value = {
            'server': 123,
            'photo': 'test',
            'hash': '123abc',
        }
        url = 'https://test.com'
        file_path = 'tests/photos/test.jpg'
        result = upload_image(url, file_path)
        self.assertEqual(result, (123, 'test', '123abc'))

    @patch('vk_bot.session')
    def test_post_save_wall_photo(self, mock_session):
        mock_session.post.return_value.json.return_value = {
            'response': [{'owner_id': 123, 'id': 456}]
        }
        server = 123
        photo = 'test'
        hash = '123abc'
        attachment = post_save_wall_photo(server, photo, hash)
        self.assertEqual(attachment, 'photo123_456')

    @patch('vk_bot.session')
    def test_wall_post(self, mock_session):
        mock_session.post.return_value.json.return_value = {
            'response': {'post_id': 123}
        }
        attachment = 'photo123_456'
        message = 'test message'
        result = wall_post(attachment, message)
        self.assertEqual(result, {'response': {'post_id': 123}})

    @patch('vk_bot.get_upload_url')
    @patch('vk_bot.upload_image')
    @patch('vk_bot.post_save_wall_photo')
    @patch('vk_bot.wall_post')
    def test_create_post_from_wall(
        self,
        mock_wall_post,
        mock_post_save_wall_photo,
        mock_upload_image,
        mock_get_upload_url,
    ):
        mock_get_upload_url.return_value = 'https://test.com'
        mock_upload_image.return_value = (123, 'test', '123abc')
        mock_post_save_wall_photo.return_value = 'photo123_456'
        mock_wall_post.return_value = {'post_id': 123}

        file_path = '/path/to/test.jpg'
        message = 'test message'
        result = create_post_from_wall(file_path, message)

        self.assertEqual(result, {'post_id': 123})

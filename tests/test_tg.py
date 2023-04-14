import os
import unittest
from dotenv import load_dotenv
from app import check_environment_variables


class TestCheckEnvironmentVariables(unittest.TestCase):
    def setUp(self):
        load_dotenv()
        self.old_api_token = os.getenv('API_TOKEN')
        self.old_white_list = os.getenv('WHITE_LIST')

    def tearDown(self):
        os.environ['API_TOKEN'] = self.old_api_token
        os.environ['WHITE_LIST'] = self.old_white_list

    def test_api_token_missing(self):
        os.environ.pop('API_TOKEN', None)
        with self.assertRaises(ValueError):
            check_environment_variables()

    def test_white_list_missing(self):
        os.environ['API_TOKEN'] = 'dummy_token'
        os.environ.pop('WHITE_LIST', None)
        with self.assertRaises(ValueError):
            check_environment_variables()

    def test_both_variables_present(self):
        os.environ['API_TOKEN'] = 'dummy_token'
        os.environ['WHITE_LIST'] = '123,456'
        self.assertIsNone(check_environment_variables())


if __name__ == '__main__':
    unittest.main()

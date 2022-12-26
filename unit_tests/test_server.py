import unittest
import os
import sys
import time
sys.path.append(os.path.join(os.getcwd(),".."))
from server import process_client_message
from common import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE

class TestServer(unittest.TestCase):

    err_dict = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }

    ok_dict = {RESPONSE: 200}

    def setUp(self):

        self.presence_success_msg = {
                    ACTION: PRESENCE,
                    TIME: time.time(),                    
                    USER: {
                            ACCOUNT_NAME: 'Guest',
                         }
                    }


    def test_process_client_message_dict(self):
        self.assertIsInstance(process_client_message(self.presence_success_msg), dict)

    #from practic, no changes    

    def test_no_action(self):
        """Ошибка если нет действия"""
        self.assertEqual(process_client_message(
            {TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}), self.err_dict)

    def test_wrong_action(self):
        """Ошибка если неизвестное действие"""
        self.assertEqual(process_client_message(
            {ACTION: 'Wrong', TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}), self.err_dict)

    def test_no_time(self):
        """Ошибка, если  запрос не содержит штампа времени"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}), self.err_dict)

    def test_no_user(self):
        """Ошибка - нет пользователя"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '1.1'}), self.err_dict)

    def test_unknown_user(self):
        """Ошибка - не Guest"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest1'}}), self.err_dict)

    def test_ok_check(self):
        """Корректный запрос"""
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}), self.ok_dict)

    #variant 2

    def test_process_client_message_presence(self):
        self.assertEqual(process_client_message(self.presence_success_msg)['response'], 200)


if __name__ == '__main__':
    unittest.main()

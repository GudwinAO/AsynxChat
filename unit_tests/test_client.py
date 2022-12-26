# 1. Для всех функций из урока 3 написать тесты с использованием unittest. Они должны быть
# оформлены в отдельных скриптах с префиксом test_ в имени файла (например, test_client.py)

import unittest
import os
import sys
sys.path.append(os.path.join(os.getcwd(),".."))
from client import create_presence, process_ans
from common import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE

class TestClass(unittest.TestCase):
    

    def test_create_presence_type_dict(self):
        self.assertIsInstance(create_presence(), dict)

    def test_create_presence(self):
        test_presence = create_presence()

        # меняем время на постоянное для теста
        test_presence[TIME] = 999

        self.assertEqual(test_presence,
                         {
                             ACTION: PRESENCE,
                             TIME: 999,
                             USER: {
                                 ACCOUNT_NAME: 'Guest'
                                }
                         }
                        )

    def test_create_presence_user_type_dict(self):
        test_presence = create_presence()
        self.assertIsInstance(test_presence['user'], dict)

    def test_create_presence_num_keys(self):
        test_presence = create_presence()
        self.assertEqual(len(test_presence.keys()), 4)


    def test_process_ans_200(self):
        self.assertEqual(process_ans({RESPONSE:200}), '200 : OK')

    def test_process_ans_400(self):
        self.assertEqual(process_ans({RESPONSE:400, ERROR: 'Bad Request'}), '400 : Bad Request')
      
     
    def test_no_response(self):
        self.assertRaises(ValueError, process_ans, {ERROR: 'Bad Request'})


if __name__ == '__main__':
    unittest.main()


    

    
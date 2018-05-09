from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import input
from builtins import filter
from builtins import str
import unittest
import cow_rest
import configparser
import uuid
import os
from pathlib import Path

AUTH_TEST = False

config = configparser.ConfigParser()
CONFIG_FILE = "test.cfg"
config_file_path = Path(CONFIG_FILE)

TEXT_LOGIN_FAILED = "Login failed / Invalid auth token"
CODE_LOGIN_FAILED = "98"


@unittest.skipIf(not config_file_path.is_file(), "Skip due to no config file")
class TestErrorReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if config_file_path.is_file():
            config.read(CONFIG_FILE)
            cow_rest.api_key = config.get('auth', 'api_key')
            cow_rest.secret = config.get('auth', 'secret')
        cow_rest.auth_token = "hello"

    def test_get_list(self):
        list_id, error_text, error_code = cow_rest.get_list()
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_get_timeline(self):
        error_text, error_code = cow_rest.get_timeline(cow_rest)
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_get_new_token(self):
        cow_rest.frob = "0"
        error_text, error_code = cow_rest.get_new_token(cow_rest)
        self.assertEqual(error_text, "Invalid frob - did you authenticate?")
        self.assertEqual(error_code, "101")

    def test_verify_token_validity(self):
        error_text, error_code = cow_rest.verify_token_validity()
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_add_task(self):
        cow_rest.timeline = "0"
        taskseries_id, task_id, error_text, error_code = cow_rest.add_task("test", "0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)
        self.assertEqual(task_id, None)

    def test_roll_back(self):
        cow_rest.timeline = "0"
        error_text, error_code = cow_rest.roll_back("0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_task_list(self):
        cow_rest.timeline = "0"
        taskseries, error_text, error_code = cow_rest.list_task("0", "0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)
        self.assertEqual(taskseries, None)

    def test_delete_task(self):
        cow_rest.timeline = "0"
        transaction_id, error_text, error_code = cow_rest.delete_task("0", "0", "0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)
        self.assertEqual(transaction_id, None)


@unittest.skipIf(not config_file_path.is_file(),"Skip due to no config file")
class TestOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if config_file_path.is_file():
            config.read(CONFIG_FILE)
            cow_rest.api_key = config.get('auth', 'api_key')
            cow_rest.secret = config.get('auth', 'secret')
        cow_rest.auth_token = None

    def test_add_remove_item_to_list(self):
        task_name = "Cows Lists test item: " + str(uuid.uuid1())
        print("Working on item:" + task_name)

        cow_rest.get_token(cow_rest)
        self.assertNotEqual(cow_rest.auth_token, None)

        error_text, error_code = cow_rest.verify_token_validity()
        self.assertEqual(error_text, None)

        error_text, error_code = cow_rest.get_timeline(cow_rest)
        self.assertEqual(error_text, None)
        self.assertNotEqual(cow_rest.timeline, None)

        # Get all lists
        list_result, error_text, error_code = cow_rest.get_list()
        self.assertEqual(error_text, None)

        list_id = [x for x in list_result if str(x['name']).lower() == "inbox"][0]['id']

        # add an item
        taskseries_id, task_id, error_text, error_code = cow_rest.add_task(task_name, list_id)
        self.assertEqual(error_text, None)
        self.assertNotEqual(task_id, None)

        # check item was added
        task_list, error_code, error_text = cow_rest.list_task("status:incomplete", list_id)
        self.assertEqual(error_text, None)

        task_match = cow_rest.find_task_id(task_list, taskseries_id, task_id)

        self.assertNotEqual(task_match, None)  # assuming RTM make unique tasks

        # check flat list
        flat_task_list = cow_rest.flat_task_list(task_list)
        self.assertTrue(len([x for x in flat_task_list if x['task_name'] == task_name
                                             and x['taskseries_id'] == taskseries_id
                                             and x['task_id'] == task_id]) > 0)

        # mark task as complete
        transaction_id, error_text, error_code = cow_rest.complete_task(task_id, taskseries_id, list_id)
        self.assertEqual(error_text, None)
        self.assertNotEqual(transaction_id, None)

        # check item is completed
        task_list, error_code, error_text = cow_rest.list_task("status:completed", list_id)
        self.assertEqual(error_text, None)

        task_match = cow_rest.find_task_id(task_list, taskseries_id, task_id)
        self.assertNotEqual(task_match, None)  # assuming RTM make unique tasks

        # roll back
        error_text, error_code = cow_rest.roll_back(str(transaction_id))
        self.assertEqual(error_text, None)

        # check item was set back to incomplete
        task_list, error_code, error_text = cow_rest.list_task("status:incomplete", list_id)
        self.assertEqual(error_text, None)

        task_match = cow_rest.find_task_id(task_list, taskseries_id, task_id)
        self.assertNotEqual(task_match, None)  # assuming RTM make unique tasks

        # delete the item
        transaction_id, error_text, error_code = cow_rest.delete_task(task_id, taskseries_id, list_id)
        self.assertEqual(error_text, None)
        self.assertNotEqual(transaction_id, None)

        # check item was deleted
        task_list, error_code, error_text = cow_rest.list_task("status:incomplete", list_id)
        self.assertEqual(error_text, None)

        task_match = cow_rest.find_task_id(task_list, taskseries_id, task_id)
        self.assertEqual(task_match, None)  # assuming RTM make unique tasks


@unittest.skipIf(not config_file_path.is_file() or not AUTH_TEST,"Skip due to no config file")
class TestAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if config_file_path.is_file():
            config.read(CONFIG_FILE)
            cow_rest.api_key = config.get('auth', 'api_key')
            cow_rest.secret = config.get('auth', 'secret')
        cow_rest.auth_token = None

    def test_auth(self):
        error_text, error_code = cow_rest.get_frob(cow_rest)
        self.assertEqual(error_text, None)
        self.assertEqual(error_code, None)

        auth_url = cow_rest.get_auth_url()
        print("Authentication link")
        print(auth_url)
        print("Copy/paste URL then hit return")
        input()

        error_text, error_code = cow_rest.get_new_token(cow_rest)

        self.assertEqual(error_text, None)
        self.assertNotEqual(cow_rest.auth_token, None)


if __name__ == '__main__':
    unittest.main()

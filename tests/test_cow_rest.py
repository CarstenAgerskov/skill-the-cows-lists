import unittest
from cow_rest import *
import ConfigParser
import uuid

AUTH_TEST = False

config = ConfigParser.ConfigParser()

CONFIG_FILE = "test.cfg"

TEXT_LOGIN_FAILED = "Login failed / Invalid auth token"
CODE_LOGIN_FAILED = "98"


@unittest.skipIf(AUTH_TEST, "Skip error test")
class TestErrorReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.read(CONFIG_FILE)
        RtmParam().reset_param()
        RtmParam.api_key = config.get('auth', 'api_key')
        RtmParam.secret = config.get('auth', 'secret')
        RtmParam.auth_token = "hello"

    def test_get_list(self):
        list_id, error_text, error_code = get_list()
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_get_timeline(self):
        error_text, error_code = get_timeline()
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_get_new_token(self):
        RtmParam.frob = "0"
        error_text, error_code = get_new_token()
        self.assertEqual(error_text, "Invalid frob - did you authenticate?")
        self.assertEqual(error_code, "101")

    def test_verify_token_validity(self):
        error_text, error_code = verify_token_validity()
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_add_task(self):
        RtmParam.timeline = "0"
        taskseries_id, task_id, error_text, error_code = add_task("test", "0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)
        self.assertEqual(task_id, None)

    def test_roll_back(self):
        RtmParam.timeline = "0"
        error_text, error_code = roll_back("0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)

    def test_task_list(self):
        RtmParam.timeline = "0"
        taskseries, error_text, error_code = list_task("0", "0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)
        self.assertEqual(taskseries, None)

    def test_delete_task(self):
        RtmParam.timeline = "0"
        transaction_id, error_text, error_code = delete_task("0", "0", "0")
        self.assertEqual(error_text, TEXT_LOGIN_FAILED)
        self.assertEqual(error_code, CODE_LOGIN_FAILED)
        self.assertEqual(transaction_id, None)


@unittest.skipIf(AUTH_TEST, "Skip operation test")
class TestOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.read(CONFIG_FILE)
        RtmParam().reset_param()
        RtmParam.api_key = config.get('auth', 'api_key')
        RtmParam.secret = config.get('auth', 'secret')
        RtmParam.auth_token = None

    def test_add_remove_item_to_list(self):
        task_name = "Cows Lists test item: " + str(uuid.uuid1())
        print "Working on item:" + task_name

        get_token()
        self.assertNotEqual(RtmParam.auth_token, None)

        error_text, error_code = verify_token_validity()
        self.assertEqual(error_text, None)

        error_text, error_code = get_timeline()
        self.assertEqual(error_text, None)
        self.assertNotEqual(RtmParam.timeline, None)

        # Get all lists
        list_result, error_text, error_code = get_list()
        self.assertEqual(error_text, None)

        list_id = filter(lambda x: str(x['name']).lower() == "inbox", list_result)[0]['id']

        # add an item
        taskseries_id, task_id, error_text, error_code = add_task(task_name, list_id)
        self.assertEqual(error_text, None)
        self.assertNotEqual(task_id, None)

        # check item was added
        task_list, error_code, error_text = list_task("status:incomplete", list_id)
        self.assertEqual(error_text, None)

        task_match = find_task_id(task_list, taskseries_id, task_id)

        self.assertNotEqual(task_match, None)  # assuming RTM make unique tasks

        # mark task as complete
        transaction_id, error_text, error_code = complete_task(task_id, taskseries_id, list_id)
        self.assertEqual(error_text, None)
        self.assertNotEqual(transaction_id, None)

        # check item is completed
        task_list, error_code, error_text = list_task("status:completed", list_id)
        self.assertEqual(error_text, None)

        task_match = find_task_id(task_list, taskseries_id, task_id)
        self.assertNotEqual(task_match, None)  # assuming RTM make unique tasks

        # roll back
        error_text, error_code = roll_back(str(transaction_id))
        self.assertEqual(error_text, None)

        # check item was set back to incomplete
        task_list, error_code, error_text = list_task("status:incomplete", list_id)
        self.assertEqual(error_text, None)

        task_match = find_task_id(task_list, taskseries_id, task_id)
        self.assertNotEqual(task_match, None)  # assuming RTM make unique tasks

        # delete the item
        transaction_id, error_text, error_code = delete_task(task_id, taskseries_id, list_id)
        self.assertEqual(error_text, None)
        self.assertNotEqual(transaction_id, None)

        # check item was deleted
        task_list, error_code, error_text = list_task("status:incomplete", list_id)
        self.assertEqual(error_text, None)

        task_match = find_task_id(task_list, taskseries_id, task_id)
        self.assertEqual(task_match, None)  # assuming RTM make unique tasks


@unittest.skipUnless(AUTH_TEST, "skip auth test")
class TestAuto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.read(CONFIG_FILE)
        RtmParam().reset_param()
        RtmParam.api_key = config.get('auth', 'api_key')
        RtmParam.secret = config.get('auth', 'secret')
        RtmParam.auth_token = None

    def test_auth(self):
        error_text, error_code = get_frob()
        self.assertEqual(error_text, None)
        self.assertEqual(error_code, None)

        auth_url = get_auth_url()
        print "Authentication link"
        print auth_url
        print "Copy/paste URL then hit return"
        raw_input()

        error_text, error_code = get_new_token()

        self.assertEqual(error_text, None)
        self.assertNotEqual(RtmParam.auth_token, None)


if __name__ == '__main__':
    unittest.main()

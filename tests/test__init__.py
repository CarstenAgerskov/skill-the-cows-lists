import ConfigParser
import json
import unittest
import uuid
import cow_rest
from mock import patch, ANY
from mycroft.messagebus.message import Message
from __init__ import CowsLists

UNDO_CONTEXT = "UndoContext"
CONFIRM_CONTEXT = "ConfirmContext"

config = ConfigParser.ConfigParser()

CONFIG_FILE = "test.cfg"
TASK_PARAMETER = "taskName"
LIST_PARAMETER = "listName"


# @unittest.skip("Skip test missing token")
class TestOperationInit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')

    def test_missing_token(self):
        with patch('__init__.cow_rest.get_token'), \
             patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, "task")
            message.data.setdefault(LIST_PARAMETER, "inbox")

            cow_rest.auth_token = None
            self.assertFalse(self.cowsLists.operation_init())
            mock_speak_dialog.assert_called_with('NotAuthenticated')

            cow_rest.frob = "0"
            self.assertFalse(self.cowsLists.operation_init())
            mock_speak_dialog.assert_called_with('InAuthentication')


# @unittest.skip("Skip test missing token")
class TestAuthenticateIntent(unittest.TestCase):  # assuming a valid token in test.cfg
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')

    def test_token_valid(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context:
            cow_rest.auth_token = None  # Get token from config
            self.assertFalse(self.cowsLists.authenticate_intent())
            mock_speak_dialog.assert_called_with('TokenValid')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_none(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'), \
                patch('__init__.CowsLists.send_email') as mock_send_email:
            cow_rest.auth_token = None
            self.assertFalse(self.cowsLists.authenticate_intent())
            mock_speak_dialog.assert_called_with('EmailSent')
            mock_send_email.assert_called_with('Authentication', ANY)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_invalid(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'), \
                patch('__init__.CowsLists.send_email') as mock_send_email:
            cow_rest.auth_token = "0"
            self.assertFalse(self.cowsLists.authenticate_intent())
            mock_speak_dialog.assert_called_with('EmailSent')
            mock_send_email.assert_called_with('Authentication', ANY)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)


# @unittest.skip("Skip GetTokenIntent")
class TestGetTokenIntent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')

    def test_valid_token(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context:
            cow_rest.auth_token = None  # Get token from config
            self.cowsLists.get_token_intent()
            mock_speak_dialog.assert_called_with('TokenValid')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_none_frob_none(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'):
            cow_rest.auth_token = None
            cow_rest.frob = None
            self.cowsLists.get_token_intent()
            mock_speak_dialog.assert_called_with('AuthenticateBeforeToken')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_invalid_frob_none(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'):
            cow_rest.auth_token = "0"
            cow_rest.frob = None
            self.cowsLists.get_token_intent()
            mock_speak_dialog.assert_called_with('AuthenticateBeforeToken')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_none_frob_fake(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'), \
                patch('__init__.cow_rest.get_new_token') as mock_get_new_token:
            cow_rest.auth_token = None
            cow_rest.frob = "0"
            mock_get_new_token.return_value = None, None
            self.cowsLists.get_token_intent()
            mock_speak_dialog.assert_called_with("GotToken")
            mock_remove_context.assert_called_with(UNDO_CONTEXT)


# @unittest.skip("Skip TestAddTaskToList")
class TestAddTaskToList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name = "Cows Lists test item: " + str(uuid.uuid1())
        print "Using task :" + cls.task_name

    def test_list_match(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, "inbox")
            cow_rest.auth_token = None  # get token from config
            self.cowsLists.add_task_to_list_intent(message)
            mock_remove_context.assert_any_call(CONFIRM_CONTEXT)
            mock_remove_context.assert_any_call(UNDO_CONTEXT)
            mock_set_context.assert_called_with(UNDO_CONTEXT, ANY)
            mock_speak_dialog.assert_called_with("AddTaskToList", ANY)
            c = json.loads(mock_set_context.call_args_list[0][0][1])
            self.assertEqual(str(c['dialog']), "AddTaskToListUndo")

            # Remove task again
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, mock_set_context.call_args_list[0][0][1])
            self.cowsLists.undo_intent(message)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            mock_speak_dialog.assert_called_with("AddTaskToListUndo", ANY)

    def test_list_match_list(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            # test that a list name of 'test' will match 'test list'. Since the word list is lost in translation
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, "test")
            self.cowsLists.add_task_to_list_intent(message)
            mock_remove_context.assert_any_call(CONFIRM_CONTEXT)
            mock_remove_context.assert_any_call(UNDO_CONTEXT)
            mock_set_context.assert_called_with(UNDO_CONTEXT, ANY)
            mock_speak_dialog.assert_called_with("AddTaskToList", ANY)
            c = json.loads(mock_set_context.call_args_list[0][0][1])
            self.assertEqual(str(c['dialog']), "AddTaskToListUndo")

            # Remove task again
            message.data.setdefault(UNDO_CONTEXT, mock_set_context.call_args_list[0][0][1])
            self.cowsLists.undo_intent(message)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            mock_speak_dialog.assert_called_with("AddTaskToListUndo", ANY)

    def test_list_match_best(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, "binbox")
            self.cowsLists.add_task_to_list_intent(message)
            mock_remove_context.assert_any_call(CONFIRM_CONTEXT)
            mock_remove_context.assert_any_call(UNDO_CONTEXT)
            mock_set_context.assert_called_with("ConfirmContext", ANY)
            mock_speak_dialog.assert_called_with("AddTaskToListMismatch", ANY, expect_response=True)
            c = json.loads(mock_set_context.call_args_list[0][0][1])
            self.assertEqual(str(c['dialog']), "AddTaskToList")

            message.data.setdefault(CONFIRM_CONTEXT, mock_set_context.call_args_list[0][0][1])
            self.cowsLists.confirm_intent(message)
            mock_remove_context.assert_called_with(CONFIRM_CONTEXT)
            mock_set_context.assert_called_with(UNDO_CONTEXT, ANY)
            mock_speak_dialog.assert_called_with("AddTaskToList", ANY)
            c = json.loads(mock_set_context.call_args_list[1][0][1])
            self.assertEqual(str(c['dialog']), "AddTaskToListUndo")

            # Remove task again
            message.data.setdefault(UNDO_CONTEXT, mock_set_context.call_args_list[1][0][1])
            self.cowsLists.undo_intent(message)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            mock_speak_dialog.assert_called_with("AddTaskToListUndo", ANY)


# @unittest.skip("Skip TestReadList")
class TestReadList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name = "Cows Lists test item: " + str(uuid.uuid1())
        cls.list_name = 'test list'
        print "Using task :" + cls.task_name

    def test_read_list(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak') as mock_speak:
            cow_rest.auth_token = None  # get token from config
            cow_rest.timeline = None # First call without timeline
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, self.list_name)

            # Read empty list
            self.cowsLists.read_list_intent(message)
            mock_speak_dialog.assert_any_call("NoTaskOnList", ANY)
            mock_speak_dialog.reset_mock()

            # Add task to list
            self.cowsLists.add_task_to_list_intent(message)
            timeline = cow_rest.timeline
            mock_speak_dialog.reset_mock()

            # Read one item
            self.cowsLists.read_list_intent(message)
            mock_speak_dialog.assert_any_call("ReadListOneItem", ANY)
            mock_speak.assert_any_call(self.task_name)

            # Add identical task to list
            self.cowsLists.add_task_to_list_intent(message)
            timeline = cow_rest.timeline
            mock_speak_dialog.reset_mock()

            # Read more than one item nomatch list
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, self.list_name + 'x')
            self.cowsLists.read_list_intent(message)
            mock_speak_dialog.assert_any_call("ReadList", ANY)
            mock_speak_dialog.assert_any_call("UsingAnotherList", ANY)
            mock_speak.assert_any_call(self.task_name)

            # Remove task again
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            self.cowsLists.complete_task_on_list_intent(message)
            mock_speak_dialog.assert_any_call("CompleteManyTasksOnList", ANY)


# @unittest.skip("Skip TestFindTaskOnList")
class TestFindTaskOnList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name = "Cows Lists test item: " + str(uuid.uuid1())
        print "Using task :" + cls.task_name

    def test_find_task(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            # Add test task
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, "inbox")
            cow_rest.auth_token = None  # get token from config
            self.cowsLists.add_task_to_list_intent(message)
            mock_speak_dialog.assert_called_with("AddTaskToList", ANY)

            # Find task match and list match
            mock_speak_dialog.reset_mock()
            self.cowsLists.find_task_on_list_intent(message)
            mock_speak_dialog.assert_called_with("FindTaskOnList", ANY)
            mock_speak_dialog.assert_called_once()

            # find task nomatch and list match
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, "x" + self.task_name)
            message.data.setdefault(LIST_PARAMETER, "inbox")
            mock_speak_dialog.reset_mock()
            self.cowsLists.find_task_on_list_intent(message)
            mock_speak_dialog.assert_any_call("FindTaskOnListMismatch", ANY)
            mock_speak_dialog.assert_called_once()

            # find any task on list nomatch
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, "x" + self.task_name)
            message.data.setdefault(LIST_PARAMETER, "inbox" + str(uuid.uuid1()))
            self.cowsLists.find_task_on_list_intent(message)
            mock_speak_dialog.assert_any_call("UsingAnotherList", ANY)

            # Remove task again
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, mock_set_context.call_args_list[0][0][1])
            self.cowsLists.undo_intent(message)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            mock_speak_dialog.assert_called_with("AddTaskToListUndo", ANY)


# @unittest.skip("Skip CompleteTaskOnList")
class CompleteTaskOnList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name = "Cows Lists test item: " + str(uuid.uuid1())
        cls.list_name = 'test list'
        print "Using task :" + cls.task_name

    def test_find_task(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak') as mock_speak, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            # Complete non existent task - empty list
            cow_rest.auth_token = None  # get token from config
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            self.cowsLists.complete_task_on_list_intent(message)
            mock_speak_dialog.assert_called_with("NoTaskOnList", ANY)
            mock_speak_dialog.assert_called_once()
            mock_speak_dialog.reset_mock()

            # Add test task
            self.cowsLists.add_task_to_list_intent(message)
            mock_speak_dialog.assert_called_with("AddTaskToList", ANY)
            mock_speak_dialog.reset_mock()

            # Complete task
            mock_set_context.reset_mock()
            self.cowsLists.complete_task_on_list_intent(message)
            mock_speak_dialog.assert_called_with("CompleteTaskOnList", ANY)
            mock_speak_dialog.assert_called_once()
            self.assertEqual(mock_speak_dialog.call_args_list[0][0][1]['listName'], self.list_name)
            self.assertEqual(mock_speak_dialog.call_args_list[0][0][1]['taskName'], self.task_name.lower())
            mock_speak_dialog.reset_mock()

            # Undo
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, mock_set_context.call_args_list[0][0][1])
            self.cowsLists.undo_intent(message)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            mock_speak_dialog.assert_called_with("CompleteTaskOnListUndo", ANY)
            mock_speak_dialog.reset_mock()

            # Add new identical test task
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            self.cowsLists.add_task_to_list_intent(message)
            mock_speak_dialog.assert_called_with("AddTaskToList", ANY)
            mock_speak_dialog.reset_mock()

            # Complete task nomatch and list match
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name + 'x')
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            self.cowsLists.complete_task_on_list_intent(message)
            mock_speak_dialog.assert_any_call("FindTaskOnListMismatch", ANY)
            mock_speak_dialog.assert_any_call("CompleteManyTasksOnList", ANY)
            self.assertEqual(mock_speak_dialog.call_args_list[1][0][1]['nofTask'], '2')
            self.assertEqual(mock_speak_dialog.call_args_list[1][0][1]['listName'], self.list_name)
            self.assertEqual(mock_speak_dialog.call_args_list[1][0][1]['taskName'], self.task_name.lower())
            mock_speak_dialog.reset_mock()

            # Undo
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, mock_set_context.call_args_list[0][0][1])
            self.cowsLists.undo_intent(message)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            mock_speak_dialog.assert_called_with("CompleteTaskOnListUndo", ANY)
            mock_speak_dialog.reset_mock()

            # Check both tasks complete undone
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            self.cowsLists.read_list_intent(message)
            self.assertEqual(mock_speak_dialog.call_args_list[0][0][1]['nofTask'], '2')
            mock_speak_dialog.reset_mock()

            # Add third identical test task
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            self.cowsLists.add_task_to_list_intent(message)
            mock_speak_dialog.assert_called_with("AddTaskToList", ANY)
            mock_speak_dialog.reset_mock()

            # Complete any task on list nomatch
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(TASK_PARAMETER, self.task_name)
            message.data.setdefault(LIST_PARAMETER, self.list_name + str(uuid.uuid1()) + 'x')
            mock_speak_dialog.reset_mock()
            self.cowsLists.complete_task_on_list_intent(message)
            mock_speak_dialog.assert_any_call("CompleteManyTasksOnList", ANY)
            mock_speak_dialog.assert_any_call("UsingAnotherList", ANY)
            self.assertEqual(mock_speak_dialog.call_args_list[1][0][1]['nofTask'], '3')
            self.assertEqual(mock_speak_dialog.call_args_list[1][0][1]['listName'], self.list_name)
            self.assertEqual(mock_speak_dialog.call_args_list[1][0][1]['taskName'], self.task_name.lower())

if __name__ == '__main__':
    unittest.main()

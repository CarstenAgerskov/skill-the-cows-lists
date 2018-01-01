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


#@unittest.skip("Skip test missing token")
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


#@unittest.skip("Skip test missing token")
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


#@unittest.skip("Skip GetTokenIntent")
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


#@unittest.skip("Skip TestAddTaskToList")
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
            mock_speak_dialog.assert_called_with("AddTaskToListMismatch", ANY)
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

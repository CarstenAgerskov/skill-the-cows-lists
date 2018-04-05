import ConfigParser
import json
import unittest
import uuid
import cow_rest
from mock import patch, ANY
from mycroft.messagebus.message import Message
from __init__ import CowsLists
from collections import namedtuple


TASK_PARAMETER = "taskName"
LIST_PARAMETER = "listName"
BEST_MATCH_PARAMETER = "bestMatch"
ERROR_TEXT_PARAMETER = "errorText"
ERROR_CODE_PARAMETER = "errorCode"
FUNCTION_NAME_PARAMETER = "functionName"
LINE_PARAMETER = "lineNumber"
NOF_TASK_PARAMETER = "nofTask"
DUE_PARAMETER = "dueDate"
UNDO_CONTEXT = "UndoContext"
EXCEPTION_CONTEXT = "ExceptionContext"
LIST_CONTEXT = "ListContext"
TASK_CONTEXT = "TaskContext"
REPEAT_ADD_TASK_CONTEXT = "RepeatAddTaskContext"
TEST_CONTEXT = "_TestContext"
MAX_TASK_COMPLETE = 40

config = ConfigParser.ConfigParser()

CONFIG_FILE = "test.cfg"
LANGUAGE = "en-us"


def test_add_task_to_list(self, task_name, list_tuple):
    with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, (
            patch('__init__.CowsLists.set_context')) as mock_set_context:
        self.assertTrue(
            self.cowsLists.add_task_to_list(task_name, list_tuple))
        mock_set_context.assert_any_call(UNDO_CONTEXT, ANY)
        mock_set_context.assert_called_with(TASK_CONTEXT, ANY)
        self.assertFalse('RestResponseError' in  mock_speak_dialog.call_args_list)

def test_find_list(self, list_name, match=False):
    with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, (
            patch('__init__.CowsLists.set_context')) as mock_set_context:
        list_best_match = self.cowsLists.find_list(list_name)
        mock_set_context.assert_called_with(LIST_CONTEXT, ANY)
        self.assertFalse('RestResponseError' in  mock_speak_dialog.call_args_list)
        if match:
            self.assertEqual(list_name, list_best_match.name)
        return list_best_match

def test_operation_init(self):
    self.assertTrue(self.cowsLists.operation_init())

def test_get_timeline(self):
    self.assertTrue(self.cowsLists.get_timeline())

def test_complete_list_explain(self, list_name, list_best_match):
    with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
          patch('__init__.CowsLists.set_context'), \
          patch('__init__.CowsLists.remove_context'):
        self.cowsLists.complete_list_explain(list_name, list_best_match)
        self.assertFalse('RestResponseError' in  mock_speak_dialog.call_args_list)

def test_find_task_on_list(self, task_name, list_name, match=False, no_match=False):
    with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, (
            patch('__init__.CowsLists.set_context')) as mock_set_context:
        task_best_match = self.cowsLists.find_task_on_list_explain(task_name, list_name)
        if match:
            self.assertEqual(task_name, task_best_match.name)
            self.assertEqual(list_name, task_best_match.list_best_match.name)
        if no_match:
            self.assertNotEqual(task_name, task_best_match.name)
            self.assertEqual(list_name, task_best_match.list_best_match.name)
        self.assertFalse('RestResponseError' in  mock_speak_dialog.call_args_list)
        mock_set_context.assert_any_call(LIST_CONTEXT, ANY)
        return task_best_match


def test_mock_call_sequence(self, verify_mock, dialog_sequence):
    seq=[]
    seq = map(lambda y: y[1][0],
              filter(lambda x: x[0] != '__str__', verify_mock.mock_calls))
    self.assertEqual(dialog_sequence, seq)
    print "Call sequence verified for " + str(verify_mock) + ": " + str(seq)

def get_mock_call_parameters(self, param_mock, first_param):
    s = filter(lambda z: z[0] == first_param,
               map(lambda y: y[1],
                   filter(lambda x: x[0] != '__str__',
                          param_mock.mock_calls)))
    return s[0][1]

def set_list_context(self, message, list_best_match):
    message.data.setdefault(LIST_CONTEXT,
                     json.dumps({'id': list_best_match.id,
                                 'name': list_best_match.name,
                                 'significance': list_best_match.significance}))

def set_task_context(self, message, task_best_match):
    message.data.setdefault(TASK_CONTEXT,
                    json.dumps({'id': task_best_match.id,
                               'name': task_best_match.name,
                               'taskseries_id': task_best_match.taskseries_id}))

def add_task_to_list_by_name(self, list_name, task_name):
    test_operation_init(self)
    test_get_timeline(self)
    list_best_match = test_find_list(self, list_name)
    test_add_task_to_list(self, task_name, list_best_match)


class TestFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_regex_evaluation_explain(self):
        # Set up interface
        test_operation_init(self)
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            message = Message(self)
            message.data.setdefault('utterance', 'not to be recognized')
            k, m = self.cowsLists.regex_evaluation_explain(message, ['ReadList'])
            self.assertEqual(m, None)
            test_mock_call_sequence(self, mock_speak_dialog,
                                    ['IDontUnderstand'])


#@unittest.skip("Skip TestOperationInit")
class TestOperationInit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')

    def test_operation_init(self):
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


#@unittest.skip("Skip TestAuthenticateIntent")
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
            message = Message(self)
            cow_rest.auth_token = None  # Get token from config
            self.assertFalse(self.cowsLists.authenticate_intent(message))
            mock_speak_dialog.assert_called_with('TokenValid')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_none(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'), \
                patch('__init__.CowsLists.send_email') as mock_send_email:
            message = Message(self)
            cow_rest.auth_token = None
            self.assertFalse(self.cowsLists.authenticate_intent(message))
            mock_speak_dialog.assert_called_with('EmailSent')
            mock_send_email.assert_called_with('Authentication', ANY)
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_invalid(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'), \
                patch('__init__.CowsLists.send_email') as mock_send_email:
            message = Message(self)
            cow_rest.auth_token = "0"
            self.assertFalse(self.cowsLists.authenticate_intent(message))
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
            message = Message(self)
            cow_rest.auth_token = None  # Get token from config
            self.cowsLists.get_token_intent(message)
            mock_speak_dialog.assert_called_with('TokenValid')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_none_frob_none(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'):
            message = Message(self)
            cow_rest.auth_token = None
            cow_rest.frob = None
            self.cowsLists.get_token_intent(message)
            mock_speak_dialog.assert_called_with('AuthenticateBeforeToken')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_invalid_frob_none(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'):
            message = Message(self)
            cow_rest.auth_token = "0"
            cow_rest.frob = None
            self.cowsLists.get_token_intent(message)
            mock_speak_dialog.assert_called_with('AuthenticateBeforeToken')
            mock_remove_context.assert_called_with(UNDO_CONTEXT)

    def test_token_none_frob_fake(self):
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.cow_rest.get_token'), \
                patch('__init__.cow_rest.get_new_token') as mock_get_new_token:
            message = Message(self)
            cow_rest.auth_token = None
            cow_rest.frob = "0"
            mock_get_new_token.return_value = None, None
            self.cowsLists.get_token_intent(message)
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
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_add_task_to_list(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        print "Add one task to an empty list"
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            task_name_1 = "test item: " + str(uuid.uuid1())
            message.data.setdefault(TASK_PARAMETER, task_name_1)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance', 'add ' + task_name_1 + ' to my ' + list_name + ' list')
            cow_rest.auth_token = None  # get token from config

            self.cowsLists.add_task_to_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['AddTaskToList'])
            c = json.loads(get_mock_call_parameters(self, mock_set_context, UNDO_CONTEXT))
            self.assertEqual('AddTaskToListUndo', str(c['dialog']))
            list_best_match = json.loads(get_mock_call_parameters(self, mock_set_context, LIST_CONTEXT))
            self.assertEqual(list_name, str(list_best_match['name']))
            task_best_match = json.loads(get_mock_call_parameters(self, mock_set_context, TASK_CONTEXT))
            self.assertEqual(task_name_1, str(task_best_match['name']))

            print "Add one taks to a nonempty list, list names do not match"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            task_name_2 = "test item: " + str(uuid.uuid1())
            message.data.setdefault(TASK_PARAMETER, task_name_2)
            message.data.setdefault(LIST_PARAMETER, list_name+'x')
            message.data.setdefault('utterance', 'add ' + task_name_2 + ' to my ' + list_name + 'x list')
            with patch('__init__.CowsLists.get_response', return_value='yes') as mock_get_response:
                self.cowsLists.add_task_to_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_get_response, ['UsingAnotherList'])
            test_mock_call_sequence(self, mock_speak_dialog, ['AddTaskToList'])
            list_context_param = get_mock_call_parameters(self, mock_set_context, LIST_CONTEXT)
            undo_context_param = get_mock_call_parameters(self, mock_set_context, UNDO_CONTEXT)

            print "Test that the tasks are actually there"
            test_find_task_on_list(self, task_name_1, list_name, match=True)
            test_find_task_on_list(self, task_name_2, list_name, match=True)

            print "Undo, remove last task"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, undo_context_param)

            self.cowsLists.undo_intent(message)

            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            test_mock_call_sequence(self, mock_speak_dialog, ['AddTaskToListUndo'])
            test_find_task_on_list(self, task_name_2, list_name, no_match=True)

            print "Add task in list context"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(LIST_CONTEXT, list_context_param)
            message.data.setdefault(TASK_PARAMETER, task_name_2)
            message.data.setdefault('utterance', 'add ' + task_name_2)
            task_name_3 = "test item: " + str(uuid.uuid1())

            with patch('__init__.CowsLists.get_response', side_effect=[task_name_3, 'no']) as mock_get_response:
                self.cowsLists.add_task_intent(message)

            test_mock_call_sequence(self,
                                    mock_remove_context,
                                    [UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT, UNDO_CONTEXT, TASK_CONTEXT, LIST_CONTEXT])
            test_mock_call_sequence(self, mock_get_response, ['AnythingElse', 'AnythingElse'])
            test_mock_call_sequence(self, mock_speak_dialog, ['AnythingElseEnd'])

            print "Test that the tasks are actually there"
            test_find_task_on_list(self, task_name_1, list_name, match=True)
            test_find_task_on_list(self, task_name_2, list_name, match=True)
            test_find_task_on_list(self, task_name_3, list_name, match=True)

            print "Add task in list context, with matching list"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(LIST_CONTEXT, list_context_param)
            message.data.setdefault(TASK_PARAMETER, task_name_2)
            message.data.setdefault('utterance', 'add ' + task_name_2 + ' to the test list list' )

            with patch('__init__.CowsLists.get_response', return_value= 'no') as mock_get_response:
                self.cowsLists.add_task_intent(message)

            test_mock_call_sequence(self,
                                    mock_remove_context,
                                    [UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT, LIST_CONTEXT])
            test_mock_call_sequence(self, mock_get_response, ['AnythingElse'])
            test_mock_call_sequence(self, mock_speak_dialog, ['AnythingElseEnd'])

            print "Add list in list context, with different list"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(LIST_CONTEXT, list_context_param)
            message.data.setdefault(TASK_PARAMETER, task_name_2)
            message.data.setdefault('utterance', 'add ' + task_name_2 + ' to the inbox list' )

            self.cowsLists.add_task_intent(message)

            test_mock_call_sequence(self,
                                    mock_remove_context,
                                    [UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['AddTaskToList'])

            print "undo add to inbox list"
            undo_context_param = get_mock_call_parameters(self, mock_set_context, UNDO_CONTEXT)
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, undo_context_param)
            self.cowsLists.undo_intent(message)


#@unittest.skip("Skip TestFindTask")
class TestFindTask(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'Cows Lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'Cows Lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()


    def test_find_task_nomatch(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        print "Add test tasks"
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )
        add_task_to_list_by_name(self, self.list_name, self.task_name_2 )

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, "x" + self.task_name_1)
        message.data.setdefault('utterance', 'find x' + self.task_name_1 + " on my " + self.list_name + " list")
        set_list_context(self, message, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.find_task_intent(message)


            test_mock_call_sequence(self, mock_remove_context, [])
            test_mock_call_sequence(self, mock_speak_dialog,
                                    ['FindTaskOnListMismatch'])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, TASK_CONTEXT])

    def test_find_task_new_context(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        print "Add test tasks"
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )
        add_task_to_list_by_name(self, self.list_name, self.task_name_2 )

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault('utterance', 'find x' + self.task_name_1 + " on my " + self.list_name + "x list")
        set_list_context(self, message, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.get_response', return_value='yes') \
                        as mock_get_response, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.find_task_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [])
            test_mock_call_sequence(self, mock_speak_dialog,
                                    ['FindTaskOnListMismatch'])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_get_response, ['UsingAnotherList'])

#@unittest.skip("Skip TestFindTaskOnList")
class TestFindTaskOnList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'Cows Lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'Cows Lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()


    def test_task_on_empty_list(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault(LIST_PARAMETER, self.list_name)
        message.data.setdefault('utterance',
                                'find ' + self.task_name_1 + " on the " + self.list_name + " list")
        cow_rest.auth_token = None  # get token from config

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.find_task_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [])
            test_mock_call_sequence(self, mock_speak_dialog, ['NoTaskOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])

    def test_only_task_on_list(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault(LIST_PARAMETER, self.list_name)
        message.data.setdefault('utterance', 'find ' + self.task_name_1 + " on my " + self.list_name + " list")
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:

            cow_rest.auth_token = None  # get token from config

            self.cowsLists.find_task_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [])
            test_mock_call_sequence(self, mock_speak_dialog, ['FindTaskOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, TASK_CONTEXT])

    def test_task_nomatch_list_nomatch(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, "x" + self.task_name_1)
        message.data.setdefault(LIST_PARAMETER, self.list_name + 'x')
        message.data.setdefault('utterance', 'find x' + self.task_name_1 + " on the " + self.list_name + "x list")
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.get_response', return_value='yes') as mock_get_response:
            self.cowsLists.find_task_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_get_response, ['UsingAnotherList'])
            test_mock_call_sequence(self, mock_speak_dialog, ['FindTaskOnListMismatch'])


#@unittest.skip("Skip CompleteTaskOnList")
class CompleteTaskOnList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_complete_task_on_empty_list(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault(LIST_PARAMETER, self.list_name)
        message.data.setdefault('utterance',
                                'complete ' + self.task_name_1 + " on the " + self.list_name + " list")
        cow_rest.auth_token = None  # get token from config

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.complete_task_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['NoTaskOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])


    def test_complete_only_task_on_list_and_undo(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault(LIST_PARAMETER, self.list_name)
        message.data.setdefault('utterance', 'complete ' + self.task_name_1 + " on my " + self.list_name + " list")
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.complete_task_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteTaskOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, UNDO_CONTEXT])

            undo_context_param = get_mock_call_parameters(self, mock_set_context, UNDO_CONTEXT)

            print "Test that the tasks is removed"
            test_find_task_on_list(self, self.task_name_1, self.list_name, no_match=True)

            print "Undo, restore last task"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, undo_context_param)

            self.cowsLists.undo_intent(message)

            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteTaskOnListUndo'])

            print "Test that the tasks is restored"
            test_find_task_on_list(self, self.task_name_1, self.list_name, match=True)


    def test_complete_identical_tasks_on_list(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault(LIST_PARAMETER, self.list_name)
        message.data.setdefault('utterance', 'complete ' + self.task_name_1 + " on my " + self.list_name + " list")
        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.complete_task_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteManyTasksOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, UNDO_CONTEXT])

            undo_context_param = get_mock_call_parameters(self, mock_set_context, UNDO_CONTEXT)

            print "Test that the tasks is removed"
            test_find_task_on_list(self, self.task_name_1, self.list_name, no_match=True)

            print "Undo, restore last task"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, undo_context_param)

            self.cowsLists.undo_intent(message)

            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteTaskOnListUndo'])

            print "Test that the tasks is restored"
            test_find_task_on_list(self, self.task_name_1, self.list_name, match=True)


#@unittest.skip("Skip CompleteTask")
class CompleteTask(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_complete_task(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault('utterance',
                                'complete ' + self.task_name_1)
        set_list_context(self, message, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.complete_task_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteTaskOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, UNDO_CONTEXT])

    def test_complete_task_new_context(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )

        message = Message(self)
        message.data.setdefault(TASK_PARAMETER, self.task_name_1)
        message.data.setdefault('utterance', 'complete ' + self.task_name_1 +
                                "x on my " + self.list_name + "x list")
        set_list_context(self, message, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.get_response',
                  return_value='yes') as mock_get_response:
            self.cowsLists.complete_task_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['FindTaskOnListMismatch', 'CompleteTaskOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_get_response, ['UsingAnotherList', 'DoYouWantToCompleteIt'])

            undo_context_param = get_mock_call_parameters(self, mock_set_context, UNDO_CONTEXT)

            print "Undo, restore last task"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, undo_context_param)

            self.cowsLists.undo_intent(message)

            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            test_mock_call_sequence(self, mock_speak_dialog,
                                    ['CompleteTaskOnListUndo'])

    def test_complete_task_context(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )
        task_best_match = test_find_task_on_list(self, self.task_name_1,
                                                 self.list_name, match=True)

        message = Message(self)
        message.data.setdefault('utterance', 'complete task')
        set_list_context(self, message, list_best_match)
        set_task_context(self, message, task_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.complete_task_intent(message)

            test_mock_call_sequence(self, mock_remove_context, [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteTaskOnList'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT, UNDO_CONTEXT])


#@unittest.skip("Skip CompleteList")
class CompleteList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_complete_empty_list(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance', 'complete all tasks on my ' + list_name + ' list')

            self.cowsLists.complete_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['NoTaskOnList'])


    def test_complete_list_one_task_undo(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance',
                                    'complete all tasks on the ' + list_name + ' list')


            self.cowsLists.complete_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteListOneTask'])

            test_find_task_on_list(self, self.task_name_1, list_name, no_match=True)

            undo_context_param = get_mock_call_parameters(self,
                                                          mock_set_context,
                                                          UNDO_CONTEXT)

            print "Undo, restore last task"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, undo_context_param)

            self.cowsLists.undo_intent(message)

            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteListOneTaskUndo'])
            test_find_task_on_list(self, self.task_name_1, list_name, match=True)

    def test_complete_list_undo(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance',
                                    'complete all tasks on the ' + list_name + ' list')


            self.cowsLists.complete_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteList'])

            undo_context_param = get_mock_call_parameters(self,
                                                          mock_set_context,
                                                          UNDO_CONTEXT)

            test_find_task_on_list(self, self.task_name_1, list_name, no_match=True)
            test_find_task_on_list(self, self.task_name_2, list_name, no_match=True)

            print "Undo, restore last tasks"
            mock_speak_dialog.reset_mock()
            mock_remove_context.reset_mock()
            mock_set_context.reset_mock()
            message = Message(self)
            message.data.setdefault(UNDO_CONTEXT, undo_context_param)

            self.cowsLists.undo_intent(message)

            mock_remove_context.assert_called_with(UNDO_CONTEXT)
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteListUndo'])
            test_find_task_on_list(self, self.task_name_1, list_name, match=True)
            test_find_task_on_list(self, self.task_name_2, list_name, match=True)


    def test_complete_list_many_tasks(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        for i in range(0, 41):
            add_task_to_list_by_name(self, self.list_name, self.task_name_1)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance',
                                    'complete all tasks on the ' + list_name + ' list')


            self.cowsLists.complete_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompletePartOfListStart', 'CompleteListStart','CompleteList'])


#@unittest.skip("Skip Complete")
class Complete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_complete(self):
        # Set up interface
        test_operation_init(self)

        list_best_match = test_find_list(self, self.list_name, match=True)

        print "Clear the list"
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        print "Add test tasks"
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )
        add_task_to_list_by_name(self, self.list_name, self.task_name_2 )

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault('utterance', 'complete all tasks')
            set_list_context(self, message, list_best_match)

            self.cowsLists.complete_intent(message)

            test_mock_call_sequence(self, mock_remove_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteList'])

            test_find_task_on_list(self, self.task_name_1, list_best_match.name, no_match=True)
            test_find_task_on_list(self, self.task_name_2, list_best_match.name, no_match=True)


    def test_complete_list_new_context(self):
        # Set up interface
        test_operation_init(self)

        list_best_match = test_find_list(self, "test list", match=True)

        print "Clear the list"
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        print "Add test tasks"
        add_task_to_list_by_name(self, self.list_name, self.task_name_1 )
        add_task_to_list_by_name(self, self.list_name, self.task_name_2 )

        message = Message(self)
        message.data.setdefault('utterance',
                                'complete all tasks on the ' + self.list_name + 'x list')
        set_list_context(self, message, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.get_response',
                      return_value='yes') as mock_get_response:

            self.cowsLists.complete_intent(message)

            test_mock_call_sequence(self, mock_remove_context,
                                    [UNDO_CONTEXT, TASK_CONTEXT])
            test_mock_call_sequence(self, mock_set_context,
                                    [LIST_CONTEXT, UNDO_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['CompleteList'])
            test_mock_call_sequence(self, mock_get_response,
                                    ['UsingAnotherList'])

            undo_context_param = get_mock_call_parameters(self,
                                                          mock_set_context,
                                                          UNDO_CONTEXT)

            test_find_task_on_list(self, self.task_name_1, list_best_match.name, no_match=True)
            test_find_task_on_list(self, self.task_name_2, list_best_match.name, no_match=True)


#@unittest.skip("Skip TestReadList")
class TestReadList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_read_empty_list(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance', 'read my ' + list_name + ' list')

            self.cowsLists.read_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['NoTaskOnList'])


    def test_read_list_one_item(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance',
                                    'read the ' + list_name + ' list')


            self.cowsLists.read_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['ReadListOneItem'])


    def test_read_list(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, list_name)
            message.data.setdefault('utterance',
                                    'read the ' + list_name + ' list')


            self.cowsLists.read_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['ReadList'])


#@unittest.skip("Skip TestReadList")
class TestRead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1())
        cls.list_name = 'test list'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()


    def test_read(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, self.list_name, match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)
        add_task_to_list_by_name(self, self.list_name, self.task_name_1)

        message = Message(self)
        message.data.setdefault('utterance', 'read the list')
        set_list_context(self, message, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.read_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_speak_dialog,
                                    ['ReadListOneItem'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])


    def test_read_new_context(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_name = 'test list'
        list_best_match = test_find_list(self, list_name, match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.get_response',
                      return_value='yes') as mock_get_response:
            message = Message(self)
            set_list_context(self, message, list_best_match)
            message.data.setdefault('utterance',
                                    'read the ' + list_name + 'x list')

            self.cowsLists.read_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['ReadList'])
            test_mock_call_sequence(self, mock_get_response, ['UsingAnotherList'])


#@unittest.skip("Skip DueOnList")
class TestDueOnList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1()) + ' tomorrow'
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1()) + ' yesterday'
        cls.list_name = 'test'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()

    def test_due_on_empty_list(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_best_match = test_find_list(self, "test list", match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch('__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            message.data.setdefault('utterance', 'what is on my ' +
                                    self.list_name + ' list  tomorrow')

            self.cowsLists.due_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['NoTaskOnList'])


    def test_due_on_list_one_item(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_best_match = test_find_list(self, "test list", match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            message.data.setdefault('utterance',
                                    'what is on my ' + self.list_name +
                                    ' list  tomorrow')


            self.cowsLists.due_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['ReadListOneItem', 'WithDueDate'])


    def test_due_on_list(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_best_match = test_find_list(self, "test list", match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.set_context') as mock_set_context:
            message = Message(self)
            message.data.setdefault(LIST_PARAMETER, self.list_name)
            message.data.setdefault('utterance',
                                    'what is on my ' + self.list_name +
                                    ' list  tomorrow')


            self.cowsLists.due_on_list_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['ReadList', 'WithDueDate'])


#@unittest.skip("Skip Due")
class TestDue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cowsLists = CowsLists()
        config.read(CONFIG_FILE)
        cow_rest.api_key = config.get('auth', 'api_key')
        cow_rest.secret = config.get('auth', 'secret')
        cls.task_name_1 = 'cows lists test item: ' + str(uuid.uuid1()) + ' tomorrow'
        cls.task_name_2 = 'cows lists test item: ' + str(uuid.uuid1()) + ' yesterday'
        cls.list_name = 'test'
        cls.cowsLists.vocab_dir = cls.cowsLists._dir + "/vocab/" + cls.cowsLists.lang
        cls.cowsLists.initialize()


    def test_due(self):
        test_operation_init(self)
        list_best_match = test_find_list(self, "test list", match=True)
        test_complete_list_explain(self, list_best_match.name, list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        message = Message(self)
        message.data.setdefault('utterance', 'what is due tomorrow')
        set_list_context(self, message, list_best_match)

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog:
            self.cowsLists.due_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_speak_dialog,
                                    ['ReadListOneItem', 'WithDueDate'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])


    def test_read_new_context(self):
        # Set up interface
        test_operation_init(self)

        print "Clear the list"
        list_best_match = test_find_list(self, "test list", match=True)
        test_complete_list_explain(self, list_best_match.name,
                                   list_best_match)

        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_1)
        add_task_to_list_by_name(self, self.list_name, self.task_name_2)

        message = Message(self)
        set_list_context(self, message, list_best_match)
        message.data.setdefault('utterance',
                                'what is on the ' + self.list_name + 'x list tomorrow')

        with patch('__init__.CowsLists.speak_dialog') as mock_speak_dialog, \
                patch(
                    '__init__.CowsLists.remove_context') as mock_remove_context, \
                patch('__init__.CowsLists.set_context') as mock_set_context, \
                patch('__init__.CowsLists.speak'), \
                patch('__init__.CowsLists.get_response',
                      return_value='yes') as mock_get_response:

            self.cowsLists.due_intent(message)

            test_mock_call_sequence(self, mock_remove_context, ['TaskContext'])
            test_mock_call_sequence(self, mock_set_context, [LIST_CONTEXT])
            test_mock_call_sequence(self, mock_speak_dialog, ['ReadList', 'WithDueDate'])
            test_mock_call_sequence(self, mock_get_response, ['UsingAnotherList'])

if __name__ == '__main__':
    unittest.main()

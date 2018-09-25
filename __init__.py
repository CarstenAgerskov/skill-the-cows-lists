"""
skill the-cows-lists
Copyright (C) 2017  Carsten Agerskov

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import sys
import os
import traceback
import re
from collections import namedtuple
from adapt.intent import IntentBuilder
from fuzzywuzzy import process
from mycroft import removes_context
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler
from mycroft.util.log import getLogger
from importlib import reload

HOME_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HOME_DIR)
import cow_rest

__author__ = 'cagerskov'

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
TEST_CONTEXT = "_TestContext"
MAX_TASK_COMPLETE = 40

LIST_TUPLE = namedtuple('list', 'name, id, significance, error_text, '
                                'error_code')
TASK_LIST_TUPLE = namedtuple('task_list', (
    'name, id, taskseries_id, significance, task_list, list_best_match, error_text, error_code'))

LOGGER = getLogger(__name__)


class CowsLists(MycroftSkill):
    def __init__(self):
        super(CowsLists, self).__init__(name='TheCowsLists')
        reload(cow_rest)
        self.last_traceback = None
        self.last_message = None
        self.no_keyword = None
        self.yes_keyword = None
        self.local_regex = {}
        self.vocab_dir = None

    def initialize(self):
        self.vocab_dir = HOME_DIR + '/vocab/' + self.lang
        self.no_keyword = open(self.vocab_dir + '/NoKeyword.voc', 'r').read()
        self.yes_keyword = open(self.vocab_dir + '/YesKeyword.voc', 'r').read()
        local_regex = json.loads(
            open(HOME_DIR + '/regex/' + self.lang + '/LocalRegex.json', 'r')
                .read())

        for key, value in local_regex.items():
            self.local_regex.update({key: [re.compile(v) for v in value]})


    def get_config(self):
        if cow_rest.api_key and cow_rest.secret:
            return True

        try:
            try:
                if not cow_rest.api_key:
                    cow_rest.api_key = self.config.get('api_key')
            except Exception:
                pass

            try:
                if not cow_rest.secret:
                    cow_rest.secret = self.config.get('secret')
            except Exception:
                pass

            if not cow_rest.secret:
                cow_rest.secret = self.settings.get('secret')

            if not cow_rest.api_key:
                cow_rest.api_key = self.settings.get('api_key')

            if not cow_rest.api_key or not cow_rest.secret:
                raise Exception("api key or secret not configured")

            return True

        except Exception:
            self.speak_dialog('ConfigNotFound')
            return False

    def operation_init(self):
        if not self.get_config():
            return False

        cow_rest.get_token(cow_rest)

        if not cow_rest.auth_token and cow_rest.frob:
            self.speak_dialog("InAuthentication")
            return False

        if not cow_rest.auth_token:
            self.speak_dialog("NotAuthenticated")
            return False

        return True

    def set_task_context(self, task_list_tuple):
        self.set_context(
            TASK_CONTEXT,
            json.dumps({'id': task_list_tuple.id,
                        'name': task_list_tuple.name,
                        'taskseries_id': task_list_tuple.taskseries_id}))

    def task_context_to_tuple(self, task_context, list_context):
        list_tuple = self.list_context_to_tuple(list_context)
        c = json.loads(task_context)
        return TASK_LIST_TUPLE(c['name'], c['id'], c['taskseries_id'], 100,
                               None, list_tuple, None, None)

    def list_context_to_tuple(self, list_context):
        c = json.loads(list_context)
        return LIST_TUPLE(c['name'], c['id'], 100, None, None)

    def get_timeline(self):
        error_text, error_code = cow_rest.get_timeline(cow_rest)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return False

        return True

    def add_task_to_list(self, task_name, list_tuple):
        taskseries_id, task_id, error_text, error_code = (
            cow_rest.add_task(task_name, list_tuple.id))
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})

            return False

        c = {"dialog": "AddTaskToListUndo",
             "dialogParam": {TASK_PARAMETER: task_name,
                             LIST_PARAMETER: list_tuple.name},
             "task": {"task_id": task_id,
                      "task_name": task_name,
                      "taskseries_id": taskseries_id,
                      "list_id": list_tuple.id,
                      "list_name": list_tuple.name}}

        self.set_context(UNDO_CONTEXT, json.dumps(c))

        self.set_task_context(TASK_LIST_TUPLE(task_name, task_id, taskseries_id,
                                              100, None, list_tuple, None,
                                              None))

        return True

    def add_task_to_list_explain(self, task_name, list_tuple):
        if not self.add_task_to_list(task_name, list_tuple):
            return False

        self.speak_dialog("AddTaskToList", {TASK_PARAMETER: task_name,
                                            LIST_PARAMETER: list_tuple.name})

        return True

    def find_list(self, list_name):
        list_result, error_text, error_code = cow_rest.get_list()

        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return LIST_TUPLE(None, None, None, error_text, error_code)

        # Workaround the intent parser remove the word list: First, try to
        # match to a "list_name list"
        list_name_best_match, significance = (
            process.extractOne(list_name + " list",
                               map(lambda x: x['name'].lower(),
                                   list_result)))
        # Then try to match to "list_name"
        if significance < 100:
            list_name_best_match, significance = (
                process.extractOne(list_name,
                                   map(lambda x: x['name'].lower(),
                                       list_result)))

        list_id = [x for x in list_result if x['name'].lower() ==
                   list_name_best_match][0]['id']

        self.set_context(LIST_CONTEXT,
                         json.dumps({'id': list_id,
                                     'name': list_name_best_match,
                                     'significance': significance}))

        return LIST_TUPLE(list_name_best_match, list_id, significance, None,
                          None)

    def find_list_explain(self, list_name):
        list_best_match = self.find_list(list_name)
        if list_best_match.error_text:
            return list_best_match

        if list_best_match.significance < 100:
            response = self.get_response(
                'UsingAnotherList',
                {LIST_PARAMETER: list_name,
                 BEST_MATCH_PARAMETER: list_best_match.name},
                num_retries=0)

            if not response or response not in self.yes_keyword:
                self.speak_dialog('NoConfirm')
                return LIST_TUPLE(None, None, None, None, None)

        return list_best_match

    def find_task_on_list(self, task_name, list_best_match):
        task_list, error_code, error_text = cow_rest.list_task(
            "status:incomplete", list_best_match.id)

        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return TASK_LIST_TUPLE(None, None, None, None, None,
                                   list_best_match, error_text, error_code)

        flat_task_list = cow_rest.flat_task_list(task_list)

        if len(flat_task_list) == 0:
            return TASK_LIST_TUPLE(None, None, None, None, None,
                                   list_best_match, None, None)

        task_name_best_match, significance = (
            process.extractOne(task_name, map(lambda x: x['task_name'].lower(),
                                              flat_task_list)))

        # There may be several tasks with the same task_name_best_match,
        # selected_task_list holds all
        selected_task_list = [x for x in flat_task_list
                              if x['task_name'].lower() ==
                              task_name_best_match]

        task_list_tuple = TASK_LIST_TUPLE(task_name_best_match,
                                          selected_task_list[0]['task_id'],
                                          selected_task_list[0][
                                              'taskseries_id'],
                                          significance,
                                          selected_task_list, list_best_match,
                                          error_text,
                                          error_code)

        return task_list_tuple

    def find_task_on_list_explain(self, task_name, list_name,
                                  list_best_match=None, speak_level=0):
        if not list_best_match:
            list_best_match = self.find_list_explain(list_name)
        if not list_best_match.id:
            return TASK_LIST_TUPLE(None, None, None, None, None,
                                   list_best_match, list_best_match.error_text,
                                   list_best_match.error_code)

        task_best_match = self.find_task_on_list(task_name, list_best_match)

        if task_best_match.error_text:
            return task_best_match

        if not task_best_match.name:
            self.speak_dialog("NoTaskOnList", {
                LIST_PARAMETER: list_best_match.name})
        else:
            if (speak_level > 1 and
                    task_name.lower() == task_best_match.name.lower()):
                self.speak_dialog("FindTaskOnList", {
                    TASK_PARAMETER: task_best_match.name,
                    LIST_PARAMETER: list_best_match.name})
            if (speak_level > 0 and
                    task_name.lower() != task_best_match.name.lower()):
                self.speak_dialog("FindTaskOnListMismatch",
                                  {TASK_PARAMETER: task_name,
                                   BEST_MATCH_PARAMETER: task_best_match.name,
                                   LIST_PARAMETER: list_best_match.name})

        return task_best_match

    def filter_tasks_on_list(self, list_id, task_filter):
        task_list, error_code, error_text = cow_rest.list_task(task_filter,
                                                               list_id)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return None

        flat_task_list = cow_rest.flat_task_list(task_list)

        return flat_task_list

    def filter_tasks_on_list_read(self, list_name, list_id, task_filter,
                                  additional_dialog=None):
        flat_task_list = self.filter_tasks_on_list(list_id, task_filter)
        if flat_task_list is None:
            return

        if len(flat_task_list) == 0:
            self.speak_dialog("NoTaskOnList",
                              {LIST_PARAMETER: list_name})
            if additional_dialog:
                additional_dialog()
            return

        self.speak_dialog(
            "ReadListOneItem" if len(flat_task_list) == 1 else "ReadList",
            {LIST_PARAMETER: list_name,
             NOF_TASK_PARAMETER: str(len(flat_task_list))})
        if additional_dialog:
            additional_dialog()

        for x in flat_task_list:
            self.speak(x['task_name'])

    def complete_task_on_list_explain(self, task_name, list_name,
                                      list_best_match=None):
        task_best_match = self.find_task_on_list_explain(
            task_name,
            list_name,
            list_best_match=list_best_match,
            speak_level=1)

        if not task_best_match.name:
            return False

        if task_name != task_best_match.name:
            response = self.get_response('DoYouWantToCompleteIt', num_retries=0)

            if not response or response not in self.yes_keyword:
                self.speak_dialog('NoConfirm')
                return True

        if not self.get_timeline():
            return False

        c = {"dialog": "CompleteTaskOnListUndo",
             "dialogParam": {
                 TASK_PARAMETER: task_best_match.name,
                 LIST_PARAMETER: task_best_match.list_best_match.name},
             'transaction_id': []}

        for t in task_best_match.task_list:
            transaction_id, error_text, error_code = cow_rest.complete_task(
                t['task_id'],
                t['taskseries_id'],
                task_best_match.list_best_match.id)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                # RECOVER
                return False

            c['transaction_id'].append(transaction_id)

        if len(task_best_match.task_list) == 1:
            self.speak_dialog("CompleteTaskOnList", {
                TASK_PARAMETER: task_best_match.name,
                LIST_PARAMETER: task_best_match.list_best_match.name})
        else:
            self.speak_dialog("CompleteManyTasksOnList", {
                NOF_TASK_PARAMETER: str(len(task_best_match.task_list)),
                TASK_PARAMETER: task_best_match.name,
                LIST_PARAMETER: task_best_match.list_best_match.name})

        self.set_context(UNDO_CONTEXT, json.dumps(c))

        return True

    def complete_list_explain(self, list_name, list_best_match=None):
        if not list_best_match:
            list_best_match = self.find_list_explain(list_name)
            if not list_best_match.id or list_best_match.error_text:
                return

        task_list, error_code, error_text = cow_rest.list_task(
            'status:incomplete', list_best_match.id)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return

        flat_task_list = cow_rest.flat_task_list(task_list)

        if len(flat_task_list) == 0:
            self.speak_dialog("NoTaskOnList",
                              {LIST_PARAMETER: list_best_match.name})
            return

        nof_tasks_to_complete = len(flat_task_list)

        if nof_tasks_to_complete > MAX_TASK_COMPLETE:
            nof_tasks_to_complete = MAX_TASK_COMPLETE
            self.speak_dialog('CompletePartOfListStart', {
                NOF_TASK_PARAMETER: str(len(flat_task_list))})

        if nof_tasks_to_complete > 10:
            self.speak_dialog('CompleteListStart',
                              {NOF_TASK_PARAMETER: nof_tasks_to_complete,
                               LIST_PARAMETER: list_best_match.name})

        if not self.get_timeline():
            return

        c = {
            "dialog": ("CompleteListOneTaskUndo" if nof_tasks_to_complete == 1
                       else "CompleteListUndo"),
            "dialogParam": {NOF_TASK_PARAMETER: nof_tasks_to_complete,
                            LIST_PARAMETER: list_best_match.name},
            'transaction_id': []}

        i = nof_tasks_to_complete
        for t in flat_task_list:
            transaction_id, error_text, error_code = cow_rest.complete_task(
                t['task_id'],
                t['taskseries_id'],
                list_best_match.id)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                # RECOVER
                return

            c['transaction_id'].append(transaction_id)

            i = i - 1
            if i < 1:
                break

        self.speak_dialog(
            ("CompleteListOneTask" if nof_tasks_to_complete == 1
             else "CompleteList"),
            {LIST_PARAMETER: list_best_match.name,
             NOF_TASK_PARAMETER: nof_tasks_to_complete})

        self.set_context(UNDO_CONTEXT, json.dumps(c))

    def regex_evaluation_explain(self, message, regex_key):
        m = None
        k = None
        for k in regex_key:
            for r in self.local_regex[k]:
                m = r.match(message.data.get('utterance'))
                if m:
                    break
            if m:
                break

        if not m:
            self.speak_dialog("IDontUnderstand")

        return k, m

    def speak_exception(self, trace_back, message, function_name):
        self.last_traceback = "Error in " + function_name + ": " + trace_back
        self.last_message = message
        LOGGER.exception(self.last_traceback)
        self.speak_dialog('GeneralError',
                          {FUNCTION_NAME_PARAMETER: function_name,
                           LINE_PARAMETER: format(
                               sys.exc_info()[-1].tb_lineno)})
        self.set_context(EXCEPTION_CONTEXT)
        self.speak_dialog('AskSendException', None, expect_response=True)

    @intent_handler(
        IntentBuilder("SendExceptionIntent").require("YesKeyword").require(
            EXCEPTION_CONTEXT).optionally(TEST_CONTEXT).build())
    @removes_context(EXCEPTION_CONTEXT)
    @removes_context(UNDO_CONTEXT)
    def send_exception_intent(self, message):
        try:
            if message.data.get(TEST_CONTEXT):
                # Last traceback may not exist if testing
                self.speak("Test context:")
                return

            mail_body = "This mail contains details of an exception in the cows lists<br>" \
                        + "Please report the issue at " \
                        + '<a href = "https://github.com/CarstenAgerskov/skill-the-cows-lists/issues">https://github.com/CarstenAgerskov/skill-the-cows-lists/issues</a>' \
                        + "<br>When reporting the issue, you decide what information to include, " \
                        + "or if you wish to anonymize any data. " \
                        + "Please provide the following information:<br><br>" \
                        + "* A description of your dialog with Mycroft<br>" \
                        + "* Any other details that may help<br>" \
                        + "* The last utterance below<br>" \
                        + "* The exception text below<br><br>" \
                        + "Utterance: " \
                        + self.last_message.data.get('utterance') \
                        + "<br><br>" \
                        + self.last_traceback

            self.send_email("Exception details", mail_body)
            self.speak_dialog('SendException')

        except Exception as e:
            LOGGER.exception("Error in send_exception: {0}".format(e))
            self.speak_dialog('GeneralError',
                              {FUNCTION_NAME_PARAMETER: "send exception",
                               LINE_PARAMETER: format(
                                   sys.exc_info()[-1].tb_lineno)})

    @intent_handler(IntentBuilder("AuthenticateIntent").require(
        "AuthenticateKeyword").build())
    @removes_context(UNDO_CONTEXT)
    def authenticate_intent(self, message):
        try:
            if not self.get_config():
                return

            cow_rest.get_token(cow_rest)

            if cow_rest.auth_token:
                error_text, error_code = cow_rest.verify_token_validity()
                if not error_text:
                    self.speak_dialog("TokenValid")
                    return

            error_text, error_code = cow_rest.get_frob(cow_rest)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                return

            auth_url = cow_rest.get_auth_url()

            mail_body = "Use the link below to authenticate Mycroft with remember the milk.<br>" \
                        + "After authentication, say: Hey Mycroft, get a token for remember the milk<br><br>" \
                        + '<a href = "' + auth_url + '">' + auth_url + '</a>'

            self.send_email("Authentication", mail_body)
            self.speak_dialog("EmailSent")

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "get token intent")

    @intent_handler(
        IntentBuilder("GetTokenIntent").require("GetTokenKeyword").build())
    @removes_context(UNDO_CONTEXT)
    def get_token_intent(self, message):
        try:
            if not self.get_config():
                return

            cow_rest.get_token(cow_rest)

            if cow_rest.auth_token:
                error_text, error_code = cow_rest.verify_token_validity()
                if error_text and error_code != '98':
                    self.speak_dialog('RestResponseError',
                                      {ERROR_TEXT_PARAMETER: error_text,
                                       ERROR_CODE_PARAMETER: error_code})
                    return

                if not error_text:
                    self.speak_dialog("TokenValid")
                    return

            if not cow_rest.frob:
                self.speak_dialog('AuthenticateBeforeToken')
                return

            error_text, error_code = cow_rest.get_new_token(cow_rest)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                return

            self.speak_dialog("GotToken")

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "get token intent")

    @intent_handler(IntentBuilder("AddTaskIntent").require(
        "AddTaskToListKeyword").require(TASK_PARAMETER).require(LIST_CONTEXT).
                    optionally(TEST_CONTEXT).build())
    def add_task_intent(self, message):
        try:
            list_tuple = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_evaluation_explain(
                message, ['AddTaskToList', 'AddTask'])
            if not m:
                return

            if k == 'AddTaskToList' and (
                    m.groupdict()[LIST_PARAMETER] != list_tuple.name):
                self.add_task_to_list_intent(message)
                return

            task_name = m.groupdict()[TASK_PARAMETER]

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, add task intent: task name " + task_name +
                    ", list name " + list_tuple.name)
                return

            self.remove_context(UNDO_CONTEXT)

            if not self.operation_init():
                return

            if not self.get_timeline():
                return

            self.add_task_to_list(task_name, list_tuple)

            # The user added a task to a list in context, ask for more
            while True:
                task_name = self.get_response("AnythingElse",
                                              {TASK_PARAMETER: task_name},
                                              num_retries=0)
                if not task_name or task_name in self.no_keyword:
                    self.speak_dialog("AnythingElseEnd",
                                      {LIST_PARAMETER: list_tuple.name})
                    # refresh context, prevent context timeout
                    self.set_context(LIST_CONTEXT,
                                     message.data.get(LIST_CONTEXT))
                    break

                self.add_task_to_list(task_name, list_tuple)

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "add task intent")

    @intent_handler(IntentBuilder("AddTaskToListIntent").require(
        "AddTaskToListKeyword").require(TASK_PARAMETER).require(LIST_PARAMETER).
                    optionally(TEST_CONTEXT).build())
    def add_task_to_list_intent(self, message):
        try:
            self.remove_context(UNDO_CONTEXT)

            k, m = self.regex_evaluation_explain(message, ['AddTaskToList'])
            if not m:
                return

            task_name = m.groupdict()[TASK_PARAMETER]
            list_name = m.groupdict()[LIST_PARAMETER]

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, add task to list intent: task name " +
                    task_name + ", list name " + list_name)
                return

            if not self.operation_init():
                return

            if not self.get_timeline():
                return

            list_best_match = self.find_list_explain(list_name)
            if not list_best_match.name:
                return

            self.add_task_to_list_explain(task_name, list_best_match)

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "add task to list intent")

    @intent_handler(IntentBuilder("FindTaskIntent").require(
        "FindTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_CONTEXT).optionally(TEST_CONTEXT).build())
    def find_task_intent(self, message):
        try:
            list_tuple = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_evaluation_explain(message,
                                                 ['FindTaskOnList', 'FindTask'])
            if not m:
                return

            if k == 'FindTaskOnList':
                self.find_task_on_list_intent(message)
                return

            task_name = m.groupdict()[TASK_PARAMETER]

            self.set_context(LIST_CONTEXT, message.data.get(LIST_CONTEXT))

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, find task intent: task name "
                    + task_name + ", list name " + list_tuple.name)
                return

            if not self.operation_init():
                return

            task_tuple = self.find_task_on_list_explain(
                task_name,
                list_tuple.name,
                list_best_match=LIST_TUPLE(
                    list_tuple.name,
                    list_tuple.id,
                    100, None,
                    None),
                speak_level=2)

            if task_tuple.name:
                self.set_task_context(task_tuple)

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "find task intent")

    @intent_handler(IntentBuilder("FindTaskOnListIntent").require(
        "FindTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_PARAMETER).optionally(TEST_CONTEXT).build())
    def find_task_on_list_intent(self, message):
        try:
            k, m = self.regex_evaluation_explain(message, ['FindTaskOnList'])
            if not m:
                return

            task_name = m.groupdict()[TASK_PARAMETER]
            list_name = m.groupdict()[LIST_PARAMETER]

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, find task on list intent: task name " +
                    task_name + ", list name " + list_name)
                return

            if not self.operation_init():
                return

            task_tuple = self.find_task_on_list_explain(task_name,
                                                        list_name,
                                                        speak_level=2)

            if task_tuple.name:
                self.set_task_context(task_tuple)

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "find task on list intent")

    @intent_handler(IntentBuilder("CompleteTaskIntent").require(
        "CompleteTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_CONTEXT).optionally(TASK_CONTEXT).
                    optionally(TEST_CONTEXT).build())
    def complete_task_intent(self, message):
        try:
            list_tuple = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))
            task_name = None

            k, m = self.regex_evaluation_explain(
                message,
                ['CompleteAll', 'CompleteTaskInContext', 'CompleteTaskOnList',
                 'CompleteTask'])
            if not m:
                return

            if k == 'CompleteAll':
                self.complete_intent(message)
                return

            if k == 'CompleteTaskOnList':
                self.complete_task_on_list_intent(message)
                return

            if k == 'CompleteTaskInContext':
                if not message.data.get(TASK_CONTEXT):
                    self.speak_dialog("NoTaskInContext")
                    return
                task_tuple = self.task_context_to_tuple(
                    message.data.get(TASK_CONTEXT),
                    message.data.get(LIST_CONTEXT))
                task_name = task_tuple.name

            if k == 'CompleteTask':
                task_name = m.groupdict()[TASK_PARAMETER]

            self.remove_context(UNDO_CONTEXT)
            self.remove_context(TASK_CONTEXT)
            self.set_context(LIST_CONTEXT, message.data.get(LIST_CONTEXT))

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, complete task intent: task name " +
                    task_name + ", list name " + list_tuple.name)
                return

            if not self.operation_init():
                return

            self.complete_task_on_list_explain(task_name, list_tuple.name,
                                               list_best_match=LIST_TUPLE(
                                                   list_tuple.name,
                                                   list_tuple.id,
                                                   100, None, None))

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "complete task intent")

    @intent_handler(IntentBuilder("CompleteTaskOnListIntent").require(
        "CompleteTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_PARAMETER).optionally(TEST_CONTEXT).build())
    def complete_task_on_list_intent(self, message):
        try:
            k, m = self.regex_evaluation_explain(
                message, ['CompleteList', 'CompleteTaskOnList'])
            if not m:
                return

            if k == 'CompleteList':
                self.complete_list_intent(message)
                return

            task_name = m.groupdict()[TASK_PARAMETER]
            list_name = m.groupdict()[LIST_PARAMETER]

            self.remove_context(UNDO_CONTEXT)
            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, complete task on list intent: task name " +
                    task_name + ", list name " + list_name)
                return

            if not self.operation_init():
                return

            self.complete_task_on_list_explain(task_name, list_name)

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "complete task on list intent")

    # The intent is to complete all tasks on the list in context
    # This intent does not have an intent decorator, because is is activeted
    # through another intent. So, on the technical level it is not an intent,
    # but it is an intent on the conceptual level. But due to very similar
    # wordings, Adapt cannot distinguish between this intent and other.
    def complete_intent(self, message):
        try:
            list_tuple = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_evaluation_explain(
                message, ['CompleteList', 'CompleteAll'])
            if not m:
                return

            if k == 'CompleteList':
                self.complete_list_intent(message)
                return

            self.remove_context(UNDO_CONTEXT)
            self.remove_context(TASK_CONTEXT)
            self.set_context(LIST_CONTEXT, message.data.get(LIST_CONTEXT))

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, complete intent: list name " +
                    list_tuple.name)
                return

            if not self.operation_init():
                return

            self.complete_list_explain(
                list_tuple.name, list_best_match=LIST_TUPLE(
                    list_tuple.name, list_tuple.id, 100, None, None))

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "complete intent")

    # The intent is to complete all tasks on the list Spoken in the message.
    # This intent does not have an intent decorator, because is is activeted
    # through another intent. So, on the technical level it is not an intent,
    # but it is an intent on the conceptual level. But due to very similar
    # wordings, Adapt cannot distinguish between this intent and other.
    def complete_list_intent(self, message):
        try:
            k, m = self.regex_evaluation_explain(message, ['CompleteList'])
            if not m:
                return

            list_name = m.groupdict()[LIST_PARAMETER]

            self.remove_context(UNDO_CONTEXT)
            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, complete list intent: list name " +
                    list_name)
                return

            if not self.operation_init():
                return

            self.complete_list_explain(list_name)

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "complete list intent")

    @intent_handler(
        IntentBuilder("ReadIntent").require("ReadListKeyword").require(
            LIST_CONTEXT).optionally(TEST_CONTEXT).build())
    def read_intent(self, message):
        try:
            list_tuple = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_evaluation_explain(message,
                                                 ['ReadList', 'Read'])
            if not m:
                return

            if k == 'ReadList':
                self.read_list_intent(message)
                return

            self.remove_context(TASK_CONTEXT)
            self.set_context(LIST_CONTEXT, message.data.get(LIST_CONTEXT))

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, read intent: list name " + list_tuple.name)
                return

            if not self.operation_init():
                return

            self.filter_tasks_on_list_read(list_tuple.name,
                                           list_tuple.id,
                                           'status:incomplete')

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "read intent")

    @intent_handler(
        IntentBuilder("ReadListIntent").require("ReadListKeyword").require(
            LIST_PARAMETER).optionally(TEST_CONTEXT).build())
    def read_list_intent(self, message):
        try:
            k, m = self.regex_evaluation_explain(message, ['ReadList'])
            if not m:
                return

            list_name = m.groupdict()[LIST_PARAMETER]

            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, read list intent: list name " + list_name)
                return

            if not self.operation_init():
                return

            list_best_match = self.find_list_explain(list_name)

            if not list_best_match or list_best_match.error_text:
                return

            self.filter_tasks_on_list_read(list_best_match.name,
                                           list_best_match.id,
                                           'status:incomplete')

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "read list intent")

    @intent_handler(
        IntentBuilder('DueIntent').require('DueKeyword').require(DUE_PARAMETER).
            require(LIST_CONTEXT).optionally(TEST_CONTEXT).build())
    def due_intent(self, message):
        try:
            list_tuple = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_evaluation_explain(message, ['DueOnList', 'Due'])
            if not m:
                return

            if k == 'DueOnList':
                self.due_on_list_intent(message)
                return

            due = m.groupdict()[DUE_PARAMETER]

            self.remove_context(TASK_CONTEXT)
            self.set_context(LIST_CONTEXT, message.data.get(LIST_CONTEXT))

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, due intent: list name " +
                    list_tuple.name + ", due " + due)
                return

            if not self.operation_init():
                return

            self.filter_tasks_on_list_read(
                list_tuple.name,
                list_tuple.id,
                'status:incomplete AND due:' + due,
                additional_dialog=lambda: self.speak_dialog(
                    'WithDueDate', {DUE_PARAMETER: due}))

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "due intent")

    @intent_handler(
        IntentBuilder('DueOnListIntent').require('DueKeyword').
            require(DUE_PARAMETER).require(LIST_PARAMETER).
            optionally(TEST_CONTEXT).build())
    def due_on_list_intent(self, message):
        try:
            k, m = self.regex_evaluation_explain(message, ['DueOnList'])
            if not m:
                return

            list_name = m.groupdict()[LIST_PARAMETER]
            due = m.groupdict()[DUE_PARAMETER]

            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, due on list intent: list name " +
                    list_name + ", due " + due)
                return

            if not self.operation_init():
                return

            list_best_match = self.find_list_explain(list_name)
            if not list_best_match.name:
                return

            self.filter_tasks_on_list_read(
                list_best_match.name, list_best_match.id,
                'status:incomplete AND due:' + due,
                additional_dialog=lambda: self.speak_dialog(
                    'WithDueDate', {DUE_PARAMETER: due}))

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "due on list intent")

    # RTM can roll back some operations, other has to be compensated. The undo
    # itent hides this complexity
    @intent_handler(IntentBuilder("UndoIntent").require("UndoKeyword").require(
        UNDO_CONTEXT).build())
    @removes_context(UNDO_CONTEXT)
    def undo_intent(self, message):
        try:
            c = json.loads(message.data.get(UNDO_CONTEXT))
            if c['dialog'] == "AddTaskToListUndo":
                transaction_id, error_text, error_code = cow_rest.delete_task(
                    c['task']['task_id'],
                    c['task']["taskseries_id"],
                    c['task']["list_id"])

                if error_text:
                    self.speak_dialog('RestResponseError',
                                      {ERROR_TEXT_PARAMETER: error_text,
                                       ERROR_CODE_PARAMETER: error_code})
                    return

                self.speak_dialog(c['dialog'], c['dialogParam'])

            if c['dialog'] in ["CompleteTaskOnListUndo",
                               "CompleteListOneTaskUndo", "CompleteListUndo"]:
                for t in c['transaction_id']:
                    error_text, error_code = cow_rest.roll_back(str(t))
                    if error_text:
                        self.speak_dialog('RestResponseError',
                                          {ERROR_TEXT_PARAMETER: error_text,
                                           ERROR_CODE_PARAMETER: error_code})
                        return
                self.speak_dialog(c['dialog'], c['dialogParam'])

        except Exception:
            self.speak_exception(traceback.format_exc(), message,
                                 "undo intent")

    def stop(self):
        pass


def create_skill():
    return CowsLists()

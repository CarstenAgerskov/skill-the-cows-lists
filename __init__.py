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
from adapt.intent import IntentBuilder
from fuzzywuzzy import process
from mycroft import removes_context
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler
from mycroft.util.log import getLogger
from os.path import dirname
import traceback

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
UNDO_CONTEXT = "UndoContext"
CONFIRM_CONTEXT = "ConfirmContext"
EXCEPTION_CONTEXT = "ExceptionContext"

LOGGER = getLogger(__name__)


class CowsLists(MycroftSkill):
    def __init__(self):
        super(CowsLists, self).__init__(name="TheCowsLists")
        reload(cow_rest)
        self.last_traceback = None

    def initialize(self):
        self.load_data_files(dirname(__file__))

    def get_config(self):
        try:
            try:
                if not cow_rest.api_key:
                    cow_rest.api_key = self.config.get('api_key')
            except AttributeError:
                cow_rest.api_key = self.settings.get('api_key')

            try:
                if not cow_rest.secret:
                    cow_rest.secret = self.config.get('secret')
            except AttributeError:
                cow_rest.secret = self.settings.get('secret')

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

    def add_task_to_list(self, task_name, list_name, list_id):
        taskseries_id, task_id, error_text, error_code = cow_rest.add_task(task_name, list_id)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})

            return False

        self.speak_dialog("AddTaskToList", {TASK_PARAMETER: task_name, LIST_PARAMETER: list_name})
        c = {"dialog": "AddTaskToListUndo",
             "dialogParam": {TASK_PARAMETER: task_name, LIST_PARAMETER: list_name},
             "task": {"task_id": task_id,
                      "task_name": task_name,
                      "taskseries_id": taskseries_id,
                      "list_id": list_id,
                      "list_name": list_name}}

        self.set_context(UNDO_CONTEXT, json.dumps(c))

        return True

    def find_list(self, list_name):
        list_result, error_text, error_code = cow_rest.get_list()

        if error_text:
            return None, None, None, error_text, error_code

        # Workaround the intent parser remove the word list: First, try to match to a "list_name list"
        list_name_best_match, significance = process.extractOne(list_name + " list",
                                                                map(lambda x: str(x['name']).lower(),
                                                                    list_result))

        # Then try to match to "list_name"
        if significance < 100:
            list_name_best_match, significance = process.extractOne(list_name,
                                                                    map(lambda x: str(x['name']).lower(),
                                                                        list_result))

        list_id = filter(lambda x: str(x['name']).lower() == list_name_best_match, list_result)[0]['id']

        return list_name_best_match, list_id, significance, None, None

    def find_task_on_list(self, task_name, list_name):
        list_name_best_match, list_id, significance, error_text, error_code = self.find_list(list_name)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return None, None, None, None

        if significance < 100:
            self.speak_dialog("UsingAnotherList",
                              {LIST_PARAMETER: list_name, BEST_MATCH_PARAMETER: list_name_best_match})

        task_list, error_code, error_text = cow_rest.list_task("status:incomplete", list_id)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return None, None, None, None

        flat_task_list = cow_rest.flat_task_list(task_list)

        if len(flat_task_list) == 0:
            self.speak_dialog("NoTaskOnList",
                              {LIST_PARAMETER: list_name_best_match})
            return None, None, None, None

        task_name_best_match, significance = process.extractOne(task_name,
                                                                map(lambda x: str(x['task_name']).lower(),
                                                                    flat_task_list))

        selected_task_list = filter(lambda x: str(x['task_name']).lower() == task_name_best_match, flat_task_list)

        return list_name_best_match, task_name_best_match, list_id, selected_task_list

    def complete_task_on_list(self, task_name, list_name):
        list_name_best_match, task_name_best_match, list_id, selected_task_list = self.find_task_on_list(task_name,
                                                                                                         list_name)
        if not list_name_best_match:
            return False

        if task_name.lower() != task_name_best_match.lower():
            self.speak_dialog("FindTaskOnListMismatch",
                              {TASK_PARAMETER: task_name,
                               BEST_MATCH_PARAMETER: task_name_best_match,
                               LIST_PARAMETER: list_name_best_match})

        error_text, error_code = cow_rest.get_timeline(cow_rest)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return False

        c = {"dialog": "CompleteTaskOnListUndo",
             "dialogParam": {TASK_PARAMETER: task_name_best_match, LIST_PARAMETER: list_name_best_match},
             'transaction_id': []}

        for t in selected_task_list:
            transaction_id, error_text, error_code = cow_rest.complete_task(t['task_id'],
                                                                            t['taskseries_id'],
                                                                            list_id)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                # RECOVER
                return False

            c['transaction_id'].append(transaction_id)

        if len(selected_task_list) == 1:
            self.speak_dialog("CompleteTaskOnList", {TASK_PARAMETER: task_name_best_match,
                                                     LIST_PARAMETER: list_name_best_match})
        else:
            self.speak_dialog("CompleteManyTasksOnList", {NOF_TASK_PARAMETER: str(len(selected_task_list)),
                                                          TASK_PARAMETER: task_name_best_match,
                                                          LIST_PARAMETER: list_name_best_match})

        self.set_context(UNDO_CONTEXT, json.dumps(c))

        return True

    def speak_exception(self, trace_back, function_name):
        self.last_traceback = "Error in " + function_name + ": " + trace_back
        LOGGER.exception(self.last_traceback)
        self.speak_dialog('GeneralError',
                          {FUNCTION_NAME_PARAMETER: function_name,
                           LINE_PARAMETER: format(sys.exc_info()[-1].tb_lineno)})
        self.remove_context(CONFIRM_CONTEXT)
        self.set_context(EXCEPTION_CONTEXT)
        self.speak_dialog('AskSendException', None, expect_response=True)

    @intent_handler(IntentBuilder("SendExceptionIntent").require("YesKeyword").require(EXCEPTION_CONTEXT).build())
    @removes_context(EXCEPTION_CONTEXT)
    @removes_context(UNDO_CONTEXT)
    @removes_context(CONFIRM_CONTEXT)
    def send_exception_intent(self):
        try:
            mail_body = "This mail contains details of an exception in the cows lists<br>" \
                        + "Please report the issue at " \
                        + '<a href = "https://github.com/CarstenAgerskov/skill-the-cows-lists/issues">https://github.com/CarstenAgerskov/skill-the-cows-lists/issues</a>' \
                        + "<br>When reporting the issue, make sure to include:<br><br>" \
                        + "* A description of your dialog with Mycroft<br>" \
                        + "* Any other details that may help<br>" \
                        + "* The exception text below<br><br>" \
                        + self.last_traceback

            self.send_email("Exception details", mail_body)
            self.speak_dialog('SendException')

        except Exception as e:
            LOGGER.exception("Error in send_exception: {0}".format(e))
            self.speak_dialog('GeneralError',
                              {FUNCTION_NAME_PARAMETER: "send exception",
                               LINE_PARAMETER: format(sys.exc_info()[-1].tb_lineno)})

    @intent_handler(IntentBuilder("AuthenticateIntent").require("AuthenticateKeyword").build())
    @removes_context(UNDO_CONTEXT)
    @removes_context(CONFIRM_CONTEXT)
    def authenticate_intent(self):
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
            self.speak_exception(traceback.format_exc(), "get token intent")

    @intent_handler(IntentBuilder("GetTokenIntent").require("GetTokenKeyword").build())
    @removes_context(UNDO_CONTEXT)
    @removes_context(CONFIRM_CONTEXT)
    def get_token_intent(self):
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
            self.speak_exception(traceback.format_exc(), "get token intent")

    @intent_handler(IntentBuilder("AddTaskToListIntent").require("AddTaskToListKeyword").require(TASK_PARAMETER).
                    require(LIST_PARAMETER).build())
    def add_task_to_list_intent(self, message):
        try:
            self.remove_context(UNDO_CONTEXT)
            self.remove_context(CONFIRM_CONTEXT)
            task_name = message.data.get(TASK_PARAMETER)
            list_name = message.data.get(LIST_PARAMETER)

            if not self.operation_init():
                return

            error_text, error_code = cow_rest.get_timeline(cow_rest)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                return

            list_name_best_match, list_id, significance, error_text, error_code = self.find_list(list_name)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                return

            if significance < 100:
                c = {"dialog": "AddTaskToList",
                     "dialogParam": {TASK_PARAMETER: task_name, LIST_PARAMETER: list_name_best_match},
                     "task": {"task_name": task_name,
                              "list_id": list_id,
                              "list_name": list_name_best_match}}

                self.set_context(CONFIRM_CONTEXT, json.dumps(c))
                self.speak_dialog("AddTaskToListMismatch",
                                  {LIST_PARAMETER: list_name, BEST_MATCH_PARAMETER: list_name_best_match},
                                  expect_response=True)
                return

            self.add_task_to_list(task_name, list_name_best_match, list_id)

        except Exception:
            self.speak_exception(traceback.format_exc(), "add task to list intent")

    @intent_handler(IntentBuilder("FindTaskOnListIntent").require("FindTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_PARAMETER).build())
    def find_task_on_list_intent(self, message):
        try:
            task_name = message.data.get(TASK_PARAMETER)
            list_name = message.data.get(LIST_PARAMETER)

            if not self.operation_init():
                return

            list_name_best_match, task_name_best_match, list_id, selected_task_list = self.find_task_on_list(task_name,
                                                                                                             list_name)

            if task_name.lower() != task_name_best_match.lower():
                self.speak_dialog("FindTaskOnListMismatch",
                                  {TASK_PARAMETER: task_name,
                                   BEST_MATCH_PARAMETER: task_name_best_match,
                                   LIST_PARAMETER: list_name_best_match})
            else:
                self.speak_dialog("FindTaskOnList",
                                  {TASK_PARAMETER: task_name_best_match, LIST_PARAMETER: list_name_best_match})

        except Exception:
            self.speak_exception(traceback.format_exc(), "find task intent")

    @intent_handler(IntentBuilder("CompleteTaskOnListIntent").require("CompleteTaskOnListKeyword").
                    require(TASK_PARAMETER).
                    require(LIST_PARAMETER).build())
    def complete_task_on_list_intent(self, message):
        try:
            self.remove_context(UNDO_CONTEXT)
            self.remove_context(CONFIRM_CONTEXT)
            task_name = message.data.get(TASK_PARAMETER)
            list_name = message.data.get(LIST_PARAMETER)

            if not self.operation_init():
                return

            self.complete_task_on_list(task_name, list_name)

        except Exception:
            self.speak_exception(traceback.format_exc(), "complete task on list intent")

    @intent_handler(IntentBuilder("ReadListIntent").require("ReadListKeyword").require(LIST_PARAMETER).build())
    def read_list_intent(self, message):
        try:
            list_name = message.data.get(LIST_PARAMETER)

            if not self.operation_init():
                return

            list_name_best_match, list_id, significance, error_text, error_code = self.find_list(list_name)

            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                return

            if significance < 100:
                self.speak_dialog("UsingAnotherList", {LIST_PARAMETER: list_name,
                                                       BEST_MATCH_PARAMETER: list_name_best_match})

            task_list, error_code, error_text = cow_rest.list_task("status:incomplete", list_id)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                return

            flat_task_list = cow_rest.flat_task_list(task_list)

            if len(flat_task_list) == 0:
                self.speak_dialog("NoTaskOnList",
                                  {LIST_PARAMETER: list_name_best_match})
                return

            self.speak_dialog("ReadListOneItem" if len(flat_task_list) == 1 else "ReadList",
                              {LIST_PARAMETER: list_name_best_match,
                               NOF_TASK_PARAMETER: str(len(flat_task_list))})

            map(lambda x: self.speak(x['task_name']), flat_task_list)

        except Exception:
            self.speak_exception(traceback.format_exc(), "read list intent")

    # RTM can roll back some operations, other has to be compensated. The undo itent hides this complexity
    @intent_handler(IntentBuilder("UndoIntent").require("UndoKeyword").require(UNDO_CONTEXT).build())
    @removes_context(UNDO_CONTEXT)
    def undo_intent(self, message):
        try:
            c = json.loads(message.data.get(UNDO_CONTEXT))
            if str(c['dialog']) == "AddTaskToListUndo":
                transaction_id, error_text, error_code = cow_rest.delete_task(c['task']['task_id'],
                                                                              c['task']["taskseries_id"],
                                                                              c['task']["list_id"])

                if error_text:
                    self.speak_dialog('RestResponseError',
                                      {ERROR_TEXT_PARAMETER: error_text,
                                       ERROR_CODE_PARAMETER: error_code})
                    return

                self.speak_dialog(c['dialog'], c['dialogParam'])

            if c['dialog'] == "CompleteTaskOnListUndo":
                for t in c['transaction_id']:
                    error_text, error_code = cow_rest.roll_back(str(t))
                    if error_text:
                        self.speak_dialog('RestResponseError',
                                          {ERROR_TEXT_PARAMETER: error_text,
                                           ERROR_CODE_PARAMETER: error_code})
                        return
                self.speak_dialog(c['dialog'], c['dialogParam'])

        except Exception:
            self.speak_exception(traceback.format_exc(), "undo intent")

    @intent_handler(IntentBuilder("ConfirmIntent").require("YesKeyword").require("ConfirmContext").build())
    def confirm_intent(self, message):
        self.remove_context(CONFIRM_CONTEXT)
        try:
            c = json.loads(message.data.get(CONFIRM_CONTEXT))
            if str(c['dialog']) == "AddTaskToList":
                self.add_task_to_list(c['task']['task_name'], c['task']['list_name'], c['task']['list_id'])

        except Exception:
            self.speak_exception(traceback.format_exc(), "confirm intent")

    @intent_handler(
        IntentBuilder("NoConfirmIntent").require("NoKeyword").one_of(CONFIRM_CONTEXT, EXCEPTION_CONTEXT).build())
    @removes_context(CONFIRM_CONTEXT)
    @removes_context(EXCEPTION_CONTEXT)
    def no_confirm_intent(self):
        self.speak_dialog('NoConfirm')


def create_skill():
    return CowsLists()

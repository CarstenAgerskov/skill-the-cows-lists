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
from datetime import datetime

from adapt.intent import IntentBuilder
from fuzzywuzzy import process
from mycroft import removes_context
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler
from mycroft.util.log import getLogger
from importlib import reload
from mycroft.util.format import nice_date, nice_date_time, nice_time

__author__ = 'cagerskov'

HOME_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HOME_DIR)

import cow_rest
reload(cow_rest) # make sure live update work
import time_conversion
reload(time_conversion) # make sure live update work
import constants
reload(constants)
import model
reload(model)
import regex_evaluation
reload(regex_evaluation)

from constants import TASK_PARAMETER, LIST_PARAMETER, BEST_MATCH_PARAMETER, \
    ERROR_TEXT_PARAMETER, ERROR_CODE_PARAMETER, FUNCTION_NAME_PARAMETER, \
    LINE_PARAMETER, NOF_TASK_PARAMETER, DUE_PARAMETER, UNDO_CONTEXT, \
    LIST_CONTEXT, TASK_CONTEXT, TEST_CONTEXT, \
    MAX_TASK_COMPLETE

from model import create_filter_dialog, create_add_task_dialog, \
    create_find_list_dialog, create_find_task_dialog, create_list_tuple, \
    create_task_dialog, create_task_tuple, create_task_filter, cows_filter, \
    flat_task_list

LOGGER = getLogger(__name__)


class CowsLists(MycroftSkill):
    def __init__(self):
        super(CowsLists, self).__init__(name='TheCowsLists')
        self.no_keyword = None
        self.yes_keyword = None
        self.authenticate_mail_body = None
        self.report_issue_mail_body = None
        self.local_regex = {}
        self.time_conversion = None
        self.use_24_hour = False
        self.regex_eval = None

    def initialize(self):
        try:
            # Set root_dir in case we ar running outside the Mycroft ecosystem
            if not self.root_dir:
                self.root_dir = HOME_DIR
            self.time_conversion = time_conversion.TimeConversion(
                self.location_timezone)
            self.use_24_hour = self.config_core.get('time_format') == 'full'
            with open(self.find_resource('NoKeyword.voc', 'vocab'), 'r') \
                    as no_keyword_file, \
                open(self.find_resource("YesKeyword.voc", "vocab"), 'r') \
                        as yes_keyword_file, \
                open(self.find_resource("AuthenticateMailBody.txt", "dialog"),
                     'r') as authenticate_mail_body_file, \
                open(self.find_resource("ReportIssueMailBody.txt", "dialog"),
                     'r') as report_issue_mail_file:
                self.no_keyword = no_keyword_file.read()
                self.yes_keyword = yes_keyword_file.read()
                self.authenticate_mail_body = \
                    authenticate_mail_body_file.read()
                self.report_issue_mail_body = report_issue_mail_file.read()

                self.regex_eval = regex_evaluation.RegexEvaluation(
                    self.find_resource("LocalRegex.json", "regex"))

        except Exception:
            self.mail_exception(traceback.format_exc(), '', 'initialize')


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


    def set_task_context(self, task_tuple):
        self.set_context(
            TASK_CONTEXT,
            json.dumps({'id': task_tuple.id,
                        'name': task_tuple.name,
                        'taskseries_id': task_tuple.taskseries_id}))


    def set_list_context(self, list_tuple):
        self.set_context(LIST_CONTEXT,
                         json.dumps({'id': list_tuple.id,
                                     'name': list_tuple.name}))


    def task_context_to_tuple(self, task_context):
        c = json.loads(task_context)
        return create_task_tuple(c['name'], id=c['id'],
                                 taskseries_id=c['taskseries_id'])


    def list_context_to_tuple(self, list_context):
        c = json.loads(list_context)
        return create_list_tuple(name=c['name'], id=c['id'])

    def unid_list(self, list_tuple):
        return create_list_tuple(name=list_tuple.name,
                                task_list=list_tuple.task_list)

    def unid_task(self, task_tuple):
        return create_task_tuple(name=task_tuple.name,
                                 significance=task_tuple.significance,
                                 due=task_tuple.due,
                                 priority=task_tuple.priority)

    def get_timeline(self):
        error_text, error_code = cow_rest.get_timeline(cow_rest)
        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return False
        return True


    # Take a list tuple with a name, and find the id
    # If no matching name is found, optionally ask if closest match should be
    # returned
    # Returns list id if succeeded, otherwise list id is None
    def find_list(self, list_tuple, find_list_dialog=create_find_list_dialog()):

        list_result, error_text, error_code = cow_rest.get_list()

        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return self.unid_list(list_tuple)

        # Workaround the intent parser remove the word list: First, try to
        # match to a "list_name list"
        list_name_best_match, significance = (
            process.extractOne(list_tuple.name + " list",
                               map(lambda x: x['name'].lower(),
                                   list_result)))

        # Then try to match to "list_name"
        if significance < 100:
            list_name_best_match, significance = (
                process.extractOne(list_tuple.name,
                                   map(lambda x: x['name'].lower(),
                                       list_result)))

        list_id = [x for x in list_result if x['name'].lower() ==
                   list_name_best_match][0]['id']

        if find_list_dialog.using_another_list and significance < 100:
            response = self.get_response(
                'UsingAnotherList',
                {LIST_PARAMETER: list_tuple.name,
                 BEST_MATCH_PARAMETER: list_name_best_match},
                num_retries=0)

            if not response or response not in self.yes_keyword:
                self.speak_dialog('NoConfirm')
                return self.unid_list(list_tuple)

        return create_list_tuple(name=list_name_best_match,
                                 id=list_id)


    def speak_task(self, task_tuple, task_dialog=create_task_dialog()):
        self.speak(task_tuple.name)

        if task_tuple.due and (task_dialog.due_date or task_dialog.due_time):
            local_now = self.time_conversion.naive_utc_to_local(datetime.utcnow())
            local_dt = self.time_conversion.naive_utc_to_local(task_tuple.due)

            date_str = (
                nice_date_time(
                    local_dt,
                    lang=self.lang,
                    now=local_now,
                    use_24hour=self.use_24_hour,
                    use_ampm=not self.use_24_hour
                ) if (task_dialog.due_date and
                      task_dialog.due_time and
                      task_tuple.has_due_time != '0')
                else nice_date(
                    local_dt,
                    lang=self.lang,
                    now=local_now
                ) if task_dialog.due_date
                else nice_time(
                    local_dt,
                    lang=self.lang,
                    use_24hour=self.use_24_hour,
                    use_ampm=not self.use_24_hour
                ) if (task_dialog.due_time and
                      task_tuple.has_due_time != '0')
                else None)

            if date_str:
                self.speak_dialog('WithDueTime', {DUE_PARAMETER: date_str})

        if task_dialog.priority and task_tuple.priority:
            pass



    # Filter tasks on a list, taking list name and filter as a minimum,
    # optionally list id
    # In no list id is given, and
    # if using_another_list=True, the user is prompted with the closest matching
    # list name if the list name does not match any known names
    # If using_another_list=False/None the best match is selected silently
    # Returns list id if a list was found, and a filtered task list, if found
    # If either list id or task list is None, the call failed
    def filter_tasks_on_list(self, list_tuple_orig,
                             task_filter=create_task_filter(),
                             filter_dialog=create_filter_dialog(),
                             find_list_dialog=create_find_list_dialog(),
                             task_dialog=create_task_dialog()):

        list_tuple = (list_tuple_orig if list_tuple_orig.id
                      else self.find_list(list_tuple_orig,
                                          find_list_dialog=find_list_dialog))

        if not list_tuple.id:
            return list_tuple

        task_list, error_code, error_text = cow_rest.list_task(
            cows_filter(task_filter),
            list_tuple.id)

        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})
            return self.unid_list(list_tuple_orig)

        flat_task_list = model.flat_task_list(task_list)

        if filter_dialog.no_task_on_list and len(flat_task_list) == 0:
            self.speak_dialog("NoTaskOnList",
                              {LIST_PARAMETER: list_tuple.name})
            if filter_dialog.due_date:
                self.speak_dialog("WithDueDate",
                                  {DUE_PARAMETER: task_filter.due })

        if filter_dialog.read_list and len(flat_task_list) > 0:
            self.speak_dialog(
                "ReadListOneItem" if len(flat_task_list) == 1 else "ReadList",
                {LIST_PARAMETER: list_tuple.name,
                 NOF_TASK_PARAMETER: str(len(flat_task_list))})
            if filter_dialog.due_date:
                self.speak_dialog("WithDueDateOneTask"
                                  if len(flat_task_list) == 1
                                  else "WithDueDate",
                                  {DUE_PARAMETER: task_filter.due})

            for x in flat_task_list:
                self.speak_task(x, task_dialog=task_dialog)

        return create_list_tuple(
            name=list_tuple.name,
            id=list_tuple.id,
            task_list=flat_task_list)


    # Find a task on a list given minimum task name and list name
    # find task id if not present
    # Returns task id, taskseries id, list id, and task_list
    # Call failed if any of these missing
#todo: is find_task_on_list and filter_task_on_list the same function?
    def find_task_on_list(
            self,
            task_tuple,
            list_tuple_orig,
            task_filter=create_task_filter(),
            find_task_dialog=create_find_task_dialog(),
            filter_dialog=create_filter_dialog(),
            find_list_dialog=create_find_list_dialog()):

        # filter_task_on_list will find the list id if it is not supplied
        list_tuple = self.filter_tasks_on_list(
            list_tuple_orig,
            task_filter=task_filter,
            filter_dialog=filter_dialog,
            find_list_dialog=find_list_dialog)

        if not (list_tuple.id and len(list_tuple.task_list) > 0):
            return list_tuple

        task_name_best_match, significance = (
            process.extractOne(
                task_tuple.name,
                [x.name.lower() for x in list_tuple.task_list]))

        # There may be several tasks with the same task_name_best_match,
        # selected_task_list holds all
        selected_task_list = [x for x in list_tuple.task_list
                              if x.name.lower() == task_name_best_match]

        if (find_task_dialog.find_task_on_list and
            task_tuple.name.lower() == task_name_best_match.lower()):
            self.speak_dialog("FindTaskOnList", {
                TASK_PARAMETER: task_name_best_match,
                LIST_PARAMETER: list_tuple.name})

        if (find_task_dialog.find_task_on_list_mismatch and
                task_tuple.name.lower() != task_name_best_match.lower()):
            self.speak_dialog("FindTaskOnListMismatch",
                              {TASK_PARAMETER: task_tuple.name,
                               BEST_MATCH_PARAMETER: task_name_best_match,
                               LIST_PARAMETER: list_tuple.name})

        return create_list_tuple(list_tuple.name,
                                 id=list_tuple.id,
                                 task_list=selected_task_list)


    def add_task_to_list(
            self,
            task_tuple_orig,
            list_tuple_orig,
            add_task_dialog=create_add_task_dialog(),
            find_list_dialog=create_find_list_dialog()):

        list_tuple = (list_tuple_orig if list_tuple_orig.id
                      else self.find_list(list_tuple_orig,
                                          find_list_dialog=find_list_dialog))

        if not list_tuple.id:
            return list_tuple

        taskseries_id, task_id, error_text, error_code = (
            cow_rest.add_task(task_tuple_orig.name, list_tuple.id))

        if error_text:
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: error_text,
                               ERROR_CODE_PARAMETER: error_code})

            return self.create_list_tuple(list_tuple.name,
                                          id=list_tuple.id,
                                          task_list=[self.unid_task(task_tuple_orig)])

        c = {"dialog": "AddTaskToListUndo",
             "dialogParam": {TASK_PARAMETER: task_tuple_orig.name,
                             LIST_PARAMETER: list_tuple.name},
             "task": {"task_id": task_id,
                      "task_name": task_tuple_orig.name,
                      "taskseries_id": taskseries_id,
                      "list_id": list_tuple.id,
                      "list_name": list_tuple.name}}

        self.set_context(UNDO_CONTEXT, json.dumps(c))

        task_tuple = create_task_tuple(task_tuple_orig.name,
                                       id=task_id, taskseries_id=taskseries_id)

        if add_task_dialog.add_task_to_list:
            self.speak_dialog("AddTaskToList",
                              {TASK_PARAMETER: task_tuple.name,
                               LIST_PARAMETER: list_tuple.name})

        return create_list_tuple(list_tuple.name,
                                 id=list_tuple.id,
                                 task_list=[task_tuple])

    def complete_task_on_list(
            self,
            task_tuple,
            list_tuple_orig,
            find_task_dialog=create_find_task_dialog(),
            filter_dialog=create_filter_dialog(),
            find_list_dialog=create_find_list_dialog()):

        list_tuple = (create_list_tuple(
            list_tuple_orig.name,
            id=list_tuple_orig.id,
            task_list=[task_tuple]) if task_tuple.id
                      else self.find_task_on_list(
            task_tuple,
            list_tuple_orig,
            find_task_dialog=find_task_dialog,
            filter_dialog=filter_dialog,
            find_list_dialog=find_list_dialog))

        if not list_tuple.id or len(list_tuple.task_list) == 0:
            return list_tuple

        if task_tuple.name.lower() != list_tuple.task_list[0].name.lower():
            response = self.get_response('DoYouWantToCompleteIt', num_retries=0)

            if not response or response not in self.yes_keyword:
                self.speak_dialog('NoConfirm')
                return self.unid_list(list_tuple)

        if not self.get_timeline():
            return self.unid_list(list_tuple)

        c = {"dialog": "CompleteTaskOnListUndo",
             "dialogParam": {
                 TASK_PARAMETER: list_tuple.task_list[0].name.lower(),
                 LIST_PARAMETER: list_tuple.name},
             'transaction_id': []}

        for t in list_tuple.task_list:
            transaction_id, error_text, error_code = cow_rest.complete_task(
                t.id,
                t.taskseries_id,
                list_tuple.id)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                # RECOVER
                return self.unid_list(list_tuple)

            c['transaction_id'].append(transaction_id)

        if len(list_tuple.task_list) == 1:
            self.speak_dialog("CompleteTaskOnList", {
                TASK_PARAMETER: list_tuple.task_list[0].name.lower(),
                LIST_PARAMETER: list_tuple.name})
        else:
            self.speak_dialog("CompleteManyTasksOnList", {
                NOF_TASK_PARAMETER: str(len(list_tuple.task_list)),
                TASK_PARAMETER: list_tuple.task_list[0].name.lower(),
                LIST_PARAMETER: list_tuple.name})

        self.set_context(UNDO_CONTEXT, json.dumps(c))

        return list_tuple


    def complete_list(
            self,
            list_tuple_orig,
            filter_dialog=create_filter_dialog(),
            find_list_dialog=create_find_list_dialog()):

        list_tuple = self.filter_tasks_on_list(
            list_tuple_orig,
            filter_dialog=filter_dialog,
            find_list_dialog=find_list_dialog)

        if not (list_tuple.id and len(list_tuple.task_list) > 0):
            return list_tuple

        nof_tasks_to_complete = len(list_tuple.task_list)

        if nof_tasks_to_complete > MAX_TASK_COMPLETE:
            nof_tasks_to_complete = MAX_TASK_COMPLETE
            self.speak_dialog('CompletePartOfListStart', {
                NOF_TASK_PARAMETER: str(len(list_tuple.task_list))})

        if nof_tasks_to_complete > 10:
            self.speak_dialog('CompleteListStart',
                              {NOF_TASK_PARAMETER: nof_tasks_to_complete,
                               LIST_PARAMETER: list_tuple.name})

        if not self.get_timeline():
            return self.unid_list(list_tuple)

        c = {
            "dialog": ("CompleteListOneTaskUndo" if nof_tasks_to_complete == 1
                       else "CompleteListUndo"),
            "dialogParam": {NOF_TASK_PARAMETER: nof_tasks_to_complete,
                            LIST_PARAMETER: list_tuple.name},
            'transaction_id': []}

        i = nof_tasks_to_complete
        for t in list_tuple.task_list:
            transaction_id, error_text, error_code = cow_rest.complete_task(
                t.id,
                t.taskseries_id,
                list_tuple.id)
            if error_text:
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: error_text,
                                   ERROR_CODE_PARAMETER: error_code})
                # RECOVER
                return self.unid_list(list_tuple)

            c['transaction_id'].append(transaction_id)

            i = i - 1
            if i < 1:
                break

        self.speak_dialog(
            ("CompleteListOneTask" if nof_tasks_to_complete == 1
             else "CompleteList"),
            {LIST_PARAMETER: list_tuple.name,
             NOF_TASK_PARAMETER: nof_tasks_to_complete})

        self.set_context(UNDO_CONTEXT, json.dumps(c))

        return list_tuple


    def mail_exception(self, trace_back, message, function_name):
        try:
            if message.data.get(TEST_CONTEXT):
                # Last traceback may not exist if testing
                self.speak("Test context:")
                return

            traceback_text = "Error in " + function_name + ": " + trace_back
            LOGGER.exception(traceback_text)

            self.speak_dialog('GeneralError',
                              {FUNCTION_NAME_PARAMETER: function_name,
                               LINE_PARAMETER: format(
                                   sys.exc_info()[-1].tb_lineno)})

            response = self.get_response('AskSendException', num_retries=0)

            if not response or response not in self.yes_keyword:
                self.speak_dialog('NoConfirm')
                return

            mail_body = self.report_issue_mail_body.format(
                utterance = message.data.get('utterance'),
                exception= traceback_text)
            mail_subject = self.dialog_renderer.templates[
                'ReportIssueMailSubject'][0]

            self.send_email(mail_subject, mail_body)
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

            mail_body = self.authenticate_mail_body.format(auth_url=auth_url)
            mail_subject = self.dialog_renderer.templates['AuthenticateMailSubject'][0]

            self.send_email(mail_subject, mail_body)
            self.speak_dialog("EmailSent")

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
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
            self.mail_exception(traceback.format_exc(), message,
                                 "get token intent")


    @intent_handler(IntentBuilder("AddTaskIntent").require(
        "AddTaskToListKeyword").require(TASK_PARAMETER).require(LIST_CONTEXT).
                    optionally(TEST_CONTEXT).build())
    def add_task_intent(self, message):
        try:
            list_tuple = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_eval.eval(
                message, ['AddTaskToList', 'AddTask'])
            if not m:
                self.speak_dialog("IDontUnderstand")
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

            list_tuple = self.add_task_to_list(
                create_task_tuple(task_name),
                list_tuple)

            # The user added a task to a list in context, ask for more
            while list_tuple.task_list[0] and list_tuple.task_list[0].id:
                task_name = self.get_response("AnythingElse",
                                              {TASK_PARAMETER: task_name},
                                              num_retries=0)
                if not task_name or task_name in self.no_keyword:
                    self.speak_dialog("AnythingElseEnd",
                                      {LIST_PARAMETER: list_tuple.name})
                    if list_tuple.id:
                        self.set_list_context(list_tuple)
                    if list_tuple.task_list[0] and list_tuple.task_list[0].id:
                        self.set_task_context(list_tuple.task_list[0])

                    break

                list_tuple = self.add_task_to_list(
                    create_task_tuple(task_name),
                    list_tuple)


        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "add task intent")


    @intent_handler(IntentBuilder("AddTaskToListIntent").require(
        "AddTaskToListKeyword").require(TASK_PARAMETER).require(LIST_PARAMETER).
                    optionally(TEST_CONTEXT).build())
    def add_task_to_list_intent(self, message):
        try:
            self.remove_context(UNDO_CONTEXT)

            k, m = self.regex_eval.eval(message, ['AddTaskToList'])
            if not m:
                self.speak_dialog("IDontUnderstand")
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

            list_tuple = self.add_task_to_list(
                create_task_tuple(task_name),
                create_list_tuple(list_name),
                add_task_dialog=create_add_task_dialog(add_task_to_list=True),
                find_list_dialog=create_find_list_dialog(using_another_list=True))

            if (list_tuple.id and
                    list_tuple.task_list[0] and
                    list_tuple.task_list[0].id):
                self.set_list_context(list_tuple)
                self.set_task_context(list_tuple.task_list[0])

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "add task to list intent")


    @intent_handler(IntentBuilder("FindTaskIntent").require(
        "FindTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_CONTEXT).optionally(TEST_CONTEXT).build())
    def find_task_intent(self, message):
        try:
            list_tuple_orig = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_eval.eval(message,
                                   ['FindTaskOnList', 'FindTask'])
            if not m:
                self.speak_dialog("IDontUnderstand")
                return

            if k == 'FindTaskOnList':
                self.find_task_on_list_intent(message)
                return

            task_name = m.groupdict()[TASK_PARAMETER]

            self.set_context(LIST_CONTEXT, message.data.get(LIST_CONTEXT))

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, find task intent: task name "
                    + task_name + ", list name " + list_tuple_orig.name)
                return

            if not self.operation_init():
                return

            list_tuple = self.find_task_on_list(
                create_task_tuple(task_name),
                list_tuple_orig,
                find_task_dialog=create_find_task_dialog(
                    find_task_on_list=True,
                    find_task_on_list_mismatch=True),
                filter_dialog=create_filter_dialog(no_task_on_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)
            if len(list_tuple.task_list) > 0 and list_tuple.task_list[0].id:
                self.set_task_context(list_tuple.task_list[0])

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "find task intent")


    @intent_handler(IntentBuilder("FindTaskOnListIntent").require(
        "FindTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_PARAMETER).optionally(TEST_CONTEXT).build())
    def find_task_on_list_intent(self, message):
        try:
            k, m = self.regex_eval.eval(message, ['FindTaskOnList'])
            if not m:
                self.speak_dialog("IDontUnderstand")
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

            list_tuple = self.find_task_on_list(
                create_task_tuple(task_name),
                create_list_tuple(list_name),
                find_task_dialog=create_find_task_dialog(
                    find_task_on_list=True,
                    find_task_on_list_mismatch=True),
                filter_dialog=create_filter_dialog(no_task_on_list=True),
                find_list_dialog=create_find_list_dialog(using_another_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)
            if len(list_tuple.task_list) > 0 and list_tuple.task_list[0].id:
                self.set_task_context(list_tuple.task_list[0])

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "find task on list intent")


    @intent_handler(IntentBuilder("CompleteTaskIntent").require(
        "CompleteTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_CONTEXT).optionally(TASK_CONTEXT).
                    optionally(TEST_CONTEXT).build())
    def complete_task_intent(self, message):
        try:
            list_tuple_orig = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))
            task_name = None

            k, m = self.regex_eval.eval(
                message,
                ['CompleteAll', 'CompleteTaskInContext', 'CompleteTaskOnList',
                 'CompleteTask'])
            if not m:
                self.speak_dialog("IDontUnderstand")
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
                    message.data.get(TASK_CONTEXT))
                task_name = task_tuple.name

            if k == 'CompleteTask':
                task_name = m.groupdict()[TASK_PARAMETER]

            self.remove_context(UNDO_CONTEXT)
            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, complete task intent: task name " +
                    task_name + ", list name " + list_tuple_orig.name)
                return

            if not self.operation_init():
                return

            list_tuple = self.complete_task_on_list(
                create_task_tuple(task_name),
                list_tuple_orig,
                find_task_dialog=create_find_task_dialog(find_task_on_list_mismatch=True),
                find_list_dialog=create_filter_dialog(no_task_on_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "complete task intent")


    @intent_handler(IntentBuilder("CompleteTaskOnListIntent").require(
        "CompleteTaskOnListKeyword").require(TASK_PARAMETER).
                    require(LIST_PARAMETER).optionally(TEST_CONTEXT).build())
    def complete_task_on_list_intent(self, message):
        try:
            k, m = self.regex_eval.eval(
                message, ['CompleteList', 'CompleteTaskOnList'])
            if not m:
                self.speak_dialog("IDontUnderstand")
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

            list_tuple = self.complete_task_on_list(
                create_task_tuple(task_name),
                create_list_tuple(list_name),
                create_find_task_dialog(find_task_on_list_mismatch=True),
                create_filter_dialog(no_task_on_list=True),
                create_find_list_dialog(using_another_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "complete task on list intent")

    # The intent is to complete all tasks on the list in context
    # This intent does not have an intent decorator, because is is activeted
    # through another intent. So, on the technical level it is not an intent,
    # but it is an intent on the conceptual level. But due to very similar
    # wordings, Adapt cannot distinguish between this intent and other.
    def complete_intent(self, message):
        try:
            list_tuple_orig = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_eval.eval(
                message, ['CompleteList', 'CompleteAll'])
            if not m:
                self.speak_dialog("IDontUnderstand")
                return

            if k == 'CompleteList':
                self.complete_list_intent(message)
                return

            self.remove_context(UNDO_CONTEXT)
            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, complete intent: list name " +
                    list_tuple_orig.name)
                return

            if not self.operation_init():
                return

            list_tuple = self.complete_list(
                list_tuple_orig,
                filter_dialog=create_filter_dialog(no_task_on_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "complete intent")


    # The intent is to complete all tasks on the list Spoken in the message.
    # This intent does not have an intent decorator, because is is activeted
    # through another intent. So, on the technical level it is not an intent,
    # but it is an intent on the conceptual level. But due to very similar
    # wordings, Adapt cannot distinguish between this intent and other.
    def complete_list_intent(self, message):
        try:
            k, m = self.regex_eval.eval(message, ['CompleteList'])
            if not m:
                self.speak_dialog("IDontUnderstand")
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

            list_tuple = self.complete_list(
                create_list_tuple(list_name),
                filter_dialog=create_filter_dialog(no_task_on_list=True),
                find_list_dialog=create_find_list_dialog(
                    using_another_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "complete list intent")



    @intent_handler(
        IntentBuilder("ReadIntent").require("ReadListKeyword").require(
            LIST_CONTEXT).optionally(TEST_CONTEXT).build())
    def read_intent(self, message):
        try:
            list_tuple_orig = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_eval.eval(message,
                                   ['ReadList', 'Read'])
            if not m:
                self.speak_dialog("IDontUnderstand")
                return

            if k == 'ReadList':
                self.read_list_intent(message)
                return

            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, read intent: list name " +
                    list_tuple_orig.name)
                return

            if not self.operation_init():
                return

            list_tuple = self.filter_tasks_on_list(
                list_tuple_orig,
                filter_dialog=create_filter_dialog(no_task_on_list=True,
                                                   read_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "read intent")


    @intent_handler(
        IntentBuilder("ReadListIntent").require("ReadListKeyword").require(
            LIST_PARAMETER).optionally(TEST_CONTEXT).build())
    def read_list_intent(self, message):
        try:
            k, m = self.regex_eval.eval(message, ['ReadList'])
            if not m:
                self.speak_dialog("IDontUnderstand")
                return

            list_name = m.groupdict()[LIST_PARAMETER]

            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, read list intent: list name " + list_name)
                return

            if not self.operation_init():
                return

            list_tuple = self.filter_tasks_on_list(
                create_list_tuple(list_name),
                filter_dialog=create_filter_dialog(
                    no_task_on_list=True,read_list=True),
                find_list_dialog=create_find_list_dialog(
                    using_another_list=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
                                 "read list intent")


    @intent_handler(
        IntentBuilder('DueIntent').require('DueKeyword').require(DUE_PARAMETER).
            require(LIST_CONTEXT).optionally(TEST_CONTEXT).build())
    def due_intent(self, message):
        try:
            list_tuple_orig = self.list_context_to_tuple(
                message.data.get(LIST_CONTEXT))

            k, m = self.regex_eval.eval(message, ['DueOnList', 'Due'])
            if not m:
                self.speak_dialog("IDontUnderstand")
                return

            if k == 'DueOnList':
                self.due_on_list_intent(message)
                return

            due = m.groupdict()[DUE_PARAMETER]

            self.remove_context(TASK_CONTEXT)

            if message.data.get(TEST_CONTEXT):
                self.speak(
                    "Test context, due intent: list name " +
                    list_tuple_orig.name + ", due " + due)
                return

            if not self.operation_init():
                return

            list_tuple = self.filter_tasks_on_list(
                list_tuple_orig,
                task_filter=create_task_filter(due=due),
                filter_dialog=create_filter_dialog(
                    no_task_on_list=True,
                    due_date=True,
                    read_list=True),
                task_dialog = create_task_dialog(due_time=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(),
                                message,
                                "due intent")


    @intent_handler(
        IntentBuilder('DueOnListIntent').require('DueKeyword').
            require(DUE_PARAMETER).require(LIST_PARAMETER).
            optionally(TEST_CONTEXT).build())
    def due_on_list_intent(self, message):
        try:
            k, m = self.regex_eval.eval(message, ['DueOnList'])
            if not m:
                self.speak_dialog("IDontUnderstand")
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

            list_tuple = self.filter_tasks_on_list(
                create_list_tuple(list_name),
                task_filter=create_task_filter(due=due),
                filter_dialog=create_filter_dialog(
                    no_task_on_list=True,
                    due_date=True,
                    read_list=True),
                find_list_dialog=create_find_list_dialog(
                    using_another_list=True),
                task_dialog=create_task_dialog(due_time=True))

            if list_tuple.id:
                self.set_list_context(list_tuple)

        except Exception:
            self.mail_exception(traceback.format_exc(), message,
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
            self.mail_exception(traceback.format_exc(), message,
                                 "undo intent")


    def stop(self):
        pass


def create_skill():
    return CowsLists()

"""
skill the-cows-lists
Copyright (C) 2018  Carsten Agerskov

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
TEST_CONTEXT = "_TestContext"
MAX_TASK_COMPLETE = 40

LIST_TUPLE = namedtuple('list', 'name, id, significance, due, filter, task_list')

TASK_LIST_TUPLE = namedtuple('task',
    'name, id, taskseries_id, significance, due, list_tuple')

FILTER_DIALOG = namedtuple('filter_dialog',
                           'no_task_on_list, due_date, read_list')

ADD_TASK_DIALOG = namedtuple('add_task_dialog', 'add_task_to_list')

FIND_LIST_DIALOG = namedtuple('find_list_dialog', 'using_another_list')

FIND_TASK_DIALOG = namedtuple('find_task_dialog', 'find_task_on_list, find_task_on_list_mismatch')


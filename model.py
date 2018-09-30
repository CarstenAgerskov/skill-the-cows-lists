"""
skill the-cows-lists
Copyright (C) 2017-2018  Carsten Agerskov

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

LIST_TUPLE = namedtuple('list', 'name, id, task_list')

# todo: rename to TASK_TUPLE
TASK_LIST_TUPLE = namedtuple(
    'task',
    'name, id, taskseries_id, significance, due, has_due_time, priority')

FILTER_DIALOG = namedtuple('filter_dialog',
                           'no_task_on_list, due_date, read_list')

ADD_TASK_DIALOG = namedtuple('add_task_dialog', 'add_task_to_list')

FIND_LIST_DIALOG = namedtuple('find_list_dialog', 'using_another_list')

FIND_TASK_DIALOG = namedtuple('find_task_dialog',
                              'find_task_on_list, find_task_on_list_mismatch')

TASK_DIALOG = namedtuple('task_dialog', 'due_date, due_time, priority')

TASK_FILTER = namedtuple('task_filter', 'status, due, priority')

def create_task_tuple(task_name, id=None, taskseries_id=None,
                      significance=None, due=None, has_due_time=None,
                      priority=None):
    return TASK_LIST_TUPLE(
                    name=task_name,
                    id=id,
                    taskseries_id=taskseries_id,
                    significance=significance,
                    due=due,
                    has_due_time=has_due_time,
                    priority=priority)

def create_list_tuple(name=None, id=None, task_list=None):
    return LIST_TUPLE(
        name=name,
        id=id,
        task_list=task_list)

def create_filter_dialog(no_task_on_list=None, due_date=None, read_list=None):
    return FILTER_DIALOG(no_task_on_list=no_task_on_list,
                         due_date=due_date,
                         read_list=read_list)

def create_add_task_dialog(add_task_to_list=None):
    return ADD_TASK_DIALOG(add_task_to_list=add_task_to_list)

def create_find_list_dialog(using_another_list=None):
    return FIND_LIST_DIALOG(using_another_list=using_another_list)

def create_find_task_dialog(find_task_on_list=None,
                            find_task_on_list_mismatch=None):
    return FIND_TASK_DIALOG(
        find_task_on_list=find_task_on_list,
        find_task_on_list_mismatch=find_task_on_list_mismatch)

def create_task_dialog(due_date=None, due_time=None, priority=None):
    return TASK_DIALOG(due_date=due_date,due_time=due_time, priority=priority)

def create_task_filter(status='incomplete', due=None, priority=None):
    return TASK_FILTER(status=status, due=due, priority=priority)

def flat_task_list(task_list):
    flat_task = []
    if 'list' not in task_list:
        return flat_task

    for taskseries in task_list['list']:
        if isinstance(taskseries['taskseries'], list):
            for t in taskseries['taskseries']:
                if isinstance(t['task'], list):
                    for x in t['task']:
                        flat_task.append(
                            create_task_tuple(
                                t['name'],
                                id=x['id'],
                                taskseries_id=t['id'],
                                due=x['due'],
                                has_due_time=x['has_due_time'],
                                priority=x['priority']))
                else:
                    flat_task.append(
                        create_task_tuple(
                            t['name'],
                            id=t['task']['id'],
                            taskseries_id=t['id'],
                            due=t['task']['due'],
                            has_due_time=t['task']['has_due_time'],
                            priority=t['task']['priority']))

        else:
            if isinstance(taskseries['taskseries']['task'], list):
                for x in taskseries['taskseries']['task']:
                    flat_task.append(
                        create_task_tuple(
                            taskseries['taskseries']['name'],
                            id=x['id'],
                            taskseries_id=taskseries['taskseries']['id'],
                            due=x['due'],
                            has_due_time=x['has_due_time'],
                            priority=x['priority']))
            else:
                flat_task.append(
                    create_task_tuple(
                        taskseries['taskseries']['name'],
                        id=taskseries['taskseries']['task']['id'],
                        taskseries_id=taskseries['taskseries']['id'],
                        due=taskseries['taskseries']['task']['due'],
                        has_due_time=taskseries['taskseries']['task']['has_due_time'],
                        priority=taskseries['taskseries']['task']['priority']))


    return flat_task

def cows_filter(task_filter):

    def add_filter(cows_filter, n, v):
        if v:
            if len(cows_filter) > 0:
                cows_filter = cows_filter + ' AND '
            return cows_filter + n + ':' + v
        return cows_filter

    cows_filter = add_filter('', 'status', task_filter.status)
    cows_filter = add_filter(cows_filter, 'due', task_filter.due)
    cows_filter = add_filter(cows_filter, 'priority', task_filter.priority)

    return cows_filter

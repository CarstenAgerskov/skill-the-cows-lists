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

from hashlib import md5
from urllib2 import urlopen
import urllib
import json
import ConfigParser
import os

__author__ = 'cagerskov'

RTM_URL = "https://api.rememberthemilk.com/services/rest/"
AUTH_URL = "https://www.rememberthemilk.com/services/auth/"

HOME_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = HOME_DIR + "/cowslist.cfg"

config = ConfigParser.ConfigParser()


class RtmRest:
    def __init__(self, default_param, secret):
        self.param = list([['format', 'json']])
        self.param.extend(default_param)
        self.secret = secret

    def add(self, param_list):
        self.param.extend(param_list)

    def get_param_string(self):
        self.param.sort()
        return '?' + ''.join(map((lambda x: x[0] + '=' + urllib.quote(x[1].encode('utf8')) + '&'), self.param)) \
               + 'api_sig=' + md5(self.secret + ''.join(map((lambda x: x[0] + x[1]), self.param))).hexdigest()

    def call(self):
        s = urlopen(RTM_URL + self.get_param_string())
        response = json.load(s)
        s.close()
        return response


class RtmParam:
    def __init__(self):
        pass

    @classmethod
    def reset_param(cls):
        cls.api_key = None
        cls.secret = None
        cls.auth_token = None
        cls.frob = None
        cls.timeline = None


def _get_basic_param():
    return list([['api_key', RtmParam.api_key]])


def _get_full_param():
    return _get_basic_param() + [['auth_token', RtmParam.auth_token]]


def _get_full_timeline_param():
    return _get_full_param() + [['timeline', RtmParam.timeline]]


def find_task_id(task_list, taskseries_id, task_id):
    if 'list' not in task_list:
        return None

    task_match = None
    taskseries_match = None
    for taskseries in task_list['list']:
        if not isinstance(taskseries['taskseries'], list):
            if taskseries['taskseries']['id'] == taskseries_id:
                taskseries_match = taskseries['taskseries']
        else:
            taskseries_match = filter(lambda x: x['id'] == taskseries_id, taskseries['taskseries'])

    if not taskseries_match:
        return None

    if not isinstance(taskseries_match, list):
        task_match = filter(lambda x: x['id'] == task_id, taskseries_match['task'])
    else:
        for task in taskseries_match:
            task_match = filter(lambda x: x['id'] == task_id, task['task'])

    return task_match


def get_token():
    if not RtmParam.auth_token:
        config.read(CONFIG_FILE)
        if config.has_option('auth', 'auth_token'):
            RtmParam.auth_token = config.get('auth', 'auth_token')


def get_new_token():
    r = RtmRest(_get_basic_param(), RtmParam.secret)
    r.add([["method", 'rtm.auth.getToken'],
           ["frob", RtmParam.frob]])
    auth_token = r.call()

    if auth_token['rsp']['stat'] == 'fail':
        return auth_token['rsp']['err']['msg'], auth_token['rsp']['err']['code']

    if not config.has_section('auth'):
        config.add_section('auth')

    config.set('auth', 'auth_token', auth_token['rsp']['auth']['token'])
    with open(CONFIG_FILE, 'wb') as configfile:
        config.write(configfile)

    RtmParam.auth_token = auth_token['rsp']['auth']['token']

    return None, None


def get_timeline():
    r = RtmRest(_get_full_param(), RtmParam.secret)
    r.add([['method', 'rtm.timelines.create']])
    timeline_result = r.call()

    if timeline_result['rsp']['stat'] == 'fail':
        return timeline_result['rsp']['err']['msg'], timeline_result['rsp']['err']['code']

    RtmParam.timeline = timeline_result['rsp']['timeline']
    return None, None


def verify_token_validity():
    r = RtmRest(_get_full_param(), RtmParam.secret)
    r.add([["method", 'rtm.auth.checkToken']])
    check_token = r.call()

    if check_token['rsp']['stat'] == 'fail':
        return check_token['rsp']['err']['msg'], check_token['rsp']['err']['code']

    return None, None


def get_frob():
    r = RtmRest(_get_basic_param(), RtmParam.secret)
    r.add([["method", 'rtm.auth.getFrob']])
    frob = r.call()

    if frob['rsp']['stat'] == 'fail':
        return frob['rsp']['err']['msg'], frob['rsp']['err']['code']

    RtmParam.frob = str(frob['rsp']['frob'])

    return None, None


def get_auth_url():
    return AUTH_URL + '?api_key=' + RtmParam.api_key + '&perms=delete&frob=' + RtmParam.frob \
           + '&api_sig=' + md5(RtmParam.secret + 'api_key' + RtmParam.api_key + 'frob'
                               + RtmParam.frob + 'permsdelete').hexdigest()


def get_list():
    r = RtmRest(_get_full_param(), RtmParam.secret)
    r.add([["method", "rtm.lists.getList"]])
    list_result = r.call()

    if list_result['rsp']['stat'] == 'fail':
        return None, list_result['rsp']['err']['msg'], list_result['rsp']['err']['code']

    return list_result['rsp']['lists']['list'], None, None


def add_task(item_name, list_id):
    r = RtmRest(_get_full_timeline_param(), RtmParam.secret)
    r.add([['method', 'rtm.tasks.add'],
           ['list_id', list_id],
           ['name', item_name],
           ['parse', '1']])
    insert_result = r.call()

    if insert_result['rsp']['stat'] == 'fail':
        return None, None, insert_result['rsp']['err']['msg'], insert_result['rsp']['err']['code']

    return insert_result['rsp']['list']['taskseries']['id'], \
           insert_result['rsp']['list']['taskseries']['task']['id'], None, None


def delete_task(task_id, taskseries_id, list_id):
    r = RtmRest(_get_full_timeline_param(), RtmParam.secret)
    r.add([['method', 'rtm.tasks.delete'],
           ['task_id', task_id],
           ['taskseries_id', taskseries_id],
           ['list_id', list_id]])
    delete_result = r.call()

    if delete_result['rsp']['stat'] == 'fail':
        return None, delete_result['rsp']['err']['msg'], delete_result['rsp']['err']['code']

    return delete_result['rsp']['transaction']['id'], None, None


def list_task(list_filter, list_id):
    # This call may return a huge amount of data, be sure to use filter!
    r = RtmRest(_get_full_timeline_param(), RtmParam.secret)
    r.add([['method', 'rtm.tasks.getList'], ['filter', list_filter]])
    if list_id:
        r.add([['list_id', list_id]])
    list_result = r.call()

    if list_result['rsp']['stat'] == 'fail':
        return None, list_result['rsp']['err']['msg'], list_result['rsp']['err']['code']

    return list_result['rsp']['tasks'], None, None


def roll_back(transaction_id):
    r = RtmRest(_get_full_timeline_param(), RtmParam.secret)
    r.add([['method', 'rtm.transactions.undo'],
           ['transaction_id', transaction_id]])
    roll_back_result = r.call()

    if roll_back_result['rsp']['stat'] == 'fail':
        return roll_back_result['rsp']['err']['msg'], roll_back_result['rsp']['err']['code']

    return None, None


def complete_task(task_id, taskseries_id, list_id):
    r = RtmRest(_get_full_timeline_param(), RtmParam.secret)
    r.add([['method', 'rtm.tasks.complete'],
           ['task_id', task_id],
           ['taskseries_id', taskseries_id],
           ['list_id', list_id]])
    complete_result = r.call()

    if complete_result['rsp']['stat'] == 'fail':
        return None, complete_result['rsp']['err']['msg'], complete_result['rsp']['err']['code']

    return complete_result['rsp']['transaction']['id'], None, None

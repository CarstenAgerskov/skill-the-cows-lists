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

from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from hashlib import md5
from urllib2 import urlopen
import urllib
import json
import sys
import ConfigParser
import os

__author__ = 'cagerskov'

RTM_URL = "https://api.rememberthemilk.com/services/rest/"
AUTH_URL = "https://www.rememberthemilk.com/services/auth/"

ITEM_PARAMETER = "itemName"
LIST_PARAMETER = "listName"
ERROR_TEXT_PARAMETER = "errorText"
ERROR_CODE_PARAMETER = "errorCode"
FUNCTION_NAME_PARAMETER = "functionName"
LINE_PARAMETER = "lineNumber"

HOME_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = HOME_DIR + "/cowslist.cfg"
LOGGER = getLogger(__name__)

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
        self.api_key = None
        self.secret = None
        self.auth_token = None
        self.frob = None

    def get_basic_param(self):
        return list([['api_key', self.api_key]])

    def get_full_param(self):
        return self.get_basic_param() + [['auth_token', self.auth_token]]


class CowsLists(MycroftSkill):
    def __init__(self):
        super(CowsLists, self).__init__(name="TheCowsLists")
        self.rtmParam = RtmParam()

    def initialize(self):
        self.load_data_files(dirname(__file__))

        self.register_intent(IntentBuilder("AddItemToListIntent").require("AddItemToList").require(
            ITEM_PARAMETER).require(LIST_PARAMETER).build(), self.add_item_to_list_intent)

        self.register_intent(IntentBuilder("GetTokenIntent").require("GetToken").build(), self.get_token_intent)

        self.register_intent(IntentBuilder("AuthenticateIntent").require("Authenticate").build(),
                             self.authenticate_intent)

        self.settings.load_skill_settings()

    def get_config(self):
        try:
            try:
                if not self.rtmParam.api_key:
                    self.rtmParam.api_key = self.config.get('api_key')
            except AttributeError:
                self.rtmParam.api_key = self.settings.get('api_key')

            try:
                if not hasattr(self, 'secret'):
                    self.rtmParam.secret = self.config.get('secret')
            except AttributeError:
                self.rtmParam.secret = self.settings.get('secret')

            if not self.rtmParam.api_key or not self.rtmParam.secret:
                raise Exception("api key or secret not configured")

        except Exception as e:
            self.speak_dialog('ConfigNotFound')
            raise Exception('Configuration not found, error {0}'.format(e))

    def get_token(self):
        if not self.rtmParam.auth_token:
            config.read(CONFIG_FILE)
            if config.has_option('auth', 'auth_token'):
                self.rtmParam.auth_token = config.get('auth', 'auth_token')

    def verify_token_validity(self):
        if not self.rtmParam.auth_token:
            return False

        r = RtmRest(self.rtmParam.get_full_param(), self.rtmParam.secret)
        r.add([["method", 'rtm.auth.checkToken']])
        check_token = r.call()

        if check_token['rsp']['stat'] == 'fail' and check_token['rsp']['err']['code'] != '98':
            self.speak_dialog('RestResponseError',
                              {ERROR_TEXT_PARAMETER: check_token['rsp']['err']['msg'],
                               ERROR_CODE_PARAMETER: check_token['rsp']['err']['code']})
            raise Exception('Error verifying token:' + check_token['rsp']['err']['msg'])

        if check_token['rsp']['stat'] == 'fail':
            return False

        return True

    def authenticate_intent(self):
        try:
            self.get_config()
            self.get_token()

            if self.verify_token_validity():
                self.speak_dialog("TokenValid")
                return

            r = RtmRest(self.rtmParam.get_basic_param(), self.rtmParam.secret)
            r.add([["method", 'rtm.auth.getFrob']])
            frob = r.call()

            if frob['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: frob['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: frob['rsp']['err']['code']})
                return

            self.rtmParam.frob = str(frob['rsp']['frob'])

            auth_url = AUTH_URL + '?api_key=' + self.rtmParam.api_key + '&perms=delete&frob=' + self.rtmParam.frob \
                       + '&api_sig=' + md5(self.rtmParam.secret + 'api_key' + self.rtmParam.api_key + 'frob'
                                           + self.rtmParam.frob + 'permsdelete').hexdigest()

            mail_body = "Use the link below to authenticate Mycroft with remember the milk.<br>" \
                        + "After authentication, say: Hey Mycroft, get a token for remember the milk<br><br>" \
                        + '<a href = "' + auth_url + '">' + auth_url + '</a>'

            self.send_email("Authentication", mail_body)
            self.speak_dialog("EmailSent")

        except Exception as e:
            LOGGER.exception("Error in authenticate_intent: {0}".format(e))
            self.speak_dialog('GeneralError',
                              {FUNCTION_NAME_PARAMETER: "authenticate intent",
                               LINE_PARAMETER: format(sys.exc_info()[-1].tb_lineno)})

    def get_token_intent(self):
        try:
            self.get_config()
            self.get_token()

            if self.verify_token_validity():
                self.speak_dialog("TokenValid")
                return

            if not self.rtmParam.frob:
                self.speak_dialog('AuthenticateBeforeToken')
                return

            r = RtmRest(self.rtmParam.get_basic_param(), self.rtmParam.secret)
            r.add([["method", 'rtm.auth.getToken'],
                   ["frob", self.rtmParam.frob]])
            auth_token = r.call()

            if auth_token['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: auth_token['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: auth_token['rsp']['err']['code']})
                return

            if not config.has_section('auth'):
                config.add_section('auth')

            config.set('auth', 'auth_token', auth_token['rsp']['auth']['token'])
            with open(CONFIG_FILE, 'wb') as configfile:
                config.write(configfile)

            self.rtmParam.auth_token = auth_token['rsp']['auth']['token']

            self.speak_dialog("GotToken")

        except Exception as e:
            LOGGER.exception("Error in get_token_intent: {0}".format(e))
            self.speak_dialog('GeneralError',
                              {FUNCTION_NAME_PARAMETER: "get token intent",
                               LINE_PARAMETER: format(sys.exc_info()[-1].tb_lineno)})

    def add_item_to_list_intent(self, message):
        try:
            self.get_config()
            self.get_token()

            if not self.rtmParam.auth_token and self.rtmParam.frob:
                self.speak_dialog("InAuthentication")
                return

            if not self.rtmParam.auth_token:
                self.speak_dialog("NotAuthenticated")
                return

            r = RtmRest(self.rtmParam.get_full_param(), self.rtmParam.secret)
            r.add([["method", "rtm.lists.getList"]])
            list_result = r.call()

            if list_result['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: list_result['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: list_result['rsp']['err']['code']})
                return

            item_name = message.data.get(ITEM_PARAMETER)
            list_name = message.data.get(LIST_PARAMETER)

            try:
                list_id = filter(lambda x: x['name'].lower() == list_name, list_result['rsp']['lists']['list'])[0]['id']
            except IndexError:
                self.speak_dialog('ListNotFound', {LIST_PARAMETER: list_name})
                return

            r = RtmRest(self.rtmParam.get_full_param(), self.rtmParam.secret)
            r.add([['method', 'rtm.timelines.create']])
            timeline_result = r.call()

            if timeline_result['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: timeline_result['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: timeline_result['rsp']['err']['code']})
                return

            r = RtmRest(self.rtmParam.get_full_param(), self.rtmParam.secret)
            r.add([['method', 'rtm.tasks.add'],
                   ['list_id', list_id],
                   ['name', item_name],
                   ['parse', '1'],
                   ['timeline', timeline_result['rsp']['timeline']]])
            insert_result = r.call()

            if insert_result['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: insert_result['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: insert_result['rsp']['err']['code']})
                return

            self.speak_dialog('AddItemToList', {ITEM_PARAMETER: item_name, LIST_PARAMETER: list_name})

        except Exception as e:
            LOGGER.exception("Error in add_item_to_list_intent: {0}".format(e))
            self.speak_dialog('GeneralError',
                              {FUNCTION_NAME_PARAMETER: "add item to list intent",
                               LINE_PARAMETER: format(sys.exc_info()[-1].tb_lineno)})

    def stop(self):
        pass


def create_skill():
    return CowsLists()

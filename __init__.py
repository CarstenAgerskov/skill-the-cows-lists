'''
skill remember-the-milk
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
'''

from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from hashlib import md5
import urllib2
import urllib
import json

__author__ = 'cagerskov'

RTM_URL = "https://api.rememberthemilk.com/services/rest/"
AUTH_URL = "https://www.rememberthemilk.com/services/auth/"

ITEM_PARAMETER = "itemName"
LIST_PARAMETER = "listName"
ERROR_TEXT_PARAMETER = "errorText"
ERROR_CODE_PARAMETER = "errorCode"

LOGGER = getLogger(__name__)

class RtmRest:
    def __init__(self,defaultParam,secret):
        self.param = list([['format', 'json']])
        self.param.extend(defaultParam)
        self.secret = secret

    def add(self,paramList):
        self.param.extend(paramList)

    def getParamString(self):
        self.param.sort()
        self.paramString= '?' + ''.join(map((lambda x: x[0]+ '=' + urllib.quote(x[1].encode('utf8')) + '&'), self.param)) \
                          + 'api_sig=' + md5(self.secret + ''.join(map((lambda x: x[0]+x[1]), self.param))).hexdigest()
        return self.paramString

    def call(self):
        s = urllib2.urlopen(RTM_URL + self.getParamString())
        response = json.load(s)
        s.close()
        return response

class RtmParam:
    def __init__(self):
        self.api_key = None
        self.secret = None
        self.auth_token = None
        self.frob = None

    def getBasicParam(self):
        return list([['api_key', self.api_key]])

    def getFullParam(self):
        return self.getBasicParam() + [['auth_token', self.auth_token]]


class CowsLists(MycroftSkill):
    def __init__(self):
        super(CowsLists, self).__init__(name="TheCowsLists")
        self.rtmParam = RtmParam()

    def initialize(self):
        self.load_data_files(dirname(__file__))

        addItemToListIntent = IntentBuilder("AddItemToListIntent").\
            require("AddItemToList").require(ITEM_PARAMETER).require(LIST_PARAMETER).build()
        self.register_intent(addItemToListIntent, self.add_item_to_list_intent)

        getTokenIntent = IntentBuilder("GetTokenIntent").\
            require("GetToken").build()
        self.register_intent(getTokenIntent, self.get_token_intent)

        authenticateIntent = IntentBuilder("AuthenticateIntent").\
            require("Authenticate").build()
        self.register_intent(authenticateIntent, self.authenticate_intent)

        self.settings.load_skill_settings()

    def get_config(self):
        try:
            try:
                if not self.rtmParam.api_key:
                    self.rtmParam.api_key = self.config.get('api_key')
            except AttributeError:
                self.rtmParam.api_key = str(self.settings.get('api_key', None))

            try:
                if not hasattr(self, 'secret'):
                    self.rtmParam.secret = self.config.get('secret')
            except AttributeError:
                self.rtmParam.secret = str(self.settings.get('secret', None))

            if not self.rtmParam.api_key or not self.rtmParam.secret:
                raise Exception("api key or secret not configured")

        except Exception as e:
            self.speak_dialog('ConfigNotFound')
            raise Exception('Configuration not found, error {0}'.format(e))

    def get_token(self):
        try:
            if not self.rtmParam.auth_token:
                self.rtmParam.auth_token = str(self.settings.get('auth_token', None))
        except AttributeError:
            pass

    def verify_token_validity(self):
        if not self.rtmParam.auth_token:
            return False

        r = RtmRest(self.rtmParam.getFullParam(), self.rtmParam.secret)
        r.add([["method", 'rtm.auth.checkToken']])
        check_token = r.call()

        if check_token['rsp']['stat'] == 'fail' and check_token['rsp']['err']['code'] != '98':
            self.speak_dialog('RestResponseError',
                              { ERROR_TEXT_PARAMETER: check_token['rsp']['err']['msg'],
                                ERROR_CODE_PARAMETER: check_token['rsp']['err']['code']})
            raise Exception('Error verifying token:' + check_token)

        if check_token['rsp']['stat'] == 'fail':
            return False

        return True

    def authenticate_intent(self, message):
        try:
            self.get_config()
            self.get_token()

            if self.verify_token_validity():
                self.speak_dialog("TokenValid")
                return

            r = RtmRest(self.rtmParam.getBasicParam(), self.rtmParam.secret)
            r.add([["method", 'rtm.auth.getFrob']])
            frob = r.call()

            if frob['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: frob['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: frob['rsp']['err']['code']})
                raise Exception('Could not get frob, response was ' + frob)

            self.rtmParam.frob = str(frob['rsp']['frob'])

            authUrl = AUTH_URL + '?api_key=' + self.rtmParam.api_key + '&perms=delete&frob=' + self.rtmParam.frob \
                      + '&api_sig=' + md5(self.rtmParam.secret
                                         + 'api_key' + self.rtmParam.api_key
                                         + 'frob' + self.rtmParam.frob
                                         + 'permsdelete').hexdigest()


            mailBody =  "Use the link below to authenticate Mycroft with remember the milk.<br>" + \
                        "After authentication, say: Hey Mycroft, get a token for remember the milk<br><br>" + \
                        '<a href = "' + authUrl + '">' + authUrl + '</a>'

            self.send_email("Authentication",mailBody)
            self.speak_dialog("EmailSent")

        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def get_token_intent(self, message):
        try:
            self.get_config()
            self.get_token()

            if self.verify_token_validity():
                self.speak_dialog("TokenValid")
                return

            if not self.rtmParam.frob:
                self.speak_dialog('AuthenticateBeforeToken')
                return

            r = RtmRest(self.rtmParam.getBasicParam(), self.rtmParam.secret)
            r.add([["method", 'rtm.auth.getToken'],
                   ["frob", self.rtmParam.frob]])
            auth_token = r.call()

            if auth_token['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: auth_token['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: auth_token['rsp']['err']['code']})
                raise Exception('Could not get auth token, response was ' + auth_token)


            self.settings.__setitem__("auth_token",auth_token['rsp']['auth']['token'])
            self.speak_dialog("GotToken")

        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def add_item_to_list_intent(self, message):
        try:
            self.get_config()
            self.get_token()

            if not self.rtmParam.auth_token:
                self.speak_dialog("NotAuthenticated")
                return

            item = message.data.get(ITEM_PARAMETER)
            list = message.data.get(LIST_PARAMETER)

            r = RtmRest(self.rtmParam.getFullParam(), self.rtmParam.secret)
            r.add([["method", "rtm.lists.getList"]])
            listResult = r.call()

            if listResult['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: listResult['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: listResult['rsp']['err']['code']})
                raise Exception('Error finding lists:' + listResult)

            try:
                listId = filter(lambda x: x['name'].lower() == list, listResult['rsp']['lists']['list'])[0]['id']
            except IndexError:
                self.speak_dialog('ListNotFound', {LIST_PARAMETER: list })
                return

            r = RtmRest(self.rtmParam.getFullParam(), self.rtmParam.secret)
            r.add([['method', 'rtm.timelines.create']])
            timelineResult = r.call()

            if timelineResult['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: timelineResult['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: timelineResult['rsp']['err']['code']})
                raise Exception('Error getting timeline:' + timelineResult)

            r = RtmRest(self.rtmParam.getFullParam(), self.rtmParam.secret)
            r.add([['method', 'rtm.tasks.add'],
                   ['list_id', listId],
                   ['name', item],
                   ['parse', '1'],
                   ['timeline', timelineResult['rsp']['timeline']]])
            insertResult = r.call()

            if insertResult['rsp']['stat'] == 'fail':
                self.speak_dialog('RestResponseError',
                                  {ERROR_TEXT_PARAMETER: insertResult['rsp']['err']['msg'],
                                   ERROR_CODE_PARAMETER: insertResult['rsp']['err']['code']})
                raise Exception('Error adding item to list:' + insertResult)

            self.speak_dialog('AddItemToList', {ITEM_PARAMETER : item , LIST_PARAMETER : list })

        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def stop(self):
        pass

def create_skill():
    return CowsLists()

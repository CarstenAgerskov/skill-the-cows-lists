# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


# Visit https://docs.mycroft.ai/skill.creation for more detailed information
# on the structure of this skill and its containing folder, as well as
# instructions for designing your own skill based on this template.

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

ITEM_PARAMETER = "itemName"
LIST_PARAMETER = "listName"
ERROR_TEXT_PARAMETER = "errorText"
ERROR_CODE_PARAMETER = "errorCode"

LOGGER = getLogger(__name__)

class restParameters:
    def __init__(self,defaultParam,secret):
        self.param = list()
        self.param.extend(defaultParam)
        self.secret = secret

    def add(self,paramList):
        self.param.extend(paramList)

    def getParamString(self):
        self.param.sort()
        self.paramString= '?' + ''.join(map((lambda x: x[0]+ '=' + urllib.quote(x[1].encode('utf8')) + '&'), self.param)) \
                          + 'api_sig=' + md5(self.secret + ''.join(map((lambda x: x[0]+x[1]), self.param))).hexdigest()
        return self.paramString

class RtmSkill(MycroftSkill):

    def __init__(self):
        super(RtmSkill, self).__init__(name="RtmSkill")
        self.defaultParam = list([
            ['api_key', self.config.get('api_key')],
            ['auth_token', self.config.get('auth_token')],
            ['format', 'json']])
        self.secret = self.config.get('secret')

    def initialize(self):
        self.load_data_files(dirname(__file__))

        addItemToListIntent = IntentBuilder("AddItemToListIntent").\
            require("AddItemToList").require(ITEM_PARAMETER).require(LIST_PARAMETER).build()
        self.register_intent(addItemToListIntent, self.add_item_to_list_intent)


    def add_item_to_list_intent(self, message):
        try:
            item = message.data.get(ITEM_PARAMETER)
            list = message.data.get(LIST_PARAMETER)

            r = restParameters(self.defaultParam, self.secret)
            r.add([["method", "rtm.lists.getList"]])

            s = urllib2.urlopen(RTM_URL + r.getParamString())
            listResult = json.load(s)
            s.close()

            if listResult['rsp']['stat'] == 'fail':
                self.speak_dialog('GetListError', {LIST_PARAMETER: list.lower(), ERROR_TEXT_PARAMETER: listResult['rsp']['err']['msg'], ERROR_CODE_PARAMETER: listResult['rsp']['err']['code']})
                raise Exception('Error finding lists:' + listResult)

            try:
                listId = filter(lambda x: x['name'].lower() == list, listResult['rsp']['lists']['list'])[0]['id']
            except IndexError:
                self.speak_dialog('ListNotFound', {LIST_PARAMETER: list })
                raise Exception('List ' + list + ' not found in ' + listResult)

            r = restParameters(self.defaultParam, self.secret)
            r.add([['method', 'rtm.timelines.create']])

            s = urllib2.urlopen(RTM_URL + r.getParamString())
            timelineResult = json.load(s)
            s.close()

            if timelineResult['rsp']['stat'] == 'fail':
                self.speak_dialog('GetTimelineError', {ERROR_TEXT_PARAMETER: timelineResult['rsp']['err']['msg'], ERROR_CODE_PARAMETER: timelineResult['rsp']['err']['code']})
                raise Exception('Error getting timeline:' + timelineResult)

            r = restParameters(self.defaultParam, self.secret)
            r.add([['method', 'rtm.tasks.add'],
                   ['list_id', listId],
                   ['name', item],
                   ['parse', '1'],
                   ['timeline', timelineResult['rsp']['timeline']]])

            s = urllib2.urlopen(RTM_URL + r.getParamString())
            insertResult = json.load(s)
            s.close()

            if insertResult['rsp']['stat'] == 'fail':
                self.speak_dialog('AddItemToListError', {ITEM_PARAMETER: item, LIST_PARAMETER: list ,ERROR_TEXT_PARAMETER: insertResult['rsp']['err']['msg'], ERROR_CODE_PARAMETER: insertResult['rsp']['err']['code']})
                raise Exception('Error adding item to list:' + insertResult)

            self.speak_dialog('AddItemToList', {ITEM_PARAMETER : item , LIST_PARAMETER : list })

        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def stop(self):
        pass

def create_skill():
    return RtmSkill()

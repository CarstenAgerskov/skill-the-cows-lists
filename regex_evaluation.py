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

import json
import re


class RegexEvaluation:
    def __init__(self, regex_file):
        self.local_regex = {}
        with open(regex_file, 'r') as local_regex_file:
            local_regex = json.loads(local_regex_file.read())

        for key, value in local_regex.items():
            self.local_regex.update({key: [re.compile(v) for v in value]})

    def eval(self, message, regex_key):
        m = None
        k = None
        for k in regex_key:
            for r in self.local_regex[k]:
                m = r.match(message.data.get('utterance'))
                if m:
                    break
            if m:
                break

        return k, m

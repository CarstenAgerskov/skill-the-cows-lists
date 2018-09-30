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

import pytz
from datetime import datetime
from dateutil.parser import parse

class TimeConversion:
    def __init__(self, tz_str):
        try:
            self.tz = pytz.timezone(tz_str)
        except:
            self.tz = pytz.utc

    def naive_utc_to_local(self, dt):
        dt = dt if type(dt) is datetime else parse(dt)
        return dt.replace(tzinfo=pytz.utc).astimezone(self.tz)

    def naive_local_to_local(self, dt):
        return dt.replace(tzinfo=self.tz)

    def local_to_utc(self, dt):
        return dt.astimezone(pytz.utc)


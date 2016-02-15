#!/usr/bin/python
###############################################################################
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###############################################################################
#
# Prints a list of users in a JIRA JSON dump. This only prints the list of
# users in the "users" section at the top of the JSON structure, which should
# be a superset of all users with assignments, comments, history, etc. in the
# dump.
#
###############################################################################
import json
import sys

def format_user_profile_link(user, url):
    return " ".join([user["name"], user["email"], user["fullname"], "%s/secure/ViewProfile.jspa?name=%s" % (url, user["name"])])

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print "Usage: %s jira-dump.json" % sys.argv[0]
        sys.exit(1)

    files = sys.argv[1:]

    print

    for fname in files:
        with open(fname, "r") as f:
            data = json.load(f)
            for user in data["users"]:
                print format_user_profile_link(user, "https://issues.apache.org/jira")
    print
    sys.exit(0)

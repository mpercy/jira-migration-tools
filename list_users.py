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

def issue_has_user_activity(user, issue):
    """ A user usually can be a reporter/assignee/watcher/author of comment
    or author of a jira activity like transition. Returns True if the user
    'user' is in any of the above lists. False otherwise"""
    # Is reporter or assignee of the issue?
    if issue["reporter"] == user or ("assignee" in issue.keys() and issue["assignee"] == user):
        return True
    # Is the user a watcher of the issue?
#    if "watchers" in issue.keys() and user in issue["watchers"]:
#        return True
    # Has the user ever commented on this issue?
    if "comments" in issue.keys():
        for comment in issue["comments"]:
            if comment["author"] == user:
                return True
    # Did the user involve in any other activity on the issue?
    if "history" in issue.keys():
        for activity in issue["history"]:
            if activity["author"] == user:
                return True
    return False

def print_users_with_no_activity(filename, users_with_no_activity):
     with open(filename, "r") as f:
         data = json.load(f)
         for user in data["users"]:
             user_has_activity = False
             for issue in data["projects"][0]["issues"]:
                 if issue_has_user_activity(user["name"], issue):
                     user_has_activity = True
                     break
             if not user_has_activity and user["name"] not in users_with_no_activity:
                 print user["name"]
                 users_with_no_activity.append(user["name"])
     return users_with_no_activity

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print "Usage: %s jira-dump.json" % sys.argv[0]
        sys.exit(1)

    files = sys.argv[1:]

    users_with_no_activity = []
    for fname in files:
        users_with_no_activity = print_users_with_no_activity(fname, users_with_no_activity)
    sys.exit(1);

    unique_users = []

    for fname in files:
        with open(fname, "r") as f:
            data = json.load(f)
            for user in data["users"]:
                if user["name"] in unique_users or user["name"] in users_with_no_activity : continue
                try:
                    print format_user_profile_link(user, "https://issues.apache.org/jira")
                    unique_users.append(user["name"])
                except UnicodeEncodeError:
                    pass
    print
    sys.exit(0)

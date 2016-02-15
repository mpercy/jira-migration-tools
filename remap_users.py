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
# Script to munge a JSON JIRA export to perform user mappings and remove
# "hidden" JIRAs. Hidden JIRAs are created by setting "Security Level" to
# "Hidden" on the issue in JIRA.
#
###############################################################################
import json
import requests
import sys
import time

if len(sys.argv) != 4:
    print "Usage: %s user_mappings.tsv users_to_remove.lst jira.json > out.json" % sys.argv[0]
    sys.exit(1)

user_mappings_filename = sys.argv[1]
users_to_remove_filename = sys.argv[2]
filename = sys.argv[3]

users_to_exclude = [line.strip() for line in open(users_to_remove_filename, "r")]

user_mappings = {}
with open(user_mappings_filename, "r") as umf:
    for line in umf:
        line = line.strip()
        if line.startswith("#") or line == "":
            continue
        old, new = line.split("\t", 1)
        # No tab means no change to the username.
        if new is None:
            new = old
        user_mappings[old] = new

# Fields with exact username matches.
exact_username_fields = frozenset(["reporter", "name", "assignee", "author", "oldValue",
                                   "newValue", "voters", "watchers", "lead"])
# Fields with mentions.
mention_fields = frozenset(["description", "body"])

# Replace usernames in shallow fields in the given hash struct.
def replace_usernames(data):
    for field in exact_username_fields:
        if field in data:
            if isinstance(data[field], list):
                # Support watchers.
                l = data[field]
                for i in range(0, len(l)):
                    if l[i] in user_mappings:
                        l[i] = user_mappings[l[i]]
            else:
                if data[field] in user_mappings:
                    data[field] = user_mappings[data[field]]
    for field in mention_fields:
        if field in data:
            for old_name in user_mappings:
                old_mention = "[~%s]" % (old_name,)
                new_mention = "[~%s]" % (user_mappings[old_name],)
                data[field] = data[field].replace(old_mention, new_mention)

if __name__ == "__main__":
    with open(filename, "r") as f:
        data = json.load(f)
        for proj in data["projects"]:
            replace_usernames(proj)
            proj_prefix = None
            new_issues = []
            for issue in proj["issues"]:
                replace_usernames(issue)

                hidden = False
                for h in issue["history"]:
                    replace_usernames(h)
                    if "items" in h:
                        for item in h["items"]:
                            replace_usernames(item)
                            if "field" in item and "newValue" in item and "newDisplayValue" in item:
                                # Check if the issue is "hidden". If so, we skip it.
                                if item["field"] == "security" and item["newDisplayValue"] == "Hidden":
                                    hidden = True
                for c in issue["comments"]:
                    replace_usernames(c)

                if hidden:
                    # Simply skip this one.
                    continue
                # The "normal" case.
                new_issues.append(issue)
            proj["issues"] = new_issues

        # Remove users we don't want included in the migration.
        new_users = []
        for user in data["users"]:
            if user["name"] in users_to_exclude:
                continue
            replace_usernames(user)
            new_users.append(user)
        data["users"] = new_users

        print json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

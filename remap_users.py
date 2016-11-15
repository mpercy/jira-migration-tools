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
# Munge a JSON JIRA export to perform username mappings.
#
###############################################################################
import json
import requests
import sys
import time
from list_users import format_user_profile_link

# Fields with exact username matches.
EXACT_USERNAME_FIELDS = frozenset(["reporter", "name", "assignee", "author", "oldValue",
                                   "newValue", "voters", "watchers", "lead"])
# Fields with mentions.
MENTION_FIELDS = frozenset(["description", "body"])

def replace_usernames(data):
    """ Replace usernames in shallow fields in the given hash struct. """
    for field in EXACT_USERNAME_FIELDS:
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
    for field in MENTION_FIELDS:
        if field in data:
            for old_name in user_mappings:
                old_mention = "[~%s]" % (old_name,)
                new_mention = "[~%s]" % (user_mappings[old_name],)
                data[field] = data[field].replace(old_mention, new_mention)

def get_user_mappings(user_mappings_filename):
    """
    Returns a dict of old-username to new-username based on parsing the given
    user mapping file.
    """
    user_mappings = {}
    with open(user_mappings_filename, "r") as umf:
        for line in umf:
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            fields = line.split("=", 1)
            if len(fields) == 2:
                old, new = fields
            else:
                # No tab means no change to the username.
                old = new = fields[0]
            user_mappings[old] = new
    return user_mappings

if __name__ == "__main__":

    if len(sys.argv) != 5:
        sys.stderr.write("Usage: %s user_mappings.tsv users_to_exclude.lst dest_jira_url jira.json > out.json\n" % sys.argv[0])
        sys.stderr.write("Example: %s user_mappings.tsv users_to_exclude.lst https://issues.apache.org/jira infile.json > outfile.json\n" % sys.argv[0])
        sys.exit(1)

    user_mappings_filename = sys.argv[1]
    users_to_exclude_filename = sys.argv[2]
    dest_jira_url = sys.argv[3]
    json_filename = sys.argv[4]

    user_mappings = get_user_mappings(user_mappings_filename)
    users_to_exclude = frozenset([line.strip() for line in open(users_to_exclude_filename, "r")])

    with open(json_filename, "r") as f:
        data = json.load(f)

        # Validate that we have accounted for all users in our mappings.
        found_all_users = True
        for user in data["users"]:
            if user["name"] not in users_to_exclude and user["name"] not in user_mappings:
                if found_all_users:
                    found_all_users = False
                    sys.stderr.write("ERROR: The following users were not found in any mapping / exclusion files:\n")
                    sys.stderr.write("%s\n" % ('='*80,))
                sys.stderr.write("%s\n" % (format_user_profile_link(user, dest_jira_url),))
        if not found_all_users:
            sys.exit(1)

        # Remove users we don't want included in the migration.
        new_users = []
        for user in data["users"]:
            if user["name"] in users_to_exclude:
                continue
            replace_usernames(user)
            new_users.append(user)
        data["users"] = new_users

        # Replace usernames throughout the project.
        for proj in data["projects"]:
            replace_usernames(proj)
            proj_prefix = None
            new_issues = []
            for issue in proj["issues"]:
                replace_usernames(issue)

                hidden = False
                if "history" in issue.keys():
                    for h in issue["history"]:
                        replace_usernames(h)
                        if "items" in h:
                            for item in h["items"]:
                                replace_usernames(item)
                                if "field" in item and "newValue" in item and "newDisplayValue" in item:
                                    # Check if the issue is "hidden". If so, we skip it.
                                    if item["field"] == "security" and item["newDisplayValue"] == "Hidden":
                                        hidden = True
                if "comments" in issue.keys():
                    for c in issue["comments"]:
                        replace_usernames(c)

                if hidden:
                    # Simply skip this one.
                    continue
                # The "normal" case.
                new_issues.append(issue)
            proj["issues"] = new_issues

            new_components = []
            for component in proj["components"]:
                replace_usernames(component)
                new_components.append(component);
            proj["components"] = new_components

        print json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '))

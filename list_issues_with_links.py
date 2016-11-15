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
# Script to add back fields that are not automatically exported by JIRA export.
# Also performs mappings between resolutions and versions for history reasons.
# This uses the REST API for both the old and new servers to figure out the
# version mappings and to get the latest values for "component", "resolution",
# and "fixVersions".
#
###############################################################################
import json
import requests
import sys
import time
from collections import defaultdict
from remap_users import get_user_mappings

def get_version_map(src_jira_url, dest_jira_url, project_key):
    version_api_path = "/rest/api/2/project/%s/versions" % (project_key,)
    version_name_map = defaultdict(list)
    for root in (src_jira_url, dest_jira_url):
        url = root + version_api_path
        r = requests.get(url);
        versions = r.json()
        print versions
        for v in versions:
            version_name_map[v['name']].append(v['id'])
    mapping = {}
    for name in version_name_map:
        l = version_name_map[name]
        if len(l) != 2:
            sys.stderr.write("WARN: Version with name '%s' does not appear in both instances\n" % (name,))
            continue
        old, new = l
        mapping[old] = new
    return mapping

def get_field_map(src_jira_url):
    """ Return map of available JIRA fields, keyed by field id. """
    field_api_path = "/rest/api/2/field"
    field_name_map = {}
    url = src_jira_url + field_api_path
    r = requests.get(url);
    fields = r.json()
    for field in fields:
        if "id" in field:
            field_name_map[field["id"]] = field
    return field_name_map

def add_missing_issue_fields(src_jira_url, issue, field_map, user_map):
    issue_api_path = "/rest/api/2/issue/%s" % (issue["key"],)
    url = src_jira_url + issue_api_path
    r = requests.get(url);
    rest_issue = r.json()

    if rest_issue["fields"]["issuelinks"]:
        print src_jira_url + "/browse/" + issue["key"]
    return

if __name__ == "__main__":

    if len(sys.argv) != 5:
        sys.stderr.write("Usage: %s user_mappings.tsv src_jira_url dest_jira_url file.json > out.json\n" % sys.argv[0])
        sys.stderr.write("Example: %s user_mappings.tsv https://issues.cloudera.org https://issues.apache.org/jira file.json > out.json\n" % sys.argv[0])
        sys.exit(1)

    user_mappings_filename = sys.argv[1]
    src_jira_url = sys.argv[2]
    dest_jira_url = sys.argv[3]
    filename = sys.argv[4]

    # Read the username mappings.
    user_map = get_user_mappings(user_mappings_filename)

    # Fetch the global list of fields from the server.
    field_map = get_field_map(src_jira_url)

    with open(filename, "r") as f:
        data = json.load(f)
        for proj in data["projects"]:
            project_key = None
            release_version_map = None
            for issue in proj["issues"]:
                if project_key is None:
                    project_key, _ = issue["key"].split("-", 2)
                    release_version_map = get_version_map(src_jira_url, dest_jira_url, project_key)

                sys.stderr.write("INFO: Processing %s...\n" % (issue["key"],))
                add_missing_issue_fields(src_jira_url, issue, field_map, user_map)

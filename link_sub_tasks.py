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

# Script that adds the sub-task-links by polling the source URL since the exported
# JSON dump doesn't include this information

import json
import requests
import sys
import time
import requests
from collections import defaultdict
from remap_users import get_user_mappings

from jira import JIRA
from jira.exceptions import JIRAError

requests.packages.urllib3.disable_warnings()

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.stderr.write("Usage: %s file.json jira_url > out.json\n" % sys.argv[0])
        sys.stderr.write("Example: %s file.json https://issues.cloudera.org > out.json\n" % sys.argv[0])
        sys.exit(1)

    filename = sys.argv[1]
    jira = JIRA(sys.argv[2])

    links = []
    with open(filename, "r") as f:
        data = json.load(f)
        for proj in data["projects"]:
            project_key = proj["key"]
            for issue in proj["issues"]:
                if project_key is None:
                    project_key, _ = issue["key"].split("-", 2)
                # Use an externalId that is same as the issue key
                issue["externalId"] = issue["key"]
                if "issueType" in issue.keys() and issue["issueType"] != "Sub-task":
                    continue
                sys.stderr.write("INFO: Processing subtasks for %s...\n" % (issue["key"],))
                try:
                  issue_json = jira.issue(issue["key"]).raw
                except JIRAError as e:
                  continue
                if "parent" not in issue_json["fields"].keys(): continue
                parent_key = issue_json["fields"]["parent"]["key"]

                # Build the entry for links list.
                sub_task_link = {}
                sub_task_link["name"] = "sub-task-link"
                sub_task_link["sourceId"] = issue["key"]
                sub_task_link["destinationId"] = parent_key

                links.append(sub_task_link)

    data["links"] = links
    print json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '))

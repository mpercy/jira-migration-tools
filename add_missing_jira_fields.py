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

# Custom fields. These vary by project. If this doesn't apply to you, just
# leave the CUSTOM_FIELD_IDS list blank.
CUSTOM_FIELD_IDS = [ "customfield_10060",   # "Target Version/s"
                     "customfield_10066"    # "Code Review"
                    ]

# This "Resolution" map is manually constructed by looking at the output from
# the REST API calls from the source and destination JIRAs. In this case:
#
# https://issues.cloudera.org/rest/api/2/resolution
# https://issues.apache.org/jira/rest/api/2/resolution
#
# If you are importing from/to other JIRA servers then you will have to come up
# with your own mappings. This can't be fully automated because the names
# aren't guaranteed to match (custom Resolution values are common).
# On the bright side, "Resolution" is "global" for a given JIRA server -- it's
# not project-specific.
resolution_map = {
    "1" : "1", # Fixed
    "2" : "2", # Won't fix
    "3" : "3", # Duplicate
    "4" : "4", # Incomplete
    "5" : "5", # Works for me / Cannot reproduce
    "6" : "6", # Not A Bug / Invalid
    "10003" : "7", # Feedback received / Later
    "10001" : "8", # Won't do / Not a problem
    "10004" : "9", # Information provided / Unresolved
    "10008" : "10", # Delivered / Implemented
    "10000" : "11", # Done
    "z1" : "10000", # Auto Closed
    "z2" : "10001", # Pending Closed
    "z3" : "10002", # REMIND
    "z4" : "10003", # Resolved
    "10002" : "5", # Cannot reproduce
    "10005" : "8", # Not delivered
    "10006" : "1", # Staged
    "10007" : "2", # Workaround
    "10100" : "1", # Configuration change
    "10101" : "1", # Deployed
    "10102" : "1", # Patch applied
    "10103" : "1", # Patch created
    "10104" : "4", # Unresolved

    # Alternate world of resolutions from jira.cloudera.com (due to a prior JIRA migration).
    "7" : "1", # Patch created
    "8" : "1", # Patch applied
    "9" : "1", # Configuration change
    "10" : "6", # Not a bug
    "11" : "7", # Feedback received
    "12" : "9", # Information provided
    "13" : "1", # Delivered
    "14" : "8", # Not Delivered
    "15" : "9", # Unresolved
    "16" : "1", # Staged
    "17" : "10", # Deployed
    "18" : "11", # Done
    # 1000 # "Won't do". This conflicts with "Done" above, so we'll just ignore this.
}

def get_version_map(src_jira_url, dest_jira_url, project_key):
    version_api_path = "/rest/api/2/project/%s/versions" % (project_key,)
    version_name_map = defaultdict(list)
    for root in (src_jira_url, dest_jira_url):
        url = root + version_api_path
        r = requests.get(url);
        versions = r.json()
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

    # Note: The REST issues API has a different JSON schema than the JSON import/export API.
    # The JSON import/export format is documented here:
    # https://confluence.atlassian.com/jira/importing-data-from-json-495976468.html

    # For some reason, the resolution field is not exported by the exporter, so we add it back here.
    # If Resolution is not set, it doesn't appear in the REST API output.
    if "resolution" in rest_issue["fields"]:
        res = rest_issue["fields"]["resolution"]
        if res:
            issue["resolution"] = res["name"]

    # Component/s is also missing from the export.
    component_names = []
    for c in rest_issue["fields"]["components"]:
        component_names.append(c["name"])
    issue["components"] = component_names

    # Affects Version/s is also missing. It's an array, empty if not set.
    affects_version_names = []
    for v in rest_issue["fields"]["versions"]:
        affects_version_names.append(v["name"])
    issue["affectedVersions"] = affects_version_names

    # Fix Version/s is also missing.
    fix_version_names = []
    for v in rest_issue["fields"]["fixVersions"]:
        fix_version_names.append(v["name"])
    issue["fixedVersions"] = fix_version_names

    # Attachments are also missing.
    # Documentation for JSON import of attachments:
    # https://confluence.atlassian.com/jira061/jira-administrator-s-guide/migrating-from-other-issue-trackers/importing-data-from-json-beta-release
    attachments = rest_issue["fields"]["attachment"]
    for a in attachments:
        author_oldname = a["author"]["name"]
        if author_oldname not in user_map:
            sys.stderr.write("ERROR: attachment user '%s' not in username map\n" % (author_oldname,))
            sys.exit(1)
        issue["attachments"].append({ "name": a["filename"],
                                      "attacher": user_map[author_oldname],
                                      "created": a["created"],
                                      "uri": a["content"],
                                      "description": "" })

    # Custom fields. Add the fields you want to pull to the CUSTOM_FIELD_IDS
    # array at the top of this file.
    # At the time of this writing, support for doing the mapping for different
    # field types is limited, but this script can easily be augmented to
    # support different field types. Docs on custom field formats are here:
    # https://confluence.atlassian.com/jira/importing-data-from-json-495976468.html#ImportingDatafromJSON-CustomFields
    for custom_field_id in CUSTOM_FIELD_IDS:
        if custom_field_id not in field_map:
            sys.stderr.write("ERROR: Unable to find custom field '%s' in field map" % (custom_field_id,))
            sys.exit(1)
        field = field_map[custom_field_id]
        if not field["custom"]:
            sys.stderr.write("ERROR: Only custom fields are supported in this code path. Field '%s' is not a custom field" % (custom_field_id,))
            sys.exit(1)
        custom_field_name = field["name"]
        custom_field_type = field["schema"]["type"]
        custom_field_customtype = field["schema"]["custom"]

        # Handle the different types of fields here.
        custom_field_out = None

        if custom_field_customtype == "com.atlassian.jira.plugin.system.customfieldtypes:multiversion":
            # Note: This code path would probably also work for generic arrays of strings.
            custom_field_out = { "fieldName": custom_field_name, "fieldType": custom_field_customtype, "value": [] }
            if rest_issue["fields"][custom_field_id]:
                for entry in rest_issue["fields"][custom_field_id]:
                    custom_field_out["value"].append(entry["name"])
        elif custom_field_type == "string":
            if custom_field_id in rest_issue["fields"] and rest_issue["fields"][custom_field_id] is not None:
                custom_field_out = { "fieldName": custom_field_name,
                                     "fieldType": custom_field_customtype,
                                     "value": rest_issue["fields"][custom_field_id] }
        else:
            # TODO: Add handling for more custom types here.
            sys.stderr.write("ERROR: Handler needed for custom field '%s' with name '%s' of type '%s'" % (custom_field_id, custom_field_name, custom_field_customtype))
            sys.exit(1)

        if custom_field_out is not None:
            issue["customFieldValues"].append(custom_field_out)

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

                for h in issue["history"]:
                    if "items" in h:
                        for item in h["items"]:
                            value_fields = ["oldValue", "newValue"] # correct history as needed
                            for value_field in value_fields:
                                if "field" in item and value_field in item and "newDisplayValue" in item:
                                    # Apply resolution mappings.
                                    if item["field"] == "resolution":
                                        item[value_field] = resolution_map[item[value_field]]
                                    # Apply version mappings.
                                    if item["field"] == "Version" or item["field"] == "Fix Version":
                                        if item[value_field] in release_version_map:
                                            item[value_field] = release_version_map[item[value_field]]
                                        else:
                                            # TODO: Potentially crash with error in this case.
                                            pass

                                    # Note: This mapping may not apply to all projects.
                                    # Target Version/s is a JSON-encoded array of ints.
                                    if item["field"] == "Target Version/s":
                                        vals = json.loads(item[value_field])
                                        for i in range(len(vals)):
                                            if str(vals[i]) in release_version_map:
                                                vals[i] = int(release_version_map[str(vals[i])])
                                            else:
                                                # TODO: Potentially crash with error in this case.
                                                pass
                                        item[value_field] = json.dumps(vals);

        print json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '))

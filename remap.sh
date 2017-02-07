#!/bin/bash
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
# Convenience script to run remap_users.py and add_missing_jira_fields.py in
# succession.
#
###############################################################################
set -e

MAPPINGS=$1
REMOVE_LIST=$2
SOURCE_URL=$3
DEST_URL=$4
INFILE=$5
OUTFILE=$6

NO_NULLS="$(mktemp)"
# Remove null bytes, which cause import to choke and die
sed -r 's/([^\])\\u0000/\1/g' "${INFILE}" >"${NO_NULLS}"

if [ -z "$6" -o -n "$7" ]; then
  echo "Usage: $0 user_mappings.tsv users_to_remove.lst src_jira_url dest_jira_url infile outfile.json"
  echo "Example: $0 user_mappings.tsv users_to_remove.lst https://issues.cloudera.org https://issues.apache.org/jira infile.json outfile.json"
  exit 1
fi

TMPFILE=$(mktemp)
TMPFILE2=$(mktemp)
TMPFILE3=$(mktemp)
ROOT=$(dirname $0)

echo Remapping users...
$ROOT/remap_users.py "$MAPPINGS" "$REMOVE_LIST" "$DEST_URL" "${NO_NULLS}" > "$TMPFILE"

echo Adding missing fields...
$ROOT/add_missing_jira_fields.py "$MAPPINGS" "$SOURCE_URL" "$DEST_URL" "$TMPFILE" > "$TMPFILE2"

echo Fixing sub-task links...
$ROOT/link_sub_tasks.py "$TMPFILE2" "$SOURCE_URL" > "$TMPFILE3"

# Remove the null bytes again, just in case?
sed -r 's/([^\])\\u0000/\1/g' "${TMPFILE3}" >"${OUTFILE}"

rm "$TMPFILE"
rm "$TMPFILE2"
rm "$TMPFILE3"
echo Done
exit 0

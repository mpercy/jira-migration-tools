#!/bin/bash
#########################3
set -e

MAPPINGS=$1
REMOVE_LIST=$2
SOURCE_URL=$3
DEST_URL=$4
INFILE=$5
TMPFILE=$6
OUTFILE=$7

if [ -z "$MAPPINGS" -o -z "$INFILE" -o -z "$TMPFILE" -o -z "$OUTFILE" ]; then
  echo "Usage: $0 user_mappings.tsv users_to_remove.lst src_jira_url dest_jira_url infile outfile.json"
  echo "Example: $0 user_mappings.tsv users_to_remove.lst https://issues.cloudera.org https://issues.apache.org/jira infile.json outfile.json"
  exit 1
fi

echo Remapping users...
./remap_users.py "$MAPPINGS" "$REMOVE_LIST" "$INFILE" > "$TMPFILE"

echo Adding missing fields...
./add_missing_jira_fields.py "$SOURCE_URL" "$DEST_URL" "$TMPFILE" > "$OUTFILE"

rm "$TMPFILE"
echo $Done
exit 0

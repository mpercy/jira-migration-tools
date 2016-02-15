#!/bin/bash
#########################
set -e

MAPPINGS=$1
REMOVE_LIST=$2
SOURCE_URL=$3
DEST_URL=$4
INFILE=$5
OUTFILE=$6

if [ -z "$6" -o -n "$7" ]; then
  echo "Usage: $0 user_mappings.tsv users_to_remove.lst src_jira_url dest_jira_url infile outfile.json"
  echo "Example: $0 user_mappings.tsv users_to_remove.lst https://issues.cloudera.org https://issues.apache.org/jira infile.json outfile.json"
  exit 1
fi

TMPFILE=$(mktemp -t "$OUTFILE.tmp.XXXXXX")
ROOT=$(dirname $0)

echo Remapping users...
$ROOT/remap_users.py "$MAPPINGS" "$REMOVE_LIST" "$DEST_URL" "$INFILE" > "$TMPFILE"

echo Adding missing fields...
$ROOT/add_missing_jira_fields.py "$MAPPINGS" "$SOURCE_URL" "$DEST_URL" "$TMPFILE" > "$OUTFILE"

rm "$TMPFILE"
echo Done
exit 0

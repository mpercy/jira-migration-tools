#!/usr/bin/env python2

import codecs
import filecmp
from jira import JIRA
from jira.exceptions import JIRAError
import os
import re
import requests
import stat
import sys
import tempfile
import urllib

requests.packages.urllib3.disable_warnings()

# TODO(jbapple): Have asked on https://issues.apache.org/jira/browse/INFRA-12157 for a new
# docs text field on issues.apache.org and issues-test.a.o

EQUAL_FIELD_IDS = {
    "versions",
    "assignee",
#    "attachment", # attachments are compared separately
    "comment",
    "components",
    "created",
    "creator",
    "description",
    "duedate",
    "environment",
    "fixVersions",
    "thumbnail",
    "issuetype",
    "issuekey",
    "labels",
    "issuelinks",
    "priority",
    "project",
    "reporter",
    "resolution",
    "resolutiondate",
    "security",
    "status",
    "subtasks",
    "summary",
    "votes",
    "watches",
    "workratio"}
CUSTOMFIELD_MAP = {
#    10177: 12312421,
    10055: 12311123,
    10053: 12311120,
    10052: 12311121,
    10054: 12311122,
    10021: 12310291,
    10020: 12310290,
    #10056: 12311820,
    10023: 12310293,
    10060: 12310320}
FIELD_MAP = dict({"customfield_" + str(keynum): "customfield_" + str(valnum) for
                  (keynum, valnum) in CUSTOMFIELD_MAP.iteritems()},
                 **{key: key for key in EQUAL_FIELD_IDS})

# A sample JSON dump of a jira is like follows
# http://github.mtv.cloudera.com/gist/bharathv/f54f22d96e6787eb7c84c09efbadaa81
# Given two jiras, the matching fields from it should be as follows
# - [key] - ID of the jira
# - [fields][issuetype][name] - Issue type
# - [fields][issuetype][subtask] - Is it a subtask?
# - [fields][fixVersions] - List of fixVersions
# - [fields][resolution][name] - Resoultion type
# - [fields][watches][watchCount] - No. of watchers
# - [fields][priority][name] - Priority of the jira
# - [fields][labels] - List of labels
# - [fields][versions] - List of versions applied
# - [fields][issuelinks] - List of issue links
# - [fields][status][name] - Current status of the jira
# - [fields][components] - List of components
# - [fields][attachment] - List of attachments
# - [fields][summary] - Summary of the jira (String match)
# - [fields][subtasks] - List of subtasks
# - [fields][comments] - List of comments
# - [fields][votes][votes] - No. of votes.

apache_jira = JIRA('https://issues-test.apache.org/jira')
cloudera_jira = JIRA('https://issues.cloudera.org')

IGNORABLE_KEYS = {'16x16', '24x24', '32x32', '48x48', 'timeZone', 'displayName'}
IGNORABLE_PATHS = {'priority.iconUrl', 'comment.comments.self', 'comment.comments.id',
                   'resolution.description', 'fixVersions.self', 'fixVersions.id',
                   'versions.self', 'versions.id', 'issuetype.iconUrl',
                   'reporter.emailAddress', 'project.id', 'assignee.emailAddress',
                   'comment.comments.updateAuthor.emailAddress',
                   'comment.comments.author.emailAddress', 'creator',
                   'issuetype.avatarId', 'project.self', 'status.description',
                   'resolution.id', 'resolution.self', 'components.self', 'components.id',
                   'comment.comments.updated', 'issuetype.self', 'issuetype.id',
                   'attachment', # attachments are checked separately
}

mismatches = set()

SUBSTITUTIONS = [('issues.cloudera.org/browse/HUE','HUE_PLACEHOLDER_ASF'),
                 ('issues.cloudera.org', 'issues-test.apache.org/jira'),
                 ('HUE_PLACEHOLDER_ASF','issues.cloudera.org/browse/HUE')]

NAME_SUBS = []

with codecs.open(sys.argv[1], 'r', 'utf-8') as f:
  for line in f:
    if line.find('=') >= 0:
      [old, new] = line.split('=')
      NAME_SUBS += [(old, new.strip())]

COMPILED_RES = []

for k, v in NAME_SUBS:
  COMPILED_RES += [(re.compile(u'^{}$'.format(k)), v)]
  COMPILED_RES += [(re.compile(u'user\?username={}$'.format(k)),
                    u'user?username={}'.format(v.replace(u"@", u"%40")))]

NAME_CONTEXTS = [u'[~{}]']

# Compare field1 and field2 and print if they don't match
def compare_and_print_fields(field1, field2, comp, path=''):
  global mismatches
  if path in IGNORABLE_PATHS: return
  if type(field1) not in [list, dict] and type(field2) not in [list, dict]:
    if (path, field1, field2) in mismatches: return
  if type(field1) == type(field2) == unicode:
    for k,v in SUBSTITUTIONS:
      if path != 'description':
        field1 = field1.replace(k, v)
    for context in NAME_CONTEXTS:
      for k,v in NAME_SUBS:
        field1 = field1.replace(context.format(k), context.format(v))
    for k,v in COMPILED_RES:
      field1 = re.sub(k, v, field1)
    field1 = field1.strip()
    field2 = field2.strip()
  if field1 == field2: return
  if type(field1) == type(field2):
    if type(field1) == dict:
      for k,v in field1.iteritems():
        pk = path + '.'+k
        if pk in IGNORABLE_PATHS: continue
        if k not in field2:
          if v:
            if (pk,v) not in mismatches:
              mismatches.add((pk,v))
              print "Missing key:", pk, repr(v)
        else:
          if field1[k] != field2[k]:
            if k not in IGNORABLE_KEYS:
              compare_and_print_fields(v, field2[k], comp, path + '.' + str(k))
          del(field2[k])
      for k,v in field2.iteritems():
        pk = path + '.' + k
        if pk in IGNORABLE_PATHS: continue
        if v:
          if type(v) == dict: v = repr(v)
          if (pk,v) not in mismatches:
            mismatches.add((pk,v))
            print "Missing key:", pk, repr(v)
      return
    elif type(field1) == list:
      for i in range(0, len(field1)):
        if i >= len(field2):
          print "Missing list item (in LHS only):", path, field1[i]
        else:
          compare_and_print_fields(field1[i], field2[i], comp, path)
      if len(field2) > len(field1):
        print "Missing list items (in RHS only):", path, field2[len(field1):]
      return
  if type(field1) in [list, dict] or type(field2) in [list, dict]:
    print "Mismatched", path, field1, field2
  elif (path, field1, field2) not in mismatches:
    mismatches.add((path, field1, field2))
    print "Mismatched", path, repr(field1), repr(field2)


def compare_and_print_lists(list1, list2, comp):
    if len(list1) != len(list2):
        print "Mismatched length for fields: " + comp, list1, list2
        return
    # Sort the two lists and compare the corresponding fields.
    list1.sort()
    list2.sort()
    for i in range(0, len(list1)):
        if list1[i] == list2[i]: continue
        print "Mismatched lists at index : ", i, comp, str(list1), str(list2)
        break

# Compare two jiras src and dest. They should be in the raw json format
def compare_jiras(src, dest):
    print "Comparing " + src["key"] + " with " + dest["key"]
    for cloudera_field, apache_field in FIELD_MAP.iteritems():
      if cloudera_field in src["fields"] and apache_field in dest["fields"]:
        compare_and_print_fields(src["fields"][cloudera_field],
                                 dest["fields"][apache_field],
                                 str((cloudera_field, apache_field)),
                                 cloudera_field)
      if (cloudera_field in src["fields"] and src["fields"][cloudera_field]
          and apache_field not in dest["fields"]):
        print "Missing field in apache:", (cloudera_field, apache_field,
                                           src["fields"][cloudera_field])
      if (apache_field in dest["fields"] and dest["fields"][apache_field]
          and cloudera_field not in src["fields"]):
        print "Missing field in cloudera:", (cloudera_field, apache_field,
                                             dest["fields"][apache_field])

    return

MISSING_JIRAS = [335, 566, 830, 854]

# Compare jira issues from IMPALA-$start to IMPALA-$max_range from apache_jira and cloudera_jira
# URLS above.
def compare_all_jiras(start, max_range):
    for i in range(start, max_range):
      if i in MISSING_JIRAS: continue
      try:
        src_issue = cloudera_jira.issue('IMPALA-' + str(i)).raw
        dest_issue = apache_jira.issue('IMPALA-' + str(i)).raw
        compare_jiras(src_issue, dest_issue)
      except JIRAError as e:
        print "Error fetching jira " + str(i) + ":" + format(e)


# Example usage. Compares jiras from IMPALA-101 to IMPALA-200
compare_all_jiras(1, 6000)

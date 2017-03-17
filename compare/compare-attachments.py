#!/usr/bin/env python2

# Checks issues on different servers for equal attachments.

# If an issue cannot be read, it is considered to have the "same" attachments as an issue
# with no attachments.

import argparse
import hashlib
import json
from multiprocessing import Pool
import urllib
import os
import re
import requests
import sys
import xml.etree.ElementTree as ET

requests.packages.urllib3.disable_warnings()

def hash_filename(filename):
  """Files are compared by their hashes."""
  h = hashlib.sha512()
  with open(filename, "rf") as f:
    for chunk in iter(lambda: f.read(4096), b""):
      h.update(chunk)
  return h.hexdigest()
  os.remove(filename)

def get_xml_attachments(key, server):
  """Returns a set of (filename, sha512hash) tuples derived from the XML dump of 'key'
  (like "IMPALA-123") at 'server' (like "https://issues-test.apache.org/jira")."""
  url= ("{server}/si/jira.issueviews:issue-xml/{key}/{key}.xml"
        .format(server=server, key=key))
  while True:
    try:
      page = urllib.urlopen(url)
      break
    except IOError:
      #sys.stdout.write('timeout ')
      #sys.stdout.flush()
      pass
  if page.getcode() == 404:
    # http 404 issues are considered to have no attachments
    return {}
  xmlissue = page.read()
  try:
    root = ET.fromstring(xmlissue)
  except:
    print url
    raise
  [channel] = [x for x in list(root) if x.tag == "channel"]
  [item] = [x for x in list(channel) if x.tag == "item"]
  [attachments] = [x for x in list(item) if x.tag == "attachments"]
  attachment_list = [x for x in list(attachments) if x.tag == "attachment"]
  result = {}
  for attachment in attachment_list:
    ident = attachment.attrib['id']
    name = attachment.attrib['name']
    url = '{server}/secure/attachment/{ident}/{name}'
    url = url.format(server=server, ident=ident, name=urllib.quote(name.encode('utf8')))
    while True:
      try:
        (filename, _) = urllib.urlretrieve(url)
        break
      except:
        pass
    info = (name, hash_filename(filename))
    if info in result: result[info] += [url]
    else: result[info] = [url]
  return result

def get_json_attachments(issue_dict):
  """Returns a set of (filename, sha512hash) like get_xml_attachments, above, but for a
  dictionary parsed from a JSON issue produced by running add_missing_jira_fields.py on an
  exported JSON issue."""
  result = {}
  if "attachments" in issue_dict:
    for attachment in issue_dict["attachments"]:
      url = attachment["uri"]
      while True:
        try:
          (filename, _) = urllib.urlretrieve(url)
          break
        except:
          pass
      info = (attachment["name"], hash_filename(filename))
      if info in result: result[info] += [url]
      else: result[info] = [url]
  return result

KEY_REGEX = re.compile("^.+-([1-9][0-9]*)$")

def compare_json_issue_attachments((json_issue, minkey_num, maxkey_num, new_server)):
  key = json_issue["key"]
  key_num = int(KEY_REGEX.match(key).group(1))
  if key_num < minkey_num or key_num >= maxkey_num: return
  from_json = get_json_attachments(json_issue)
  while True:
    try:
      from_xml = get_xml_attachments(key, new_server)
      break
    except:
      pass
  result = ""
  for info, urls in from_json.iteritems():
    if info not in from_xml:
      result += "\nAdd {} times: {}".format(len(urls), urls[0])
    elif len(from_xml[info]) < len(urls):
      result += "\nAdd {} times: {}".format(len(urls) - len(from_xml[info]), urls[0])
    elif len(from_xml[info]) > len(urls):
      for i in xrange(0, len(from_xml[info]) - len(urls)):
        result += "\nRemove {}".format(from_xml[info][i])
  for info, urls in from_xml.iteritems():
    if info not in from_json:
      for url in urls:
        result += "\nRemove {}".format(url)
  if result: print key, result

def parallel_compare_export_attachments(json_export, minkey, maxkey, new_server):
  minkey_num = int(KEY_REGEX.match(minkey).group(1))
  maxkey_num = int(KEY_REGEX.match(maxkey).group(1))
  json_issues = [json_issue for json_project in json_export["projects"]
                 for json_issue in json_project["issues"]]
  p = Pool(16)
  p.map(compare_json_issue_attachments,
        [(json_issue, minkey_num, maxkey_num, new_server) for json_issue in json_issues])


def compare_export_attachments(json_export, minkey, maxkey, new_server):
  minkey_num = int(KEY_REGEX.match(minkey).group(1))
  maxkey_num = int(KEY_REGEX.match(maxkey).group(1))
  for json_project in json_export["projects"]:
    for json_issue in json_project["issues"]:
      key = json_issue["key"]
      key_num = int(KEY_REGEX.match(key).group(1))
      if key_num < minkey_num or key_num >= maxkey_num: continue
      sys.stdout.write(key)
      sys.stdout.flush()
      from_json = get_json_attachments(json_issue)
      from_xml = get_xml_attachments(key, new_server)
      if len(from_json) == 0 == len(from_xml):
        print " NO-OP"
      elif from_json == from_xml:
        print " SUCCEED"
      else:
        print " FAIL", from_json, from_xml, from_json.symmetric_difference(from_xml)

def compare_xml_attachments(key, server1, server2):
  sys.stdout.write(key + ' ')
  sys.stdout.flush()
  attachments1 = get_xml_attachments(key, server1)
  attachments2 = get_xml_attachments(key, server2)
  if len(attachments1) == 0 == len(attachments2):
    return
  elif attachments1 == attachments2:
    print "\n{}: SUCCEED".format(key)
  else:
    print "\n{}: FAIL".format(key)
    print attachments1, "\n"
    print attachments2, "\n"
    print attachments1.symmetric_difference(attachments2), "\n"

if __name__ == "__main__":
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  old = parser.add_mutually_exclusive_group()
  old.add_argument("--json", help="Filename of the JSON export")
  old.add_argument("--old_server", default="https://issues.cloudera.org", help=" ")
  parser.add_argument("--minkey", default="IMPALA-1", help=" ")
  parser.add_argument("--maxkey", default="IMPALA-6000", help=" ")
  parser.add_argument("--new_server", default="https://issues.apache.org/jira",
                      help=" ")
  args = parser.parse_args()
  if args.json:
    parallel_compare_export_attachments(
        json.load(open(args.json)),
        args.minkey, args.maxkey, args.new_server)
  else:
    start = int(KEY_REGEX.match(args.minkey).group(1))
    end = int(KEY_REGEX.match(args.maxkey).group(1))
    for key in xrange(start, end):
      compare_xml_attachments("IMPALA-{}".format(key), args.old_server, args.new_server)
    print ""

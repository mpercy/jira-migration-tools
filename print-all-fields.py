#!/usr/bin/env python

# Fetch and print the full set of fields from a given JIRA installation. The purpose is to
# enable a human to inspect the fields and match up corresponding fields for use in:
#
# 1. Cleaning up the exported JSON in preparation for import
# 2. Comparing the imported issues to the corresponding issues in the source JIRA
#    installation

import jira
import optparse
import re
import requests
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

requests.packages.urllib3.disable_warnings()

def print_fields(server_url):
  server = jira.JIRA({"server": server_url})
  fields = server.fields()
  print "\n".join(sorted([str((field["name"].upper(), field["id"])) for field in fields]))

SERVERS = {"apache": "http://issues.apache.org/jira/",
           "cloudera": "http://issues.cloudera.org/"}

print_fields(SERVERS[sys.argv[1]])

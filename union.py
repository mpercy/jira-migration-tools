#!/usr/bin/env python2

import json
import sys

def dict2list(d, keyname):
  result = []
  for k,v in d.iteritems():
    v.update({keyname: k})
    result.append(v)
  return result

def list2dict(l, keyname):
  result = {}
  for v in l:
    k = v.pop(keyname)
    result[k] = v
  return result

result = json.load(open(sys.argv[1]))

for filename in sys.argv[2:]:
  export = json.load(open(filename))

  old_projects = list2dict(result["projects"], "key")
  new_projects = list2dict(export["projects"], "key")
  for key, project in old_projects.iteritems():
    if key in new_projects:
      project["issues"] = project["issues"] + new_projects[key]["issues"]
  result["projects"] = dict2list(old_projects, "key")

  old_users = list2dict(result["users"], "name")
  new_users = list2dict(export["users"], "name")
  old_users.update(new_users)
  result["users"] = dict2list(old_users, "name")

print json.dumps(result, indent = 2)

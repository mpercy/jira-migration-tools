import hashlib
import jira
import json
import os
import requests
import stat
import sys

# For unicode printing:
reload(sys)
sys.setdefaultencoding("utf-8")

def load_manual_usernames(filename):
  result = {}
  with open(filename) as f:
    for line in f:
      source = sink = line.strip()
      if "=" in source:
        [source, sink] = source.split("=")
      result[source] = sink
  return result

def get_matching_usernames(manual_username_map,
                           upstream_server_url, json_export_filenames):
  jiracred_filename = os.path.dirname(os.path.abspath(__file__)) + "/.jiracred"
  assert 0 == os.stat(jiracred_filename).st_mode & (stat.S_IRWXG | stat.S_IRWXO), (
    "credentials insecure")
  jiracred_username = ""
  jiracred_password = ""
  with open(jiracred_filename) as jiracred_file:
    jiracred_username = jiracred_file.readline().strip()
    jiracred_password = jiracred_file.readline().strip()
  # Ignore environment's SSL problems:
  requests.packages.urllib3.disable_warnings()
  source_user_emails = {}
  for json_export_filename in json_export_filenames:
    with open(json_export_filename) as json_export_file:
      export = json.load(json_export_file)
      for user in export["users"]:
        source_user_emails[user["name"]] = user["email"]
  upstream_jira = jira.JIRA({'server': upstream_server_url, 'verify': False},
                            basic_auth = (jiracred_username, jiracred_password))
  result = {}
  for name, email in sorted(source_user_emails.items()):
    sys.stdout.write(name + "=")
    sys.stdout.flush()
    if name in manual_username_map:
      result[name] = manual_username_map[name]
    else:
      result[name] = name + "_impala_" + hashlib.md5(name).hexdigest()[0:4]
      while True:
        try:
          candidate_names = upstream_jira.search_users(email)
          if candidate_names:
            result[name] = candidate_names[0].name
          break
        except Exception as e:
          print >> sys.stderr, e
    print result[name]
  return result

if __name__ == "__main__":
  manual_usernames = load_manual_usernames(sys.argv[1])
  upstream_server_url = sys.argv[2]
  json_export_filenames = sys.argv[3:]
  get_matching_usernames(manual_usernames, upstream_server_url, json_export_filenames)

#!/usr/bin/python
###############################################################################
import json
import sys

def format_user_profile_link(user, url):
    return " ".join([user["name"], user["email"], user["fullname"], "%s/secure/ViewProfile.jspa?name=%s" % (url, user["name"])])

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print "Usage: %s file.json > out.json" % sys.argv[0]
        sys.exit(1)

    files = sys.argv[1:]

    print

    for fname in files:
        with open(fname, "r") as f:
            data = json.load(f)
            for user in data["users"]:
                print format_user_profile_link(user, "https://issues.apache.org/jira")
    print
    sys.exit(0)

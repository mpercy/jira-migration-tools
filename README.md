# jira-migration-tools

Tools for migrating between JIRA instances using JSON import/export.

The major benefit to using JSON export vs. XML export is that the JIRA and
plugin versions don’t have to match between the source and destination
instances. Another benefit is that it is possible to use scripts to munge the
JSON to help with the migration, as the tools in this repository do. Strangely,
the XML exported from JIRA has an apparently invalid charset encoding and
doesn’t parse with a typical XML parser (at least in my experience, using the
standard Python libs).

The scripts here have the following requirements:
* Reasonably new version of JIRA on both sides (JIRA 6.1 should be sufficient,
  not sure what the minimum version is).
* The machine running the script must be able to simultaneously access the REST
  web service APIs on both the source and the destination JIRA instances.

The scripts provide the following features:
* Mapping / rewriting user account ids, including watchers and at-mentions.
* Migrating Fixed Versions, Components, attachments, and more.

There are several manual steps involved in migrating a JIRA project from one
instance to another, and they can be time consuming. The scripts in this
repository attempt to automate as much as possible. Please feel free to submit
a pull request if you make an improvement to these scripts, such as
implementing support for more custom field types in
`add_missing_jira_fields.py`.

Steps to migrate a JIRA project from one instance to another:

1. Enable JSON export on the source JIRA instance (the instance you are
   migrating away from) as an admin. You must enable both JSON plugins (the
   search one and the issues one). Instructions:
   https://confluence.atlassian.com/display/JIRAKB/How+To+Enable+JSON+Export+in+JIRA  
   Summary:
   1. Log in to an account with either **JIRA Administrators** or **JIRA System Administrators** Global Permission
   2. Navigate to the **Add-ons** page (Gear menu > Add-ons)
   3. Go to the **Manage add-ons** page
   4. Change the Filter to include **All add-ons**
   5. Locate **jira-importers-plugin** (or **JIRA Importers Plugin (JIM)**) and click to expand
   6. Expand to show a list of all modules
   7. Enable the 2 modules needed to enable JSON export (the names of the modules might differ depending on versions).
      In version 6.4.12 they are called **JSON (searchrequest-json)** and **JSON (issue-json)**.
2. **As an admin user**, run a search and choose Export > JSON. Do this for only
   1000 issues at a time (JIRA does not support exporting more than 1000 per
   search). You can formulate such a search request with syntax like
   `project = KUDU AND id > KUDU-1000 AND level is EMPTY order by id ASC`. If
   you wish to **exclude** any issues from your export, apply those filters at
   this time (the "level is EMPTY" clause in the above example only includes
   issues which do not have a Security Level defined). Repeat until you have
   JSON files containing all of the issues. **After you do this, you may want
   to disable the export plugins again**, because “regular” (non-admin) users
   will see the JSON export button, but they will get an error if they attempt
   to use it, which may be confusing.
3. Define the "Resolution" mappings between the instances. This is a manual
   process, since JIRA projects commonly define custom Resolutions. Since
   Resolution IDs are global for all projects on a given instance, this only
   has to be done once per pair of JIRA instances (as source and destination
   instances). You will have to update the resolution mappings defined in
   `add_missing_jira_fields.py` in a dict called `resolution_map`. The list of
   resolutions can be found with the REST API on each instance, at a URL that
   looks like the following:
   http://issues.apache.org/jira/rest/api/2/resolution  
   You can find documentation on the JIRA REST API at:
   https://docs.atlassian.com/jira/REST/latest/
4. Determine all of the username mappings you need. Usernames on different JIRA
   instances are distinct, and there may be name conflicts when you try to
   migrate. The default behavior of a JIRA project will be to attribute
   comments, assigned tickets, and at-mentions in comments to the user with
   the same username. If the account does not exist, it will be auto-created.
   1. You need to create two files: a user-mappings file and a user-excludes
      file. The user-mappings file contains a tab-separated mapping of
      old-username to new-username, one per line (old being the source
      instance, new being the destination instance). See
      `user_mappings.tsv.example` in this repository for an example. The
      user-mappings file is also allowed to have a single username on a line,
      with no tab, meaning that the username will be the same between the two
      instances (an "identity" mapping).

      The user-excludes file contains one
      username per line of user accounts that will be excluded from the dump.
      See `user_excludes.lst.example` in this repository for an example of this
      file format. For users in this exclude list, any comments or history that
      is attributed to this user in the dump (if the user does not already
      exist in the destination instance) will be instead attributed to the user
      doing the import on the destination instance (typically the administrator
      performing the import).
   2. If you start with empty files for the user-mappings and user-exclude
      files, and run `remap_users.py`, a list of users that were not accounted for will be printed to
      stderr. All users must be in one of the two files before the script will successfully complete. This behavior is intended to help ensure that no users are "missed"
      during the import. You can determine the mappings and add users to the
      appropriate files until `remap_users.py` stops complaining about missing
      users. Note: in most cases, all the users should end up in the mappings
      file, and the excludes file should be nearly empty. I primarily added
      some "system" users there who I didn't want to import into the destination
      JIRA.
   3. As you are creating the username mappings, if you find someone with a
      username on the source instance that conflicts with someone else on the
      destination JIRA instance, ask the user to create a new user account on
      the destination so that you can add a mapping for it. Else, you may want
      to simply choose a non-conflicting destination JIRA username for them. If
      they don’t already have a user account on the destination instance, and
      the name they were using on the source instance is not yet claimed on the
      destination instance, then they don't necessarily have to manually create
      an account at the destination. An account with the same details will be
      automatically be created for them when the JSON dump is imported into the
      destination instance (they will likely need to reset their password to
      gain access to the account though, since the password isn't automatically
      migrated).
5. Run the scripts to remap the users and fill in the fields missing from the
   initial export. Then import the resulting dump into the destination JIRA.
   This process requires some back-and-forth, because some mappings (such as
   version mappings) cannot be determined by the scripts until an initial
   import is done at the destination. The steps are:
   1. Use `remap_users.py` to apply the username mappings to the JSON dump.
   2. Import the result of this into the destination JIRA. This will create
      new users, as well as define IDs for Versions, Components, etc.
   3. Use `add_missing_jira_fields.py` to fill in the missing fields and do
      the version mappings for the file outputted from `remap_users.py`. This
      script will make REST calls to both the source and destination
      instances to determine the necessary field ID mappings.
   4. Delete all of the previously-imported issues from the **destination**
      project so that we can re-import them with correct history and field
      values.
   5. Import the JSON file created in step (iii).

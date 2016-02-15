# jira-migration-tools

Tools for migrating between JIRA instances using JSON import/export.

Note that using the JSON approach outlined here, attachments will not be
migrated to the new instance. The major benefit to using JSON export vs. XML
export is that the JIRA and plugin versions don’t have to match between the
source and destination instances. Another benefit is that it is easy to use
scripts to munge the JSON to help with the migration, as the tools in this
repository do. Strangely, the XML exported from JIRA has an apparently invalid
charset encoding and doesn’t parse with a typical XML parser (at least in my
experience, using the standard Python libs).

There are several manual steps involved in preparing a JIRA JSON export, and
the process is time consuming:

1. Enable JSON export on the source JIRA instance as
   an admin. You must enable both JSON plugins (the search one and the issues
   one). Instructions here:
   https://confluence.atlassian.com/display/JIRAKB/How+To+Enable+JSON+Export+in+JIRA
2. *As an admin user*, run a search and choose export as JSON. Do this for 1000
   issues at a time (JIRA does not support exporting more than 1000 per
   search). Repeat until you have JSON files containing all of the issues.
   *After you do this, you may want to disable the export plugins again*,
   because “regular” (non-admin) users will see the JSON export button, but
   they will get an error if they attempt to use it.
3. Figure all of the username mappings you need. Usernames on different JIRA
   instances are distinct, and there may be name conflicts. The default
   behavior of a JIRA project will be to attribute comments, assigned tickets,
   and at-mentions in comments to the user with that name. If the account does
   not exist, it will be auto-created.
   a. You have to run through the list of users exported with the list of
      tickets and figure out whether or not they conflict between the two
      systems. If someone is using a username that conflicts, ask them to
      create a new user account and add a mapping. If they don’t already have a
      user account on the destination instance, and the name they were using on
      the source instance is not already claimed on the destination instance,
      then you don’t have to do anything -- their account will automatically be
      created when the import is done in the destination instance from the JSON
      dump. *TODO*: A script in this repo helps with this: It’s called
      check_profiles.py and all it does is output a URL you can click to check
      if the username in the source instance is available in the ASF instance,
      or if it’s been taken, or if it’s somebody else, etc.
4. Figure out the resolution mappings between the instances. This is a manual
   and somewhat obscure step. Since Resolution IDs are global for all projects
   on a given instance, this only has to be "figured out" once per pair of
   servers as the source and destination instances. The list of resolutions can
   be found with the REST API on each instance, at a URL that looks like the
   following: http://issues.apache.org/jira/rest/api/2/resolution
   If you want documentation on the JIRA REST API you can look here:
   https://docs.atlassian.com/jira/REST/latest/
5. Run the scripts to remap the users, versions, and resolutions.
   *TODO: Document the latest versions of the scripts.*

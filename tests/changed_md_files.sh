#!/bin/bash


# TRAVIS_PULL_REQUEST: The pull request number if the current job
# is a pull request, “false” if it’s not a pull request.

# If not pull request
if [[ $TRAVIS_PULL_REQUEST == 'false' ]]
then
  # Get list of .md fies changed since previous commit
  changed_files=`git diff --name-only HEAD~1`
else # this is a PR
  # Get list of .md files changed compared to master
  changed_files=`git diff --name-only master`
fi

# echo "$changed_files"
cat "$changed_files" | grep .md$ > /tmp/files.txt

# Cat the contents of the changed md files to a single md file
for file in `cat /tmp/files.txt`; do cat "$file"; done

exit 0

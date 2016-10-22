#!/bin/bash

if [ `git symbolic-ref --short HEAD` = "master" ]
then
  # Get list of .md fies changed since previous commit
  changed_files=`git diff --name-only HEAD~1`
else
  # Get list of .md fies changed compared to master
  changed_files=`git diff --name-only master`
fi

echo "$changed_files" | grep .md$

exit 0

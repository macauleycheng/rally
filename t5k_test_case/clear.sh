#!/bin/bash

for id in $(rally task list --uuids);
do
rally task delete $id --force
done

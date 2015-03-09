#!/bin/bash

while true
do
	echo $(date) :: ingest: $(./scripts/ingest-queue.py -H schwa10 count 2> /dev/null) :: download: $(./scripts/download-queue.py -H schwa10 count 2> /dev/null) ::  extract: $(./scripts/extraction-queue.py -H schwa10 count 2> /dev/null)
	sleep 60
done

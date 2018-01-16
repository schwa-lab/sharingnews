#!/bin/bash

wait="$1"
if [ -z "$wait" ]
then
	wait=60
fi

while true
do
	echo $(date) :: ingest: $(./scripts/ingest-queue.py -H schwa10 count 2> /dev/null) :: download: $(./scripts/download-queue.py -H schwa10 count 2> /dev/null) ::  extract: $(./scripts/extraction-queue.py -H schwa10 count 2> /dev/null)
	sleep $wait
done

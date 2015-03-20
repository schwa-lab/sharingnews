#!/bin/bash

grep 'True|2' site.txt |
cut -d'|' -f4,5 |
tr ' ' '_' |
awk -F'|' '{ print (NR % 60)","((NR + 30) % 60)" * * * * cd ~likeable/data/homepage-deltas/ && mkdir -p \""$1"\" && cd \""$1"\" && ~likeable/likeable/scripts/delta-scrape.sh \"" $2 "\" > /dev/null" }'

#!/bin/bash

set -e

out_dir=$(python scripts/download-weekly-delta.py ~likeable/data/weekly-delta)

(if head -n1 $out_dir/sites.txt | grep -qv 'site_Id'
then
	# header absent
	head -n1 ~likeable/data/site.txt
fi ;
cat $out_dir/sites.txt
) | python scripts/pg-loaders/load-site.py
python scripts/join-weekly-delta.py $out_dir/WEEKLYDELTA_article.report.txt $out_dir/WEEKLYDELTA_statistic.summary.txt | python scripts/ingest-queue.py -H schwa10 --batch-size 40 enqueue

gzip $out_dir/*

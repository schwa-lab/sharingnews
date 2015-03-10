#!/bin/bash
if [ "$(scripts/download-queue.py -H schwa10 count 2>/dev/null)" -eq 0 ]
then
    if pgrep -f "scripts/ids-for-download.py" >/dev/null; then
        echo "ids-for-download process already running"
    fi
    scripts/ids-for-download.py 5000 |
    scripts/download-queue.py -H schwa10 --log-path ~likeable/logs/fetch/fetch-schwa09-cron.log.bz2 enqueue 2>&1 | grep 'ERROR'
fi

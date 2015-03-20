#!/bin/bash
if [ "$(scripts/extraction-queue.py -H schwa10 count 2>/dev/null)" -eq 0 ]
then
    if pgrep -f "scripts/ids-for-extraction.py" >/dev/null; then
        echo "ids-for-extraction process already running"
    fi
    scripts/ids-for-extraction.py |
    scripts/extraction-queue.py -H schwa10 --log-path ~likeable/logs/extract/extract-schwa09-cron.log.bz2 enqueue 2>&1 | grep 'ERROR'
fi

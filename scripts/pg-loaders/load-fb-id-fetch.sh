#!/bin/bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT INT TERM HUP
mkfifo "$tmpdir/pipe"

python -c '
from __future__ import print_function
import sys, json
for l in sys.stdin:
    try:
        obj = json.loads(l)
        items = obj.items()
    except Exception, e:
        print(repr(e), l, file=sys.stderr)
    else:
        for k, v in items:
            if v is None:
                continue
            v["_id"] = k
            print(json.dumps(v))
' |
sed 's/"title":"http[^"]*",//g' |
sed 's/\\/\\\\/g' > $tmpdir/pipe &

ls -l $tmpdir/pipe

psql -h schwa09 likeable likeable -e <<EOF
\\set ON_ERROR_STOP 1
\\echo \`date\`
CREATE TEMPORARY TABLE jsontmp$$ (blob JSON);
\\copy jsontmp$$ FROM '$tmpdir/pipe' DELIMITER '	';
\\echo \`date\`
CREATE TEMPORARY TABLE articletmp$$ (id BIGINT PRIMARY KEY, blob JSON);
INSERT INTO articletmp$$ SELECT DISTINCT ON (id) (blob->>'_id')::bigint AS id, blob FROM jsontmp$$;
--SELECT * FROM articletmp$$ LIMIT 2;
DROP TABLE jsontmp$$;
\\echo \`date\`
UPDATE likeable_article SET
    fb_created = (blob->>'created_time')::timestamp
    -- update other fields in case FB has improved
    -- fb_updated = (blob->>'updated_time')::timestamp,
    -- title = blob->>'title',
    -- fb_has_title = (blob->>'title') IS NOT NULL,
    -- description = blob->>'description',
    -- fb_type = blob->>'type'
    FROM articletmp$$ WHERE articletmp$$.id = likeable_article.id;
\\echo \`date\`
DROP TABLE articletmp$$;
EOF

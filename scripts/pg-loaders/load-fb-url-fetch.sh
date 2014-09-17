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
    except Exception, e:
        print(repr(e), l, file=sys.stderr)
    else:
        if obj is None:
            continue
        for k, v in obj.items():
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
CREATE TEMPORARY TABLE articletmp$$ (id BIGINT, url VARCHAR(1000), fb_updated TIMESTAMP, fb_type VARCHAR(35), title TEXT, description TEXT, total_shares BIGINT);
\\copy jsontmp$$ FROM '$tmpdir/pipe' DELIMITER '	';

\\echo \`date\`
EXPLAIN ANALYZE INSERT INTO articletmp$$ (id, url, fb_updated, fb_type, title, description, total_shares)
    SELECT (blob->'og_object'->>'id')::bigint, blob->'og_object'->>'url', (blob->'og_object'->>'updated_time')::timestamp, blob->'og_object'->>'type', blob->'og_object'->>'title', blob->'og_object'->>'description', (blob->'share'->>'share_count')::bigint FROM jsontmp$$;

\\echo \`date\`
EXPLAIN ANALYZE INSERT INTO likeable_article (id, url, fb_updated, fb_type, fb_has_title, title, description, total_shares, url_signature_id)
	SELECT DISTINCT ON (id) t.id, t.url, fb_updated, fb_type, title IS NOT NULL, title, description, total_shares, url_signature_id
    FROM articletmp$$ t LEFT JOIN likeable_spideredurl s ON t.url = s.url
	WHERE t.id IS NOT NULL
	AND t.url IS NOT NULL
	AND NOT EXISTS (SELECT 'X' FROM likeable_article WHERE likeable_article.id = t.id)
	AND char_length(t.url) < 1000;

\\echo \`date\`
EXPLAIN ANALYZE UPDATE likeable_spideredurl SET article_id = (blob->'og_object'->>'id')::bigint
	FROM jsontmp$$ WHERE blob->>'_id' = likeable_spideredurl.url;

\\echo \`date\`
DROP TABLE jsontmp$$;
DROP TABLE articletmp$$;
EOF

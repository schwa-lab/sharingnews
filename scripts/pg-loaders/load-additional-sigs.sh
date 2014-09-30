#!/bin/bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT INT TERM HUP
mkfifo "$tmpdir/pipe"

echo 'copy (select url from likeable_article where url_signature_id is null) to stdout;' | ./manage.py dbshell > $tmpdir/data

cat $tmpdir/data | scripts/url-append-sig.py | sed 's/\\/\\\\/g' > $tmpdir/pipe &

psql -h schwa09 likeable likeable -e <<EOF
\\set ON_ERROR_STOP 1
CREATE TEMPORARY TABLE sigtmp (url TEXT, sigid INT, sig TEXT, domain TEXT);
\\copy sigtmp (url, sig, domain) FROM '$tmpdir/pipe' DELIMITER '	';
\\echo \`date\`
UPDATE sigtmp SET sigid = lus.id
    FROM likeable_urlsignature lus WHERE lus.signature = sig;
\\echo \`date\`
INSERT INTO likeable_urlsignature (signature, base_domain)
	SELECT DISTINCT ON (sig) sig, domain FROM sigtmp WHERE sigid IS NULL AND CHAR_LENGTH(sig) <= 300;
\\echo \`date\`
UPDATE sigtmp SET sigid = lus.id
    FROM likeable_urlsignature lus WHERE lus.signature = sig AND sigid is NULL;
\\echo \`date\`
UPDATE likeable_article SET url_signature_id = sigid
    FROM sigtmp WHERE likeable_article.url = sigtmp.url;
\\echo \`date\`
SELECT * FROM sigtmp WHERE CHAR_LENGTH(sig) > 300;
EOF

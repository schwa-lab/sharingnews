#!/bin/bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT INT TERM HUP
mkfifo "$tmpdir/pipe"

sed 's/\r$//' |
tail -n+2 |
grep '|http' |
cut -d'#' -f1 |
python -c '
import sys
from likeable_scrapy.cleaning import url_signature, strip_subdomains
for l in sys.stdin:
    sig = url_signature(l.split("|")[-1].rstrip())
    sig += (strip_subdomains(sig[0]),)
    print("{}|{}{}/{}|{}".format(l.rstrip(), *sig))
' |
sed 's/\\/\\\\/g' > $tmpdir/pipe &

ls -l $tmpdir/pipe

psql -h schwa09 likeable likeable -e <<EOF
\\set ON_ERROR_STOP 1
\\echo \`date\`
CREATE TABLE spidertmp (swid BIGINT, "when" TIMESTAMP, url CHAR(1000), signature CHAR(1000), base_domain CHAR(200));
\\copy spidertmp FROM '$tmpdir/pipe' DELIMITER '|';
\\echo \`date\`
INSERT INTO likeable_urlsignature (signature, base_domain)
	SELECT DISTINCT ON (signature) signature, base_domain FROM spidertmp
    WHERE CHAR_LENGTH(base_domain) < 50 AND CHAR_LENGTH(signature) < 256 -- discard noise
	AND NOT EXISTS (SELECT 'X' FROM likeable_urlsignature WHERE likeable_urlsignature.signature = spidertmp.signature)
\\echo \`date\`
INSERT INTO likeable_spideredurl (url, url_signature_id)
	SELECT DISTINCT ON (spidertmp.url) spidertmp.url, likeable_urlsignature.id
    FROM spidertmp LEFT JOIN likeable_urlsignature ON spidertmp.signature = likeable_urlsignature.signature
	WHERE NOT EXISTS (SELECT 'X' FROM likeable_spideredurl WHERE likeable_spideredurl.url = spidertmp.url);
\\echo \`date\`
INSERT INTO likeable_sharewarsurl (id, "when", spidered_id)
    SELECT spidertmp.swid, spidertmp."when", likeable_spideredurl.id
    FROM spidertmp LEFT JOIN likeable_spideredurl ON spidertmp.url = likeable_spideredurl.url;
\\echo \`date\`
DROP TABLE spidertmp;
EOF

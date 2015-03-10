#!/bin/bash
# Site ID was not initially provided. This loader expects:
# article_Id|site_Id

if [ $# != 1 ]
then
	echo 'Usage: '$0' <path/to/site/mapping>'
	exit 1
fi

psql -h schwa09 likeable likeable -e <<EOF
\\set ON_ERROR_STOP 1
\\echo \`date\`
CREATE TEMPORARY TABLE sitetmp$$ (article_Id INTEGER, site_Id INTEGER);
\\copy sitetmp$$ FROM '$1' DELIMITER '|';
\\echo \`date\`
SELECT COUNT(*) from sitetmp$$;
\\echo \`date\`
UPDATE likeable_sharewarsurl swu SET site_id = t.site_Id
FROM sitetmp$$ t WHERE t.article_Id = swu.id;
\\echo \`date\`
UPDATE likeable_article a SET sharewars_site_id = t.site_Id
FROM sitetmp$$ t
LEFT JOIN likeable_sharewarsurl swu ON t.article_Id = swu.id
LEFT JOIN likeable_spideredurl spu ON swu.spidered_id = spu.id
WHERE spu.article_id = a.id;
\\echo \`date\`
EOF

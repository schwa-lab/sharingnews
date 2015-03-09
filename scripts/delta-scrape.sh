#!/bin/bash

url="$1"
ts=$(date)

usage() {
	echo $0 'url' >&2
}

if [ -z "$url" ]
then
	usage
	exit 1
fi
if [ -n "$2" ]
then
	usage
	exit 1
fi

if [ ! -d .git ]
then
	git init
fi

USERAGENT='Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
tmpf=$(mktemp)
git rm -rf --ignore-unmatch *
wget -E -H -k -p -A .htm,.html,.css -U "$USERAGENT" "$url" 2>$tmpf &&
(
	home_url=$(cat $tmpf |
		grep ' saved \[' |
		head -n1 |
		sed "s/^[^']*'//;s/. saved .*//")
	if [ -z "$home_url" ]
	then
		# Show wget output because no file saved
		cat $tmpf >&2
	fi
	echo $home_url > _home_path.url
)
git add * 2>/dev/null &&
git commit -m "Fetch $url at $ts"

if [ $RANDOM -lt 1000 ]  # roughly 1/32
then
	# This can be expensive on memory so we only do it occasionally
	git repack &&
	git gc --aggressive 2>/dev/null
fi

rm $tmpf

if [ "$(git log --since '6 hours ago' | wc -l)" -eq "0" ]
then
	echo 'Nothing committed at ' $PWD 'for 6 hours'
fi

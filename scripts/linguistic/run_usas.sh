#!/bin/bash
path="$1"
curl -F "tagset=c7" -F "style=vert" -F text=@"$path" http://ucrel.lancs.ac.uk/cgi-bin/usas.pl | grep ^0000

#!/bin/bash
pushd `dirname $0` > /dev/null
SCRIPTPATH=`pwd -P`
popd > /dev/null
POMPATH=$SCRIPTPATH/cleartk-pom.xml
if [ ! -f $pom ]
then
	echo Could not find POM at $POMPATH >&2
	exit 1
fi
if [ $# != 2 ]
then
	echo Usage: $0 INPUT-DIR OUTPUT-DIR >&2
	exit 1
fi
INDIR=$1
OUTDIR=$2
mvn -f $POMPATH exec:java -Dexec.mainClass="org.cleartk.timeml.TimeMlAnnotate" -Dexec.args="$INDIR $OUTDIR"

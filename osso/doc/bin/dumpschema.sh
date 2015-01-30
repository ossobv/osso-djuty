#!/bin/sh
myuser="$1"
mypass="$2"
mydbname="$3"

[ -z "$myuser" ] && echo "Usage: $0 <myuser> <mypass> <mydbname>" >&2 && exit 1

schema="`dirname "$0"`"/../sql/schema.sql
echo -n "Writing to $schema ... "
mysqldump -d -u"$myuser" -p"$mypass" "$mydbname" \
    | sed -e '{
/^-- \(Dump completed\|Host:\|Server version\)/d;
/^\/\*!50013/d;
/^\(\/\*!40101 \)\?SET \(@saved_cs\|character_set\)/d;
/^-- MySQL dump [0-9]\+/d;
s/ AUTO_INCREMENT=[0-9]*//g;
s/ AUTO_INCREMENT/ auto_increment/;
s/ COLLATE / collate /;
s/ DEFAULT\(.*\),/ default\1,/;
s/ PRIMARY KEY  (/ PRIMARY KEY (/
}' > "$schema"
echo "done"

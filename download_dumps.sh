LANG=$1
OUTPUT=$2
MATCH=$3
if [[ -z $LANG ]]; then
  echo "Usage: $0 LANG [OUTPUT_DIR] [MATCHING_STRING]"
fi
if [[ -z $OUTPUT ]]; then
  OUTPUT=.
fi

BASE=http://dumps.wikimedia.org/${LANG}wiki
DATE=`elinks -no-references -no-numbering -dump $BASE | grep '[0-9]\{8\}'/ | tail -1|awk '{print $1}' | cut -d / -f 1`
CURRENT=${BASE}/${DATE}/

FILES=`elinks -no-references -no-numbering -dump $CURRENT | grep -e $LANG'wiki-.*\.' | awk '{print $2}'`

for FILE in $(echo $FILES)
do
  if [[ -z $MATCH || `echo $FILE | grep $MATCH` ]]; then
    echo Downloading $FILE ...
    wget -N -P $OUTPUT "$CURRENT/$FILE"
  fi
done

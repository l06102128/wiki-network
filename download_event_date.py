#!/usr/bin/env python

##########################################################################
#                                                                        #
#  This program is free software; you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation; version 2 of the License.               #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#  GNU General Public License for more details.                          #
#                                                                        #
##########################################################################

import simplejson
import urllib
import sys
import csv
import logging
import re


def get_event_date(title, csv_writer, lang):
    api_base = 'http://%s.wikipedia.org/w/api.php' % lang
    options = {}
    options.update({
        'action': 'query',
        'prop': 'revisions',
        'titles': title,
        'rvprop': 'content',
        'format': 'json'
    })
    url = api_base + '?' + urllib.urlencode(options)
    logging.info(url)
    result = simplejson.load(urllib.urlopen(url))
    pages = result["query"]["pages"]
    for page in pages:
        content = pages[page]["revisions"][0]["*"]
    date = ""
    for line in content.split("\n"):
        if re.match("", line):
            result = re.search("(\d{4})", line)
            if result:
                date = result.group(0)
    csv_writer.writerow([title, date])


def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] page_title output_file")
    p.add_option('-l', '--lang', action="store", dest="lang", default="en",
                 help="Wikipedia language")
    p.add_option('-c', '--clean', action="store_true", dest="clean",
                 help="Clean wiki syntax / HTML")
    opts, files = p.parse_args()
    if len(files) != 2:
        p.error("Wrong parameters")
    logging.basicConfig(stream=sys.stderr,
                        level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    csv_reader = csv.reader(open(files[0], "r"))
    csv_writer = csv.writer(
        open(files[1], "w"),
        delimiter="\t",
        quotechar='"',
        quoting=csv.QUOTE_ALL
    )

    for page in csv_reader:
        get_event_date(page[0], csv_writer, opts.lang)


if __name__ == "__main__":
    main()

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
from sonet.mediawiki import _diff_text
from django.utils.encoding import smart_str
import logging
from sonet.mediawiki import TextCleaner


def get_revisions(title, csv_writer, lang, textcleaner,
                  startid=None, prev_text=""):
    api_base = 'http://%s.wikipedia.org/w/api.php' % lang
    options = {}
    options.update({
        'action': 'query',
        'prop': 'revisions',
        'rvlimit': 500,
        'titles': title,
        'rvprop': 'ids|timestamp|content',
        'rvdir': 'newer',
        'format': 'json'
    })
    if startid != None:
        options.update({
            'rvstartid': startid
        })
    url = api_base + '?' + urllib.urlencode(options)
    logging.info(url)
    result = simplejson.load(urllib.urlopen(url))
    pages = result["query"]["pages"]
    for page in pages:
        revs = pages[page]["revisions"]
        for r in revs:
            text_cleaned = textcleaner.clean_all(r["*"])
            text = smart_str(_diff_text(prev_text, text_cleaned)[0])
            csv_writer.writerow([r["timestamp"], lang, smart_str(title),
                                "", text])
            prev_text = text_cleaned
    try:
        cont = result['query-continue']['revisions']['rvstartid']
        logging.info("Continue to %d", cont)
        get_revisions(title, csv_writer, lang, cont, prev_text)
    except KeyError:
        logging.info("Finished!")


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
    csv_writer = csv.writer(open(files[1], "w"),
                 delimiter="\t",
                 quotechar='"',
                 quoting=csv.QUOTE_ALL)
    textcleaner = None
    if opts.clean:
        textcleaner = TextCleaner()
    get_revisions(files[0], csv_writer, opts.lang, textcleaner)

if __name__ == "__main__":
    main()

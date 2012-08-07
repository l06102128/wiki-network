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
from sonet.mediawiki import TextCleaner
from pywc import PyWC, perc

from math import asin, sqrt, atan


def calc_arcsin(value):
    return asin(sqrt(value / 100.0)) * 45.0 / float(atan(1))


def find_revision_id(title, revision, lang, startid=None):
    api_base = 'http://%s.wikipedia.org/w/api.php' % lang
    options = {}
    options.update({
        'action': 'query',
        'prop': 'revisions',
        'titles': title,
        'rvlimit': 500,
        'rvprop': 'ids',
        'rvdir': 'newer',
        'format': 'json',
    })

    if startid != None:
        options.update({'rvstartid': startid})

    url = api_base + '?' + urllib.urlencode(options)
    logging.info(url)
    result = None
    i = 0
    while result is None and i < 10:
        i += 1
        try:
            result = simplejson.load(urllib.urlopen(url))
        except Exception:
            logging.error("Can't get JSON from %s", url)
    if result is None:
        return None

    if revision < 500:
        pages = result["query"]["pages"]
        try:
            rev = pages[pages.keys()[0]]["revisions"][revision]
        except IndexError:
            logging.error("Error getting revision #%d", revision)
            return None
        else:
            return rev["revid"]
    else:
        try:
            cont = result['query-continue']['revisions']['rvstartid']
        except KeyError:
            logging.error("No such revision!")
        else:
            logging.info("Continue to %d", cont)
            return find_revision_id(title, revision - 500, lang, cont)


def get_revision(revision_id, lang):
    api_base = 'http://%s.wikipedia.org/w/api.php' % lang
    options = {}
    options.update({
        'action': 'query',
        'prop': 'revisions',
        'revids': revision_id,
        'rvprop': 'content',
        'format': 'json',
    })

    url = api_base + '?' + urllib.urlencode(options)
    logging.info(url)
    result = None
    i = 0
    while result is None and i < 10:
        i += 1
        try:
            result = simplejson.load(urllib.urlopen(url))
        except Exception:
            logging.error("Can't get JSON from %s", url)
    if result is None:
        return ""

    pages = result["query"]["pages"]
    return pages[pages.keys()[0]]["revisions"][0]["*"]


def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] dic input_file output_file")
    p.add_option('-l', '--lang', action="store", dest="lang", default="en",
                 help="Wikipedia language")
    p.add_option('-n', '--edits', action="store", dest="edits", type=int,
                 default=500, help="Edit number to consider")
    opts, files = p.parse_args()
    if len(files) != 3:
        p.error("Wrong parameters")
    logging.basicConfig(stream=sys.stderr,
                        level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    csv_reader = csv.reader(open(files[1], "r"))

    textcleaner = TextCleaner()
    pywc = PyWC()
    pywc.set_dic(files[0])

    try:
        cat_names = [str(x[1]) for x in sorted([(int(a), b) for a, b in
                     pywc.categories.items()])]
    except ValueError:
        cat_names = [str(x[1]) for x in sorted(pywc.categories.items())]

    reverse_categories = {}
    for key, value in pywc.categories.iteritems():
        reverse_categories[value] = key

    arcsin_fields = ["%s_arcsin" % key for key in cat_names]

    fields = ["title", "total_edits", "unique_editors", "traumatic",
              "non_traumatic", "natural", "human", "len", "len_cleaned"] + \
             cat_names + arcsin_fields + \
             ["qmarks", "unique", "dic", "sixltr", "total"]

    csv_writer = csv.DictWriter(open(files[2], "w"), fields)

    csv_writer.writeheader()

    for line in csv_reader:
        title, rev = line[0], opts.edits - 1
        revision_id = find_revision_id(title, rev, opts.lang, startid=None)
        if revision_id is None:
            continue
        rev = get_revision(revision_id, opts.lang)

        cleaned_rev = textcleaner.clean_all(rev)
        cleaned_rev = textcleaner.clean_wiki_syntax(cleaned_rev, True)

        pywc.parse_col(cleaned_rev)

        result = {
            "title": title,
            "total_edits": line[1],
            "unique_editors": line[2],
            "traumatic": line[3],
            "non_traumatic": line[4],
            "natural": line[5],
            "human": line[6],
            "len": len(rev.split()),
            "len_cleaned": len(cleaned_rev.split()),
            "qmarks": pywc._qmarks,
            "unique": len(pywc._unique),
            "dic": pywc._dic,
            "sixltr": pywc._sixltr,
            "total": pywc._total,
        }

        for key, val in reverse_categories.iteritems():
            score = perc(pywc._results[val], pywc._total) * 100
            arcsin = calc_arcsin(score)
            result[key] = score  # percentage results
            result["%s_arcsin" % key] = arcsin  # arcsin results

        csv_writer.writerow(result)


if __name__ == "__main__":
    main()

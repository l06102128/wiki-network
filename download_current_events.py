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
import logging
import urllib
import sys


def get_data(output, lang="en", eititle="Template:Current", eicontinue=None):
    """Function that extracts from the Wikipedia API which pages embed
       a specific template
    """
    done = False
    api_base = 'http://%s.wikipedia.org/w/api.php' % lang
    options = {
        'action': 'query',
        'list': 'embeddedin',
        'eilimit': 500,
        'eititle': eititle,
        'einamespace': 0,
        'format': 'json'
    }
    articles = []
    while not done:
        if eicontinue != None:
            options['eicontinue'] = eicontinue.encode("UTF-8")
        url = api_base + '?' + urllib.urlencode(options)
        logging.info(url)
        result = simplejson.load(urllib.urlopen(url))
        articles += ["%s\n" % x["title"].encode('UTF-8') \
                     for x in result["query"]["embeddedin"]]
        if "query-continue" in result:
            eicontinue = result["query-continue"]["embeddedin"]["eicontinue"]
        else:
            done = True
    with open(output, "w") as f:
        f.writelines(articles)


def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog lang page_title output_file")
    opts, files = p.parse_args()
    if len(files) != 3:
        p.error("Wrong parameters")

    logging.basicConfig(stream=sys.stderr,
                        level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    get_data(lang=files[0], eititle=files[1], output=files[2])


if __name__ == "__main__":
    main()

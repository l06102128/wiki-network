#!/usr/bin/env python

##########################################################################
#                                                                        #
# This program is free software; you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation; version 2 of the License.                #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           #
# GNU General Public License for more details.                           #
#                                                                        #
##########################################################################

from sonet.mediawiki import HistoryPageProcessor, \
                            get_translations, get_tags, \
                            explode_dump_filename

import csv
import sys
import logging
from random import random

from sonet import lib
from sonet.timr import Timr
from django.utils.encoding import smart_str

class HistoryRevisionsPageProcessor(HistoryPageProcessor):
    queue = None
    output = None
    desired_page_type = None

    def __init__(self, **kwargs):
        super(HistoryRevisionsPageProcessor, self).__init__(**kwargs)
        self.output = open(kwargs['output'], 'w')
        self.queue = []

    def save(self):
        """
        it flushes the queue containing the processed and chosen pages
        on the csv output file
        """
        if len(self.queue):
            #logging.info('Saving %d pages' % len(self.queue))
            for q in self.queue:
                if q and q != '': print >>self.output, q
            self.queue = []
        
    def end(self):
        logging.info('PAGES: %d' % (self.counter_pages,))
        self.save()

    def process_title(self, elem):

        #clean attributes
        self.delattr(("_counter", "_type", "_title"))

        a_title = elem.text.split(':')

        if len(a_title) == 1:
            if self.desired_page_type == "talk":
                self._skip = True
                return

            self._talk = False
            self._title = a_title[0]
        else:
            if a_title[0] == self.talkns and \
                    self.desired_page_type != "content":
                self._talk = True
                self._title = a_title[1]
            else:
                self._skip = True
                return

        self._desired = self.is_desired(self._title)

        if self._desired is not True and self.threshold < 1.:
           if random() > self.threshold:
                self._skip = True


    def process_page(self, elem):

        if self._skip is not True:
            self.queue.append(smart_str('%s%s' % (
                'Talk:' if self._talk else '',self._title,))
            )

        self.counter_pages += 1

        if not self.counter_pages % 10000:
            self.save()
            logging.info('PAGES: %d' % (self.counter_pages,))

        self._skip = False

    def process_redirect(self, _):
        # This class only considers pages that are in the desired file,
        # these pages must not be redirects
        self._skip = True
        #raise ValueError, "The page %s is a redirect. " % self._title + \
        #                  "Pages in the desired list must not be redirects."


def create_option_parser():
    import argparse

    p = argparse.ArgumentParser(description='Extract a random sample of pages title \
                                out of a Wikipedia dump')

    ## optional parameters
    p.add_argument('-t', '--type', default="all", metavar="TYPE",
                   help="Type of page to analize (content|talk|all)")
    p.add_argument('-R', '--ratio', default=1., type=float, metavar="RATIO",
                  help="percentage of pages to be analyzed")

    ## positional arguments
    p.add_argument('xml_fn', help="wikipedia dump to be parsed", metavar="DUMP_FILE")
    p.add_argument('desired_pages_fn', help="csv file containing desired pages", metavar="DESIRED_PAGES_FILE")

    return p


def main():

    logging.basicConfig(#filename="random_page_extractor.log",
                                stream=sys.stderr,
                                level=logging.DEBUG)
    logging.info('---------------------START---------------------')

    op = create_option_parser()
    args = op.parse_args()

    with open(args.desired_pages_fn, 'rb') as f:
        desired_pages = [l[0].decode('latin-1') for l in csv.reader(f)
                                        if l and not l[0][0] == '#']

    lang, date_, _ = explode_dump_filename(args.xml_fn)
    deflate, _lineno = lib.find_open_for_this_file(args.xml_fn)

    if _lineno:
        src = deflate(args.xml_fn, 51)
    else:
        src = deflate(args.xml_fn)

    translation = get_translations(src)
    tag = get_tags(src, tags='page,title,redirect')

    src.close()
    src = deflate(args.xml_fn)

    output_fn = "%swiki-%s-random_page_list.csv" % (lang, date_)

    processor = HistoryRevisionsPageProcessor(tag=tag, lang=lang,
                                              output=output_fn,
                                              threshold=args.ratio)
    
    processor.talkns = translation['Talk']
    processor.desired_page_type = args.type
    processor.set_desired(desired_pages)
    with Timr('processing'):
        processor.start(src)


if __name__ == "__main__":
    main()


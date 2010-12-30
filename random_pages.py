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
from datetime import datetime

from sonet import lib
from sonet.timr import Timr
from django.utils.encoding import smart_str

class HistoryRevisionsPageProcessor(HistoryPageProcessor):
    queue = None
    output = None
    desired_page_type = None
    _counter_revisions = None
    _editors = None
    _min_text_length = None
    _initial_revision = None

    def __init__(self, **kwargs):
        super(HistoryRevisionsPageProcessor, self).__init__(**kwargs)
        self.queue = []

    def save(self):
        """
        it flushes the queue containing the processed and chosen pages
        on the csv output file
        """
        if len(self.queue):
            #logging.info('Saving %d pages' % len(self.queue))
            for q in self.queue:
                if q and q != '':
                    if self.output:
                        print >>self.output, q
                    else:
                        print q
            self.queue = []
        
    def end(self):
        logging.info('PAGES: %d' % (self.counter_pages,))
        self.save()

    def process_title(self, elem):

        #clean attributes
        self.delattr(("_counter", "_type", "_title", "_editors", "_initial_revision"))
        
        self._editors = []
        self._counter_revisions = 0
        self._min_text_length = 0

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


    def process_text(self, elem):
        if self._skip:
            return

        if self.min_text and \
            len(elem.text) < self.min_text:
            if self._desired:
                logging.warning('Desired page %s skipped due to its text size: %d' %
                         (self._title, len(elem.text)))
            self._skip = True
            return
        else:
            pass


    def process_timestamp(self, elem):
        if self._skip:
            return

        if self.start_revision and not self._initial_revision:
            
            timestamp = elem.text
            year = int(timestamp[:4])
            month = int(timestamp[5:7])
            day = int(timestamp[8:10])
            revision_time = datetime(year, month, day)

            if revision_time > self.start_revision:
                if self._desired:
                    logging.warning('Desired page %s skipped due to its initial revision date: %s' %
                         (self._title, revision_time.strftime('%Y-%m-%d')))
                self._skip = True
                return

            self._initial_revision = revision_time
            
        else:
            pass


    def process_username(self, elem):
        if elem.text and elem.text != '':
            u = elem.text.encode('utf-8')
        else:
            return

        if u not in self._editors:
            self._editors.append(u)


    def process_ip(self, elem):
        if elem.text and elem.text != '':
            u = elem.text
        else:
            return
        
        if u not in self._editors:
            self._editors.append(u)


    def process_page(self, elem):

        if not self._skip and not self._desired and self.threshold < 1.:
           if random() > self.threshold:
                self._skip = True
        
        if not self._skip and self.n_users and \
           len(self._editors) < self.n_users:
            if self._desired:
                logging.warning('Desired page %s skipped due to low number of editors: %d' %
                         (self._title, len(self._editors)))
            self._skip = True

        if not self._skip:
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


def dumps_checker(args, type_):
    import re

    #logging.info(args)

    if args.editors_number or args.initial_revision:
        assert re.search('.-(meta-history)', type_), "Wrong dump file, required: *-meta-history"

    if args.min_text_length:
        assert type_ == '-pages-meta-current', "Wrong dump file, required: pages-meta-current"

def create_option_parser():
    import argparse

    p = argparse.ArgumentParser(description='Extract a random sample of pages title \
                                out of a Wikipedia dump')

    ## optional parameters
    p.add_argument('-t', '--type', default="content", metavar="TYPE",
                   help="Type of page to analize (content|talk|all) - default: %(default)s")
    p.add_argument('-e', '--editors-number', default=0, metavar="NUM_EDITORS", type=int,
                   help="pages with less than NUM_EDITORS editors are skipped (default: %(default)s)")
    p.add_argument('-s', '--initial_revision', type=lib.yyyymmdd_to_datetime, metavar="YYYYMMDD",
                          help="Skip pages whose first revision occurred later than this date", default=None)
    p.add_argument('-r', '--ratio', default=1., type=float, metavar="RATIO",
                  help="percentage of pages to be analyzed")
    p.add_argument('-T', '--min-text-length', default=0, metavar="TEXT_LENGTH", type=int,
                   help="pages with text shorter than TEXT_LENGTH characters are skipped (default: %(default)s)")
    p.add_argument('-o', '--output', help="output file name", metavar="OUTPUT_FILE", default=None)

    ## positional arguments
    p.add_argument('xml_fn', help="wikipedia dump to be parsed", metavar="DUMP_FILE")
    p.add_argument('desired_pages_fn', help="csv file containing desired pages", metavar="DESIRED_PAGES_FILE")

    return p


def main():

    logging.basicConfig(#filename="random_page_extractor.log",
                                stream=sys.stderr,
                                level=logging.DEBUG)

    op = create_option_parser()
    args = op.parse_args()

    with open(args.desired_pages_fn, 'rb') as f:
        desired_pages = [l[0].decode('latin-1') for l in csv.reader(f)
                                        if l and not l[0][0] == '#']

    lang, date_, type_ = explode_dump_filename(args.xml_fn)
    deflate, _lineno = lib.find_open_for_this_file(args.xml_fn)

    dumps_checker(args, type_)

    logging.info('---------------------START---------------------')

    if _lineno:
        src = deflate(args.xml_fn, 51)
    else:
        src = deflate(args.xml_fn)

    translation = get_translations(src)
    tag = get_tags(src, tags='page,title,redirect,text,username,ip,timestamp')

    src.close()
    src = deflate(args.xml_fn)

    output = open(args.output, 'w') if args.output else None

    processor = HistoryRevisionsPageProcessor(tag=tag, lang=lang,
                                              output=output,
                                              threshold=args.ratio,
                                              min_text=args.min_text_length,
                                              n_users=args.editors_number,
                                              start_revision=args.initial_revision)
    
    processor.talkns = translation['Talk']
    processor.desired_page_type = args.type
    processor.set_desired(desired_pages)
    with Timr('processing'):
        processor.start(src)


if __name__ == "__main__":
    main()


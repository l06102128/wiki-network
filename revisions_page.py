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
                            TextCleaner, \
                            get_translations, get_tags, \
                            explode_dump_filename, _diff_text  #, diff_text
from sonet import lib
from django.utils.encoding import smart_str
import csv
#import difflib
import sys
import logging
from sonet.timr import Timr


class HistoryRevisionsPageProcessor(HistoryPageProcessor):
    output = None
    queue = None
    _skip = None
    _prev_text = ""
    _text = None
    get_talks = True
    get_articles = True
    diff_timeout = 0.5
    clean = None
    textcleaner = None

    def __init__(self, **kwargs):
        super(HistoryRevisionsPageProcessor, self).__init__(**kwargs)
        self.textcleaner = TextCleaner(userns)
        self.queue = []
        f = open(self.output, 'w')
        self._keys = ["timestamp", "lang", "title", "type", "text"]
        self.csv_writer = csv.DictWriter(f, fieldnames=self._keys,
                                         delimiter='\t', quotechar='"',
                                         quoting=csv.QUOTE_ALL)

    def flush(self):
        """
        Flushes queue in the CSV output
        """
        pages = [{'title': page['title'],
                  'lang': self.lang,
                  'timestamp': page['timestamp'],
                  'text': page['text'],
                  'type': page['type']} for page in self.queue]
        self.csv_writer.writerows(pages)
        self.queue = []

    def save(self):
        """
        Saves data to the queue.
        The queue is stored using self.flush()
        """
        if self._text is None: # difflib doesn't like NoneType
            self._text = ""
        if self.clean:
            self._text = self.textcleaner.clean_all(self._text)
        page = {'title': smart_str(self._title),
                'lang': self.lang,
                'timestamp': self._date,
                'text': smart_str(_diff_text(self._prev_text,
                                             self._text,
                                             timeout=self.diff_timeout)[0]),
                'type': self._type}
        self.queue.append(page)
        self._prev_text = self._text

    def process_title(self, elem):
        self.delattr(("_counter", "_type", "_title", "_skip", "_date", "text"))
        self._skip = False
        a_title = elem.text.split(':')

        if len(a_title) == 1 and self.get_articles:
            self._type = 'normal'
            self._title = a_title[0]
        elif len(a_title) == 2 and a_title[0] == self.talkns and \
             self.get_talks:
            self._type = 'talk'
            self._title = a_title[1]
        else:
            self._skip = True

        if not self._skip:
            self._desired = self.is_desired(self._title)
            if not self._desired:
                self._skip = True
            else:
                logging.info('Start processing desired page %s (%s)',
                             self._title, self._type)

    def process_timestamp(self, elem):
        if self._skip:
            return
        self._date = elem.text

    def process_text(self, elem):
        if self._skip:
            return
        self._text = elem.text
        self.save()

    def process_page(self, _):
        self.count += 1
        if not self.count % 1000:
            logging.info(' ### Processed %d pages', self.count)
        self.delattr(("text"))
        if not self._skip:
            with Timr('Flushing %s' % self._title):
                self.flush()
        self._skip = False

    def process_redirect(self, _):
        # This class only considers pages that are in the desired file,
        # these pages must not be redirects
        self._skip = True
        raise ValueError("The page %s is a redirect. " % self._title + \
                         "Pages in the desired list must not be redirects.")


def dumps_checker(dump_name):
    """
    Checks if wikimedia dump is *-meta-history in order to extract
    revisions
    >>> dumps_checker("wikimedia-pages-current")
    Traceback (most recent call last):
    AssertionError: Wrong dump file, required: *-meta-history
    >>> dumps_checker("wikimedia-pages-meta-history")
    """
    import re
    assert re.search('.-(meta-history)', dump_name), \
           "Wrong dump file, required: *-meta-history"


def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] input_file desired_list output_file")
    p.add_option('-t', '--type', action="store", dest="type", default="all",
                 help="Type of page to analize (content|talk|all)")
    p.add_option('-e', '--encoding', action="store", dest="encoding",
                 default="latin-1", help="encoding of the desired_list file")
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output (like timings)")
    p.add_option('-T', "--timeout", action="store", dest="timeout", type=float,
                 default=0.5, help="Diff timeout (default=0.5, 0=no timeout)")
    p.add_option('-c', '--clean', action="store_true", dest="clean",
                 default=False,
                 help="Cleans HTML, wiki syntax, acronyms and emoticons")
    opts, files = p.parse_args()

    if len(files) != 3:
        p.error("Wrong parameters")
    if opts.verbose:
        logging.basicConfig(stream=sys.stderr,
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

    xml = files[0]
    desired_pages_fn = files[1]
    output = files[2]

    dumps_checker(xml)

    lang, _, _ = explode_dump_filename(xml)
    deflate, _lineno = lib.find_open_for_this_file(xml)

    if _lineno:
        src = deflate(xml, 51)
    else:
        src = deflate(xml)

    translation = get_translations(src)
    tag = get_tags(src, tags='page,title,revision,timestamp,text,redirect')
    src.close()
    src = deflate(xml)

    processor = HistoryRevisionsPageProcessor(tag=tag, lang=lang,
                                              output=output,
                                              userns=translation['User'])
    processor.talkns = translation['Talk']
    if opts.type == 'talk':
        processor.get_articles = False
    elif opts.type == 'content':
        processor.get_talks = False
    processor.diff_timeout = opts.timeout
    processor.clean = opts.clean
    processor.set_desired_from_csv(desired_pages_fn, encoding=opts.encoding)
    with Timr('Processing'):
        processor.start(src) ## PROCESSING
    processor.flush()


if __name__ == "__main__":
    main()

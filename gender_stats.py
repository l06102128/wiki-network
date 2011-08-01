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
                            explode_dump_filename, \
                            ts2dt
from sonet import lib
from django.utils.encoding import smart_str
import csv
import sys
import logging
from sonet.timr import Timr
from collections import Counter

class GenderPageProcessor(HistoryPageProcessor):
    output = None
    csv_writer = None
    gender_data_fn = None
    gender_data = None
    csv_writer = None
    queue = None
    _skip = None
    _namespace = None
    _redirect = None
    _creation_date = None
    _gender_edits = None
    _anon_edits = None
    _total_edits = None
    _started_by = None

    def __init__(self, **kwargs):
        super(GenderPageProcessor, self).__init__(**kwargs)
        fields = ["title", "namespace", "redirect", "creation_date",
                  "started_by", "nr_anon_edits", "nr_registered_edits",
                  "nr_total_edits", "nr_female_edits", "nr_male_edits",
                  "nr_anon_editors", "nr_registered_editors",
                  "nr_total_editors", "nr_female_editors", "nr_male_editors"]
        self.csv_writer = csv.DictWriter(self.output, fields)
        self.csv_writer.writeheader()
        self.gender_data_fn = kwargs["gender_data"]
        self.gender_data = {}
        self.load_gender_data()

        self.queue = []

        self._gender_edits = {}
        self._anon_edits = []
        self._total_edits = []

    def load_gender_data(self):
        with open(self.gender_data_fn) as f:
            csv_reader = csv.reader(f)
            for line in csv_reader:
                try:
                    self.gender_data[line[1]] = line[2]
                except IndexError:
                    pass

    def flush(self):
        """
        Flushes queue in the CSV output
        """
        self.csv_writer.writerows(self.queue)
        self.queue = []

    def save(self):
        page = {
            "title": self._title.encode("UTF-8"),
            "namespace": self._namespace.encode("UTF-8"),
            "redirect": 1 if self._redirect else 0,
            "creation_date": self._creation_date,
            "started_by": self._started_by,
            "nr_anon_edits": len(self._anon_edits),
            "nr_registered_edits": len(self._total_edits),
            "nr_female_edits": len(self._gender_edits["female"]),
            "nr_male_edits": len(self._gender_edits["male"]),
            "nr_anon_editors": len(set(self._anon_edits)),
            "nr_registered_editors": len(set(self._total_edits)),
            "nr_female_editors": len(set(self._gender_edits["female"])),
            "nr_male_editors": len(set(self._gender_edits["male"])),
        }
        page["nr_total_edits"] = page["nr_anon_edits"] + \
                                 page["nr_registered_edits"]
        page["nr_total_editors"] = page["nr_anon_editors"] + \
                                   page["nr_registered_editors"]
        self.queue.append(page)

    def process_timestamp(self, elem):
        current_date = elem.text
        if not self._creation_date or self._creation_date > current_date:
            self._creation_date = current_date

    def process_title(self, elem):
        self.delattr(("_counter", "_type", "_title", "_skip", "_date",
                      "_redirect", "_creation_date", "_started_by"))
        self._gender_edits.clear()
        self._gender_edits["female"] = []
        self._gender_edits["male"] = []
        self._total_edits = []
        self._anon_edits = []

        a_title = elem.text.split(':')
        if len(a_title) == 1:
            self._type = 'normal'
            self._title = a_title[0]
            self._namespace = "article"
        else:
            if a_title[0] == self.talkns:
                self._type = 'talk'
            self._title = a_title[1]
            self._namespace = a_title[0]

    def process_username(self, elem):
        if self._skip:
            return
        user = elem.text
        gender = "missing"
        if user in self.gender_data:
            gender = self.gender_data[user]
            try:
                self._gender_edits[gender].append(user)
            except KeyError:
                self._gender_edits[gender] = [user]
        self._total_edits.append(user)
        if not self._started_by:
            self._started_by = gender

    def process_ip(self, elem):
        if self._skip:
            return
        self._anon_edits.append(elem.text)

    def process_redirect(self, _):
        if self._skip:
            return
        self._redirect = True

    def process_page(self, _):
        if self._skip:
            self._skip = False
            return
        self.save()
        self.count += 1
        if self.count % 1000 == 0:
            logging.info(' ### Processed %d pages - Flushing', self.count)
            self.flush()


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
        usage="usage: %prog [options] input_file gender_file output_file")
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output (like timings)")
    opts, files = p.parse_args()

    if len(files) != 3:
        p.error("Wrong parameters")
    if opts.verbose:
        logging.basicConfig(stream=sys.stderr,
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

    xml = files[0]
    gender_data = files[1]
    output = files[2]

    dumps_checker(xml)

    lang, _, _ = explode_dump_filename(xml)
    deflate, _lineno = lib.find_open_for_this_file(xml)

    if _lineno:
        src = deflate(xml, 51)
    else:
        src = deflate(xml)

    translation = get_translations(src)
    tag = get_tags(src,
                   tags="page,redirect,timestamp,ip,"
                        "contributor,title,username")
    src.close()
    src = deflate(xml)

    out = open(output, "w")
    processor = GenderPageProcessor(tag=tag, lang=lang,
                                    output=out,
                                    userns=translation['User'],
                                    gender_data=gender_data
                                   )
    with Timr('Processing'):
        processor.start(src) ## PROCESSING
    processor.flush()
    out.close()

if __name__ == "__main__":
    main()

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
import csv
import sys
import logging
from sonet.timr import Timr
import pygeoip
from collections import Counter
import datetime
from dateutil.rrule import rrule, MONTHLY
from django.utils.encoding import smart_str


class CountriesPageProcessor(HistoryPageProcessor):
    output = None
    data = None
    per_page_stats = None
    exclude_countries = None
    gi = None
    min_edits = None
    min_anon = None

    def __init__(self, **kwargs):
        super(CountriesPageProcessor, self).__init__(**kwargs)
        self.gi = pygeoip.GeoIP(kwargs["geoip"])
        self.data = {}
        self.exclude_countries = self.exclude_countries or []
        self.per_page_data = {}
        self.countries = set()
        self._skip = None
        self._country = None
        self._country_data = Counter()
        self._anon_edits = 0
        self._edits = 0

    def flush(self):
        """
        Flushes queue in the CSV output
        """
        if self.per_page_data:
            f = open(self.per_page_stats, "w")
            for item in self.per_page_data.items():
                csv_writer = csv.writer(f)
                csv_writer.writerow([item[0]] + list(item[1]))
            f.close()

        f = open(self.output, "w")
        csv_writer = csv.DictWriter(f, ["date"] + list(self.countries))
        csv_writer.writeheader()
        for date in sorted(self.data):
            to_write = Counter(date=date)
            to_write.update(dict([(x, 0) for x in self.countries]))
            to_write.update(self.data[date])
            csv_writer.writerow(to_write)
        f.close()

    def process_timestamp(self, elem):
        if self._skip:
            return
        self._date = ts2dt(elem.text)

    def process_ip(self, elem):
        if self._skip:
            return
        try:
            self._country = self.gi.country_name_by_addr(elem.text)
        except Exception:
            logging.warn("Skipping IP %s", elem.text)
        else:
            if self._country:
                self.countries.add(self._country)
            else:
                logging.warn("Can't find country for IP %s", elem.text)
                self._country = "Unknown"
                self.countries.add(self._country)

    def process_revision(self, _):
        self._edits += 1
        if not self._country:
            return

        current_date = self._date.strftime("%Y/%m")

        first_date = None  # 2001 date mismatch
        mismatch = False

        if self.data and current_date not in self.data:
            first_date = min(self.data)
            if first_date > current_date:
                mismatch = True
                logging.warn("Date mismatch! Fixing... - %s %s", first_date,
                             current_date)

        if not self.data or mismatch:  # populate dict with all dates
            start = self._date.date()
            start = datetime.date(start.year, start.month, 1)
            end = datetime.date.today()
            for dt in rrule(MONTHLY, dtstart=start, until=end):
                dt = dt.strftime("%Y/%m")
                if dt not in self.data:
                    self.data[dt] = Counter()

        self.data[current_date][self._country] += 1

        if self.per_page_stats:
            self._country_data[self._country] += 1

        self._country = None

        self._anon_edits += 1

    def process_page(self, _):
        if self.per_page_stats and \
           (not self.min_edits or
            self.min_edits <= self._edits) and \
           (not self.min_anon or
            self.min_anon <= self._anon_edits):

            output = [self._edits, self._anon_edits]
            most_common = self._country_data.most_common(5)
            if not (most_common and
                    most_common[0][0] in self.exclude_countries):
                for country, edits in most_common:
                    if edits:
                        output += [country,
                                   edits,
                                   float(edits) / float(self._anon_edits)]
                        self.per_page_data[smart_str(self._title)] = output
        self._anon_edits = 0
        self._edits = 0
        self._country_data = Counter()

        self.skip = False

    def process_title(self, elem):
        self._title = elem.text
        self.skip = False

    def process_redirect(self, elem):
        pass


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
        usage="usage: %prog [options] input_file geoip_db output_file")
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output (like timings)")
    p.add_option('-p', '--per-page', action="store",
                 dest="per_page_stats", help="Per page stats output")
    p.add_option('-e', '--min-edits', action="store", type=int,
                 dest="min_edits",
                 help="Skip if page has less than min-edit edits")
    p.add_option('-a', '--min-anon', action="store", type=int,
                 dest="min_anon",
                 help="Skip if page has less than min-anon anonymous edits")
    p.add_option('-E', '--exclude', action="store",
                 dest="exclude_countries",
                 help="Countries to exclude, colon (;) separated")
    opts, files = p.parse_args()

    if len(files) != 3:
        p.error("Wrong parameters")
    if opts.verbose:
        logging.basicConfig(stream=sys.stderr,
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

    xml = files[0]
    geoip_db = files[1]
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
                   tags='page,redirect,timestamp,ip,revision,title')
    src.close()
    src = deflate(xml)

    processor = CountriesPageProcessor(tag=tag, lang=lang,
                                       output=output,
                                       userns=translation['User'],
                                       geoip=geoip_db
                                      )
    if opts.per_page_stats:
        processor.per_page_stats = opts.per_page_stats
    if opts.exclude_countries:
        processor.exclude_countries = opts.exclude_countries.split(";")
    processor.min_edits = opts.min_edits
    processor.min_anon = opts.min_anon
    with Timr('Processing'):
        processor.start(src)  # PROCESSING
    processor.flush()


if __name__ == "__main__":
    main()

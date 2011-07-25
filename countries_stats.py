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
from collections import Counter, OrderedDict
import datetime
from dateutil.rrule import rrule, MONTHLY

class CountriesPageProcessor(HistoryPageProcessor):
    output = None
    data = None
    gi = None
    countries = set()
    csv_writer = None
    _skip = None
    _country = None

    def __init__(self, **kwargs):
        super(CountriesPageProcessor, self).__init__(**kwargs)
        self.gi = pygeoip.GeoIP(kwargs["geoip"])
        self.data = OrderedDict()

    def flush(self):
        """
        Flushes queue in the CSV output
        """
        f = open(self.output, "w")
        self.csv_writer = csv.DictWriter(f, ["date"] + list(self.countries))
        self.csv_writer.writeheader()
        for date in self.data:
            to_write = Counter(date=date) #{"date": date}
            to_write.update(dict([(x, 0) for x in self.countries]))
            to_write.update(self.data[date])
            self.csv_writer.writerow(to_write)
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
        except pygeoip.GeoIPError:
            logging.warn("Skipping IP %s", elem.text)
        self.countries.add(self._country)

    def process_contributor(self, _):
        current_date = self._date.strftime("%Y/%m")

        first_date = None  # 2001 date mismatch
        mismatch = False
        for date in self.data:
            first_date = date
            break
        if first_date and first_date > current_date:
            mismatch = True
            logging.warn("Date mismatch! Fixing... - %s %s", first_date,
                         current_date)

        if not self.data or mismatch:  # populate dict with all dates
            start = self._date.date()
            end = datetime.date.today()
            for dt in rrule(MONTHLY, dtstart=start, until=end):
                dt = dt.strftime("%Y/%m")
                if not dt in self.data:
                    self.data[dt] = Counter()

        self.data[current_date][self._country] += 1

        self._date = None
        self._country = None

    def process_page(self, _):
        pass

    def process_redirect(self, _):
        pass

    def process_title(self, _):
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
                   tags='page,redirect,timestamp,ip,contributor,title')
    src.close()
    src = deflate(xml)

    processor = CountriesPageProcessor(tag=tag, lang=lang,
                                       output=output,
                                       userns=translation['User'],
                                       geoip=geoip_db
                                      )
    with Timr('Processing'):
        processor.start(src) ## PROCESSING
    processor.flush()


if __name__ == "__main__":
    main()

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

from sonet.mediawiki import get_tags, get_translations, \
                            explode_dump_filename, _diff_text
from sonet import lib
from sonet import mediawiki as mwlib
import sys
import logging
from sonet.timr import Timr
from revisions_page import HistoryRevisionsPageProcessor, dumps_checker
from pywc import PyWC
import csv
from django.utils.encoding import smart_str
import os
from collections import Counter, defaultdict
from operator import itemgetter

class PyWC(PyWC):
    def __init__(self, dic, output):
        self.set_dic(dic)
        self.csv_out = output
        try:
            cat_names = [str(x[0]) for x in sorted([(int(a), b) for a, b in \
                                               self.categories.items()])]
        except ValueError:
            cat_names = [str(x[0]) for x in sorted(self.categories.items())]

        self._keys = ["date", "ns"] + cat_names + ["qmarks", "unique", "dic",
                                                   "sixltr", "total", "text",
                                                   "edits"]

        self.csv_writer = csv.DictWriter(self.csv_out,
                                         delimiter=self.delimiter,
                                         fieldnames=self._keys,
                                         quotechar=self.quotechar)
        self.csv_writer.writeheader()

    def save(self):
       pass


class PyWCProcessor(HistoryRevisionsPageProcessor):
    pywc = None
    namespaces = None
    data = None
    dic = None
    detailed_start = None
    detailed_end = None
    detailed_ns = None
    # revision related variables
    _username = None
    _ip = None
    _sender = None
    _skip_revision = False

    def __init__(self, **kwargs):
        super(PyWCProcessor, self).__init__(**kwargs)
        self.dic = kwargs["dic"]
        self.pywc = PyWC(self.dic, self.output)
        self.pywc.tuning = True
        self.data = {}
        self.detailed_data = {}

    def save(self):
        if self._skip_revision:
            return
        if self._text is None: # difflib doesn't like NoneType
            self._text = ""
        if self.clean:
            self._text = self.textcleaner.clean_all(self._text)
        text_words = len(self.rwords.findall(self._text))
        prev_words = len(self.rwords.findall(self._prev_text))
        if text_words < 1000 or text_words <= 2 * prev_words:
            diff = _diff_text(self._prev_text,
                              self._text,
                              timeout=self.diff_timeout)[0]
            self.pywc.parse_col(diff)
            if not self.data.has_key(self._type):
                self.data[self._type] = {}
            current = self.data[self._type]
            date_str = self._date.strftime("%Y/%m/%d")
            tmp = {"date": date_str,
                   "qmarks": self.pywc._qmarks,
                   "unique": len(self.pywc._unique),
                   "dic": self.pywc._dic,
                   "sixltr": self.pywc._sixltr,
                   "total": self.pywc._total}
            for x in self.pywc.categories:
                tmp[x] = self.pywc._results[x]

            if not current.has_key(date_str):
                current[date_str] = tmp
                current[date_str]["edits"] = 1
            else:
                for elem in tmp:
                    if elem != "date":
                        current[date_str][elem] += tmp[elem]
                current[date_str]["edits"] += 1
            del tmp

            if self.pywc.detailed and self._type == self.detailed_ns:
                date_str = self._date.strftime("%Y/%m/%d")
                if not self.detailed_data.has_key(date_str):
                    self.detailed_data[date_str] = defaultdict(dict)
                for keyword in self.pywc._detailed_data:
                    occ = self.pywc._detailed_data[keyword]
                    tmp = self.detailed_data[date_str][keyword]
                    if not tmp:
                        tmp = {}
                        tmp["total"] = 0
                        tmp["pages"] = Counter()
                        tmp["users"] = Counter()
                    tmp["total"] += occ
                    tmp["pages"][self._title] += occ
                    tmp["users"][self._sender] += occ
                    self.detailed_data[date_str][keyword] = tmp
        else:
            logging.warn("Revert detected: skipping... (%s)", self._date)
        self._prev_text = self._text

    def flush(self):
        for ns in self.data:
            for date in sorted(self.data[ns]):
                tmp = {"ns": ns, "date": date}
                tmp.update(self.data[ns][date])
                self.pywc.csv_writer.writerow(tmp)
        for date in self.detailed_data:
            filename = "%s_detailed_%s" % (self.output.name,
                                           date.replace("/", ""))
            with open(filename, "w") as f:
                detailed_csv = csv.writer(f, delimiter="\t")
                for keyword in self.detailed_data[date]:
                    current = self.detailed_data[date][keyword]
                    top_pages = sorted(current["pages"].items(),
                                       key=itemgetter(1))[:20]
                    top_users = sorted(current["users"].items(),
                                       key=itemgetter(1))[:20]
                    tmp = [keyword, current["total"], top_pages,
                           len(current["pages"]), top_users,
                           len(current["users"])]
                    detailed_csv.writerow(tmp)

    def process_page(self, _):
        self.count += 1
        if not self.count % 1000:
            logging.info(' ### Processed %d pages', self.count)
        self.delattr(("text"))
        self._skip = False

    def process_redirect(self, _):
        self._skip = True
        pass

    def process_title(self, elem):
        self.delattr(("_counter", "_type", "_title", "_skip", "_date",
                      "text", "_username", "_ip"))
        if self._skip_revision:
            return
        self._skip = False
        print elem.text
        self._title = smart_str(elem.text)
        a_title = self._title.split(':')
        if len(a_title) == 1:
            self._type = "Normal"
        else:
            self._type = a_title[0] if a_title[0] in self.namespaces \
                                    else "Normal"

    def process_timestamp(self, elem):
        if self._skip_revision:
            return
        revision_time = mwlib.ts2dt(elem.text)
        if ((self.detailed_end and revision_time > self.detailed_end) or
            (self.detailed_start and revision_time < self.detailed_start)):
            self._skip_revision = True
        else:
            self._date = revision_time
        del revision_time

    def process_contributor(self, contributor):
        if self._skip_revision:
            return

        if contributor is None:
            self._skip_revision = True
        self._sender = self._username or self._ip
        self.delattr(("_username", "_ip"))
        if not self._sender:
            self.counter_deleted += 1
            self._skip_revision = True

    def process_revision(self, _):
        skip = self._skip_revision
        self._skip_revision = False
        if skip:
            return
        self.delattr(("_username", "_ip", "_date"))
        del skip

    def process_username(self, elem):
        if self._skip_revision:
            return
        self._username = elem.text

    def process_ip(self, elem):
        if self._skip_revision:
            return
        self._ip = elem.text


def main():
    import optparse
    from sonet.lib import SonetOption

    p = optparse.OptionParser(
            usage="usage: %prog [options] input_file dictionary output_file",
            option_class=SonetOption
        )
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output (like timings)")
    p.add_option('-T', "--timeout", action="store", dest="timeout", type=float,
                 default=0.5, help="Diff timeout (default=0.5, 0=no timeout)")
    p.add_option('-c', '--clean', action="store_true", dest="clean",
                 default=False,
                 help="Cleans HTML, wiki syntax, acronyms and emoticons")
    p.add_option('-S', '--detailed-start', action="store",
        dest='detailed_start', type="yyyymmdd", metavar="YYYYMMDD",
        default=None, help="Detailed output start date")
    p.add_option('-E', '--detailed-end', action="store",
        dest='detailed_end', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Detailed output end date")
    p.add_option('-n', '--detailed-namespace', action="store",
                 dest="detailed_ns", default="Normal",
                 help="Namespace of desired detailed data (default: Normal)")
    opts, files = p.parse_args()

    if len(files) != 3:
        p.error("Wrong parameters")
    if opts.verbose:
        logging.basicConfig(stream=sys.stderr,
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

    xml = files[0]
    dic = files[1]
    output = files[2]

    dumps_checker(xml)

    lang, _, _ = explode_dump_filename(xml)
    deflate, _lineno = lib.find_open_for_this_file(xml)

    if _lineno:
        src = deflate(xml, 51)
    else:
        src = deflate(xml)

    translation = get_translations(src)
    tag = get_tags(src, tags=('page,title,revision,timestamp,text,redirect,'
                              'contributor,username,ip'))
    namespaces = [x[1] for x in [(0, "Normal")] + mwlib.get_namespaces(src)]
    src.close()
    src = deflate(xml)

    if os.path.exists(output):
        logging.error("File %s already exists!", output)
        sys.exit(0)

    out = open(output, 'w')
    processor = PyWCProcessor(tag=tag, lang=lang, dic=dic,
                              output=out, userns=translation['User'])
    processor.namespaces = namespaces
    processor.diff_timeout = opts.timeout
    processor.clean = opts.clean
    processor.pywc.clean_wiki = processor.pywc.clean_html = opts.clean
    if opts.detailed_start and opts.detailed_end:
        print """
        You are going to run the script with detailed output on %d days.
        This is going to produce some CSV files on your disk, one for each
        day. Is this want you really want to do? [press enter to continue]
        """ % (opts.detailed_end - opts.detailed_start).days
        raw_input()
        processor.pywc.detailed = True
        processor.detailed_start = opts.detailed_start
        processor.detailed_end = opts.detailed_end
        processor.detailed_ns = opts.detailed_ns

    with Timr('Processing'):
        processor.start(src) ## PROCESSING
    processor.flush()
    out.close()


if __name__ == "__main__":
    main()

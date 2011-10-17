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
                                                   "sixltr", "total", "text"]

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

    def __init__(self, **kwargs):
        super(PyWCProcessor, self).__init__(**kwargs)
        self.dic = kwargs["dic"]
        self.pywc = PyWC(self.dic, self.output)
        self.data = {}

    def save(self):
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
            date = mwlib.ts2dt(self._date)
            date_str = date.strftime("%Y/%m/%d")
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
            else:
                for elem in tmp:
                    if elem != "date":
                        current[date_str][elem] += tmp[elem]
            del tmp
        else:
            logging.warn("Revert detected: skipping... (%s)", self._date)
        self._prev_text = self._text

    def flush(self):
        for line in self.data:
            for date in sorted(self.data[line]):
                tmp = {"ns": line, "date": date}
                tmp.update(self.data[line][date])
                self.pywc.csv_writer.writerow(tmp)

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
        self.delattr(("_counter", "_type", "_title", "_skip", "_date", "text"))
        self._skip = False
        print elem.text
        a_title = elem.text.split(':')
        if len(a_title) == 1:
            self._type = "Normal"
        else:
            self._type = a_title[0] if a_title[0] in self.namespaces \
                                    else "Normal"

def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] input_file dictionary output_file")
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
    p.add_option('-C', '--charlimit', action="store", dest="charlimit",
                 type="int", default=100000,
                 help="Maximim characters per line (default=100000)")
    p.add_option('-r', action="store_true", dest="regex", default=False,
                 help="Use a dictionary composed by regex (default=false)")
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
    tag = get_tags(src, tags='page,title,revision,timestamp,text,redirect')
    namespaces = [x[1] for x in [(0, "Normal")] + mwlib.get_namespaces(src)]
    src.close()
    src = deflate(xml)

    out = open(output, 'w')
    processor = PyWCProcessor(tag=tag, lang=lang, dic=dic,
                              output=out, userns=translation['User'])
    processor.namespaces = namespaces
    if opts.type == 'talk':
        processor.get_articles = False
    elif opts.type == 'content':
        processor.get_talks = False
    processor.diff_timeout = opts.timeout
    processor.clean = opts.clean
    processor.pywc.clean_wiki = processor.pywc.clean_html = opts.clean

    with Timr('Processing'):
        processor.start(src) ## PROCESSING
    processor.flush()
    out.close()


if __name__ == "__main__":
    main()

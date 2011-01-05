#!/usr/bin/env python

##########################################################################
#                                                                        #
# Copyleft Federico "fox" Scrinzi (fox91 at anche dot no)                #
#                                                                        #
# pyWC is free software; you can redistribute it and/or modify           #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation; version 2 of the License.                #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           #
# GNU General Public License for more details.                           #
#                                                                        #
##########################################################################

import csv
import sys
try:
    import re2 as re
except ImportError:
    logging.warn("pyre2 not available. It's gonna be a long job")
    import re
import logging
from sonet.timr import Timr

class PyWC:
    # Global proprieties (of the whole source file)
    categories = None
    keywords = None
    delimiter = "\t"
    queue = []
    max_char_limit = None
    csv_writer = None

    # Local proprieties (of every column of the source file)
    _id = None        # Line ID
    _results = None   # Dictionary where keys are cat ids and
                      # values are counters
    _total = None     # List of numbers of total words per column
    _text = None      # Current text to analize
    _counter = 0

    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def delattrs(self, attrs):
        for attr in attrs:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def _gen_keyword(self, content):
        for line in content[2].split("\n")[1:-1]:
            line = line.split("\t")
            # it fixes the keyword for regex
            # "^" is added at the beginning of every keyword
            # if keyword doesn't ends with * a "$" is added
            # bad -> ^bad$ matches "bad" but not "badass"
            # bad* -> ^bad matches "bad" and "badass"
            line[0] = "".join(["^", line[0]])
            try:
                if (line[0][-1] == "*"):
                    line[0] = line[0][:-1]
                else:
                    line[0] = "".join([line[0], "$"])
                yield (re.compile(line[0]), line[1:])
            except:
                pass

    def set_dic(self, dic):
        f = open(dic, 'r')
        content = f.read()
        content = content.split("%")
        if len(content) != 3:
            raise ValueError("Invalid dic file")

        # Creates a dictionary where category ids are the keys
        # and category names are the values.
        # Splits content at first by new line, then by tab
        self.categories = dict([line.split("\t") \
                for line in content[1].split("\n")[1:-1]])

        # Creates a dictionary where the compiled regex is the key
        # and category ids are the values
        self.keywords = dict(x for x in self._gen_keyword(content))

    def flush(self):
        self.csv_writer.writerows(self.queue)
        self.queue = []

    def save(self):
        tmp = {"id": self._id,
               "total": self._total,
               "text": self._text}
        # Join of self.categories and self._results values
        for k, v in ((self.categories[x], self._results[x]) \
                     for x in self.categories):
            tmp[k] = v
        self.queue.append(tmp)
        del tmp
        self._counter += 1
        if self._counter % 100 == 0:
            logging.info("Flushing: revision %d" % self._counter)
            self.flush()

    def parse_word(self, word):
        for regex in self.keywords:
            if regex.search(word):
                for i in self.keywords[regex]:
                    try:
                        self._results[i] += 1
                    # If dictionary contains trailing tabs,
                    # '' keys are returned. Skipping them.
                    except KeyError:
                        pass
        self._total += 1

    def parse_col(self, col):
        self.delattrs(("_results", "_total", "_text"))
        self._text = col
        self._results = {}
        for k in self.categories:
            self._results[k] = 0
        self._total = 0
        rwords = re.compile("[\w']+")
        for word in rwords.findall(col):
        #with Timr("Parsing word %s" % word):
            if not word.isdigit():  # Skip numbers, count words only
                self.parse_word(word)
        #with Timr("Saving..."):
        self.save()

    def parse_line(self, line):
        self.delattrs(("_id"))
        self._id = line[0]
        #logging.info("Start processing %s" % self._id)
        for col in line[1:]:
            if len(col) <= self.max_char_limit:
                #with Timr("Processing revision %s" % self._id):
                self.parse_col(col)
            else:
                logging.info("Warning: Line %d skipped \
                              because longer than %d chars" % \
                              (self.max_char_limit, self._counter))

    def start(self, src):
        self._keys = ["id"] + self.categories.values() + ["total", "text"]
        self.csv_writer = csv.DictWriter(sys.stdout,
                                         delimiter=self.delimiter,
                                         fieldnames=self._keys)
        self.csv_writer.writeheader()
        csv_reader = csv.reader(src, delimiter=self.delimiter)
        for line in csv_reader:
            self.parse_line(line)


def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] dic_file input_file")
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output (like timings)")
    p.add_option('-c', '--charlimit', action="store", dest="charlimit",
                 type="int", default=100000,
                 help="Maximim characters per line (default=100000)")
    opts, files = p.parse_args()
    if len(files) != 2:
        p.error("Wrong parameters")

    if opts.verbose:
        logging.basicConfig(stream=sys.stderr,
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')

    t = PyWC()
    t.max_char_limit = opts.charlimit
    t.set_dic(files[0])
    src = open(files[1], 'r')
    with Timr("Processing"):
        t.start(src)
    t.flush()


if __name__ == "__main__":
    main()

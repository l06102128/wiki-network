#!/usr/bin/env python

########################################################################
#                                                                      #
# Copyleft Federico "fox" Scrinzi (fox91 at anche dot no)              #
#                                                                      #
# pyWC is free software; you can redistribute it and/or modify         #
# it under the terms of the GNU General Public License as published by #
# the Free Software Foundation; version 2 of the License.              #
#                                                                      #
# pyWC program is distributed in the hope that it will be useful,      #
# but WITHOUT ANY WARRANTY; without even the implied warranty of       #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the         #
# GNU General Public License for more details.                         #
#                                                                      #
########################################################################

import csv
csv.field_size_limit(100000000)
import sys
import logging
try:
    import re2 as re
except ImportError:
    logging.warn("pyre2 not available. It's gonna be a long job")
    import re
from sonet.timr import Timr


class PyWC:
    """
    PyWC is a python class for word counting and text analisys.
    """
    # Global proprieties (of the whole source file)
    categories = None        # Dictionary's categories
    keywords = None          # Dictionary's keywords/regex
    delimiter = "\t"         # CSV delimiter
    quotechar = '"'          # CSV quotechar
    csv_out = sys.stdout     # CSV output
    queue = []               # Flushing queue
    max_char_limit = 100000  # Max chars per line
    ignorecols = []          # List of columns of the src file to ignore
    csv_writer = None        # Csv writer handler
    id_col = 0               # Number of the id column
    dic_regex = False        # Use dictionary made of regex
    flush_n = 100            # Number of pieces of text to store
    clean_wiki = True        # Clean wiki syntax
    clean_html = True        # Clean HTML

    clean_regex = (
        (re.compile(r"(^|\s)(\w\.)+"), ""),
        (re.compile(r"[\:|;|8|=|-]+[a-z](\s|$)", re.IGNORECASE), ""))

    # TODO TODO TODO TODO TODO
    clean_wiki_regex = (
        (re.compile(r"(?:https?://)(?:[\w]+\.)(?:\.?[\w]{2,})+(\S+)?"), ""),
        (re.compile(r"\[{1,2}([^\:\|]+?)\]{1,2}", re.DOTALL), r"\1"),
        (re.compile(r"\[{1,2}.+?[\||\:]([^\|^\:]+?)\]{1,2}",
                    re.DOTALL), r"\1"),
        (re.compile(r"\[{1,2}.+?\]{1,2}", re.DOTALL), ""),
        (re.compile(r"\{{1,3}.+?\}{1,3}", re.DOTALL), ""),
        #(re.compile(r"[\w|\s]+:\w+(.+?\])?", re.U), ""))
        (re.compile(r"\|(.+)?(\s+?)?=(\s+?)?(.+)?"), ""))

    # Stripping HTML tags and comments
    clean_html_regex = ((re.compile(r"<\!--.+?-->", re.DOTALL), ""),
                        (re.compile(r"<.+?>"), ""),
                        (re.compile(r"\&\w+;"), ""))

    cond_exp_regex = (re.compile(r"<([\w']+)>(\w+)(\/(\w+)?)?"),
                      re.compile(r"\(([\w\s]+)\)(\w+)(\/(\w+)?)?"))

    # Local proprieties (of every column of the source file)
    _id = None         # Line ID
    _results = None    # Dictionary where keys are cat ids and
                       # values are counters
    _total = None      # List of numbers of total words per column
    _text = None       # Current text to analize
    _next_word = None  # Next word that has to be analized
    _prev_cat = None   # Categories of the last word that has been analized
                       # (useful for conditional exps)
    _counter = 0       # Generic counter of how many pieces of
                       # text have been analized
    _keys = None

    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def delattrs(self, attrs):
        """
        Frees memory deleting useless attributes of the object
        """
        for attr in attrs:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def _gen_keyword(self, content):
        """
        Generator for self.keywords (dictionary made of of regexps
        as keys and thier categories as values)
        """
        for line in content[2].split("\n")[1:-1]:
            # Comments start with //
            if line and not line.startswith("//"):
                line = line.split("\t")
                # If not using a dictionary made of regexps
                # it fixes the keyword for regexping
                # "^" is added at the beginning of every keyword
                # If keyword doesn't ends with "*", a "$" is added
                # bad -> ^bad$ matches "bad" but not "badass"
                # bad* -> ^bad matches "bad" and "badass"
                if not self.dic_regex:
                    line[0] = "".join(["^", line[0]])
                    try:
                        if (line[0][-1] == "*"):
                            line[0] = line[0][:-1]
                        else:
                            line[0] = "".join([line[0], "$"])
                    except IndexError:
                        continue
                yield (re.compile(line[0]), line[1:])

    def set_dic(self, dic):
        """
        Receives as input the dictionary filename.
        Reads the dictionary file and populates self.categories and
        self.keywords
        """
        f = open(dic, 'r')
        content = f.read()
        content = content.split("%")
        if len(content) != 3:
            raise ValueError("Invalid dic file")

        # Creates a dictionary where category ids are the keys
        # and category names are the values.
        # Splits content at first by new line, then by tab
        self.categories = dict((line.split("\t") \
                for line in content[1].split("\n")[1:-1] if line))

        # Creates a dictionary where the compiled regex is the key
        # and category ids are the values
        self.keywords = dict(x for x in self._gen_keyword(content))

    def flush(self):
        """
        Writes everything which is in the queue in the csv output file
        """
        self.csv_writer.writerows(self.queue)
        self.queue = []

    def save(self):
        """
        Saves current piece of text that has been analized to the queue
        """
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
        if self._counter % self.flush_n == 0:
            logging.info("### Flushing: %d", self._counter)
            self.flush()

    def parse_word(self, word):
        """
        Parses a single word with the dictionary of regexps
        (self.keywords). For every regex that matches, it
        increments every category they belong to in self._result
        """
        cat = []
        for regex in self.keywords:
            if regex.search(word):
                for i in self.keywords[regex]:
                    res = self.cond_exp_regex[0].match(i)
                    if res:
                        if self._next_word == res.group(1):
                            cat.append(res.group(2))
                        elif res.group(4):
                            cat.append(res.group(4))
                        continue

                    res = self.cond_exp_regex[1].match(i)
                    if res:
                        if True in [c in self._prev_cat \
                                    for c in res.group(1).split(" ")]:
                            cat.append(res.group(2))
                        elif res.group(4):
                            cat.append(res.group(4))
                        continue

                    # If dictionary contains trailing tabs,
                    # '' keys are saved. It skips them.
                    if i:
                        cat.append(i)

        for c in cat:
            try:
                self._results[c] += 1
            except KeyError:
                logging.warn("Invalid category id %s", c)
        self._total += 1
        self._prev_cat = cat

    def clean_wiki_syntax(self):
        """
        Cleans self._text from wiki syntax
        """
        # TODO FILTER WIKI SYNTAX
        for regex, replace in self.clean_wiki_regex:
            self._text = regex.sub(replace, self._text)

    def clean_html_syntax(self):
        """
        Cleans self._text from HTML tags and comments
        """
        for regex, replace in self.clean_html_regex:
            self._text = regex.sub(replace, self._text)

    def clean_text(self):
        """
        Cleans self._text from emoticons and acronyms
        """
        for regex, replace in self.clean_regex:
            self._text = regex.sub(replace, self._text)

    def parse_col(self, col):
        """
        Reads a single cell of the csv file. It splits it
        into words and gives them to self.parse_word
        """
        self.delattrs(("_results", "_total", "_text",
                       "_prev_word", "_prev cat"))
        self._text = col
        logging.info("--------PRIMA-----------")
        logging.info(self._text)
        logging.info("-------------------")
        self.clean_text()
        if self.clean_wiki:
            self.clean_wiki_syntax()
        if self.clean_html:
            self.clean_html_syntax()
        logging.info("--------DOPO------------")
        logging.info(self._text)
        logging.info("-------------------")
        self._results = {}
        for k in self.categories:
            self._results[k] = 0
        self._total = 0
        rwords = re.compile("[\w']+")
        # create a list of words (_no_ numbers)
        words = [word for word in rwords.findall(col) if not word.isdigit()]
        for i, word in enumerate(words):
            try:
                self._next_word = words[i+1]
            except IndexError:
                self._next_word = ""
            self.parse_word(word)
        self.save()

    def parse_line(self, line):
        """
        Reads a single line of the csv file.
        Sets self._id and gives the cells that are not in the ignore
        list to self.parse_col
        """
        self.delattrs(("_id"))
        self._id = line[self.id_col]
        for i, col in enumerate(line):
            if len(col) <= self.max_char_limit:
                if i != self.id_col and not i in self.ignorecols:
                    self.parse_col(col)
            else:
                logging.warn(" Line %d:%d skipped "
                             "because longer than %d chars",
                             self._counter, i, self.max_char_limit)

    def start(self, src):
        """
        It starts the file processing.
        To obtain a sensible output is recommended to run self.set_dic()
        before.
        It writes the output csv header and reads every line, passing
        it to self.parse_line
        """

        # Creates a list of category names sorted by their ID.
        # Useful because Python dictionaries are not sorted objects!
        # Sorting like TAWC
        try:
            cat_names = [x[1] for x in sorted([(int(a), b) for a, b in \
                                               self.categories.items()])]
        except ValueError:
            cat_names = [x[1] for x in sorted(self.categories.items())]

        self._keys = ["id"] + cat_names + ["total", "text"]
        self.csv_writer = csv.DictWriter(self.csv_out,
                                         delimiter=self.delimiter,
                                         fieldnames=self._keys,
                                         quotechar=self.quotechar)
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
    p.add_option('-i', '--ignorecols', action="store", dest="ignorecols",
                 help="Coulmns numbers of the source file to ignore" + \
                      "(comma separated and starting from 0)")
    p.add_option('-I', '--id', action="store", dest="id_col", type="int",
                 help="Id column number (starting from 0)", default=0)
    p.add_option('-r', action="store_true", dest="regex", default=False,
                 help="Use a dictionary composed by regex (default=false)")
    p.add_option('-f', "--flush", action="store", dest="flush", type="int",
                 default=100,
                 help="Flushing to output every N pieces of text")
    p.add_option('-o', "--output", action="store", dest="output",
                 help="Output file (default=STDOUT)")
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
    if opts.ignorecols:
        t.ignorecols = [int(x) for x in opts.ignorecols.split(",")]
    t.id_col = opts.id_col
    t.dic_regex = opts.regex
    t.flush_n = opts.flush
    if opts.output is not None:
        t.csv_out = open(opts.output, 'w')

    t.set_dic(files[0])
    src = open(files[1], 'r')
    with Timr("Processing"):
        t.start(src)

    t.flush()


if __name__ == "__main__":
    main()

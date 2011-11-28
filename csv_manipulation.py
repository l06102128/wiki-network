#!/usr/bin/env python

##########################################################################
#                                                                        #
#  This program is free software; you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation; version 2 of the License.               #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#  GNU General Public License for more details.                          #
#                                                                        #
##########################################################################


"""
Simple script useful to cut or extract only specific pages from
the output of revisions_page.py
"""

import csv
from sys import stdout
from datetime import datetime as dt
import re

RWORDS = re.compile(r"\S+")


def words(text):
    return [word for word in RWORDS.findall(text)]


def get_stats(opts, files):
    csv_reader = csv.reader(open(files[0], 'r'),
                            delimiter=opts.delimiter,
                            quotechar=opts.quotechar,
                            quoting=csv.QUOTE_ALL)
    pages = set()
    counter = 0
    for line in csv_reader:
        pages.add((line[2], line[3]))
        counter += 1
    return {"pages": pages, "lines": counter}


def write_to_file(csv_writer, line, columns):
    if not columns:
        csv_writer.writerow(line)
    else:
        result = []
        for c in columns.split(","):
            result.append(line[int(c)])
        csv_writer.writerow(result)


def extract_page(opts, files, output=stdout):
    # CSV handlers
    csv_reader = csv.reader(open(files[0], 'r'),
                            delimiter=opts.delimiter,
                            quotechar=opts.quotechar,
                            quoting=csv.QUOTE_ALL)
    csv_writer = csv.writer(output,
                            delimiter=opts.delimiter,
                            quotechar=opts.quotechar,
                            quoting=csv.QUOTE_ALL)
    # Print only intresting lines!
    # Really ugly but doesn't eat memory
    i = 0
    queue = None
    for k, line in enumerate(csv_reader):
        if k < opts.start_line:
            continue
        if opts.header and k == 0:
            write_to_file(csv_writer, line, opts.columns)
            continue
        if opts.lines is not None and i >= opts.lines:
            break
        current_time = dt.strptime(line[0], "%Y-%m-%dT%H:%M:%SZ")
        if (opts.page is None or line[2] == opts.page) and \
           (opts.type is None or line[3] == opts.type) and \
           (not opts.start or current_time > opts.start) and \
           (not opts.end or current_time < opts.end):
            i += 1
            if opts.words_window:
                if not queue:
                    #print "INITIALIZING QUEUE"
                    queue = line[:]
                    queue[-1] = ""
                len_queue = len(words(queue[-1]))
                counter = 0
                for w in words(line[-1]):
                    counter += 1
                    queue[-1] += " " + w
                    #print "ADD WORD", queue[-1], len_queue+counter
                    if len_queue + counter >= opts.words_window:
                        #print "FLUSH QUEUE"
                        write_to_file(csv_writer, queue, opts.columns)
                        queue = line[:]
                        queue[-1] = ""
                        len_queue = 0
                        counter = 0
                if len_queue == 0 and counter == 0:
                    queue = None
            else:
                write_to_file(csv_writer, line, opts.columns)
    if queue:
        write_to_file(csv_writer, queue, opts.columns)


def main():
    import optparse
    from sonet.lib import SonetOption

    # Parameters
    p = optparse.OptionParser(usage="usage: %prog [options] file",
                              option_class=SonetOption)
    p.add_option('-c', '--columns', action="store", dest="columns",
                 help="Columns to output")
    p.add_option('-d', '--delimiter', action="store", dest="delimiter",
                 default="\t", help="CSV delimiter")
    p.add_option('-q', '--quotechar', action="store", dest="quotechar",
                 default='"', help="CSV quotechar")
    p.add_option('-l', '--lines', action="store", dest="lines",
                 type="int", help="Number of lines to print")
    p.add_option('-p', '--page', action="store", dest="page",
                 help="Select a specific page")
    p.add_option('-t', '--type', action="store", dest="type",
                 help="Select a specific page type (normal|talk)")
    p.add_option('-i', '--info', action="store_true", dest="info",
                 help="Get info about CSV file")
    p.add_option('-S', '--start-line', action="store", dest="start_line",
                 type="int", help="Skip lines before START_LINE")
    p.add_option('-w', '--words-window', action="store", dest="words_window",
                 type="int", help="Set a word window")
    p.add_option('-H', '--header', action="store_true", dest="header",
                 help="Output header")
    p.add_option('--split', action="store_true", dest="split_file",
                 help="Split csv into different files, one per page")
    p.add_option('-s', '--start', action="store",
        dest='start', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions starting from this date")
    p.add_option('-e', '--end', action="store",
        dest='end', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions until this date")
    opts, files = p.parse_args()
    if len(files) != 1:
        p.error("Wrong parameters")

    csv.field_size_limit(1000000000)  # Used for big cells, prevents exception

    # If needed prints info and exits
    if opts.info:
        stats = get_stats(opts, files)
        print "CSV info:"
        print "Number of lines: %d" % stats["lines"]
        print "\nPages: "
        print "\n".join(["%s (%s)" % (p[0], p[1]) for p in stats["pages"]])
    elif opts.split_file:
        stats = get_stats(opts, files)
        for page in stats["pages"]:
            fn = "%s-%s_%s.csv" % (files[0].split(".csv")[0], page[0], page[1])
            opts.page, opts.type = page
            extract_page(opts, files, open(fn, "w"))
    else:
        extract_page(opts, files)


if __name__ == '__main__':
    main()

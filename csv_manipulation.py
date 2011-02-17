#!/usr/bin/env python
"""
Simple script useful to cut or extract only specific pages from
the output of revisions_page.py
"""

import csv
from sys import stdout
from sonet.lib import yyyymmdd_to_datetime
from datetime import datetime as dt
import re

RWORDS = re.compile(r"\S+")

def words(text):
    return [word for word in RWORDS.findall(text)]

def main():
    import optparse
    from sonet.lib import SonetOption

    # Parameters
    p = optparse.OptionParser(usage="usage: %prog [options] file",
                              option_class=SonetOption)
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
    p.add_option('-s', '--start', action="store",
        dest='start', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions starting from this date")
    p.add_option('-e', '--end', action="store",
        dest='end', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions until this date")
    opts, files = p.parse_args()
    if len(files) != 1:
        p.error("Wrong parameters")

    # CSV handlers
    csv_reader = csv.reader(open(files[0], 'r'),
                            delimiter=opts.delimiter,
                            quotechar=opts.quotechar,
                            quoting=csv.QUOTE_ALL)
    csv_writer = csv.writer(stdout,
                            delimiter=opts.delimiter,
                            quotechar=opts.quotechar,
                            quoting=csv.QUOTE_ALL)
    csv.field_size_limit(1000000000)  # Used for big cells, prevents exception

    # If needed prints info and exits
    if opts.info:
        counter = 0
        for line in csv_reader:
            counter += 1
        print "CSV info:"
        print "Number of lines: %d" % counter
        exit(0)

    # Print only intresting lines!
    # Really ugly but doesn't eat memory
    i = 0
    queue = None
    for k, line in enumerate(csv_reader):
        if k < opts.start_line:
            continue
        if opts.header and k == 0:
            csv_writer.writerow(line)
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
                        csv_writer.writerow(queue)
                        queue = line[:]
                        queue[-1] = ""
                        len_queue = 0
                        counter = 0
                if len_queue == 0 and counter == 0:
                    queue = None

                """
                wline = words(line[-1])
                if len(wline) < opts.words_window:
                    if not queue:
                        # If queue is empty set initial value
                        print "SETTING INITIAL QUEUE = LINE"
                        queue = line
                    else:
                        #if len(words(queue[-1])) + len(wline) < opts.words_window:
                        print "ADDING TEXT TO QUEUE"
                        # add revision to queue
                        queue[-1] += " " + " ".join(wline)
                else:
                    # If revision is too big leave it as its
                    print "OUTPUTTING QUEUE AND LINE!"
                    if queue:
                        csv_writer.writerow(queue)
                        queue = None
                        i += 1
                    csv_writer.writerow(line)
                    i += 1
                """
            else:
                csv_writer.writerow(line)
    if queue:
        csv_writer.writerow(queue)

    # hungry of memory
    """
    if opts.page is not None:
        out = [line for line in csv_reader if line[2] == opts.page]
    else:
        out = [line for line in csv_reader]
    l = len(out)
    if opts.lines > 0 and opts.lines <= len(out):
        l = opts.lines
    for e in out[:opts.lines]:
        csv_writer.writerow(e)
    """

if __name__ == '__main__':
    main()

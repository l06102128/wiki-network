#!/usr/bin/env python

import matplotlib
matplotlib.use("pdf")
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import matplotlib.dates as md
from datetime import datetime as dt
from datetime import timedelta
import csv
import numpy as np
import sys
import logging
from sonet.timr import Timr

# Quite ugly, if it's possible use groupby
# [list(e) for k,e in groupby([11,12,13,21],(lambda x : x//10 ))]
def collapse_values(timestamps, values, totals, radius):
    """
    Function that collapses timestamps and values in a time window

    >>> t = [dt(2011, 01, 20, 0, 0), dt(2011, 01, 20, 0, 0), \
             dt(2011, 01, 22, 0, 0), dt(2011, 01, 23, 0, 0), \
             dt(2011, 01, 28, 0, 0), dt(2011, 01, 30, 0, 0), \
             dt(2011, 01, 31, 0, 0)]
    >>> v = [1,2,3,4,5,6,7]
    >>> tot = [2,3,4,5,6,7, 8]
    >>> collapse_values(t, v, tot, 2)
    ([datetime.datetime(2011, 1, 20, 0, 0), datetime.datetime(2011, 1, 23, 0, 0), datetime.datetime(2011, 1, 28, 0, 0), datetime.datetime(2011, 1, 31, 0, 0)], [3, 7, 5, 13], [5, 9, 6, 15])
    >>> collapse_values(t, v, tot, 4)
    ([datetime.datetime(2011, 1, 23, 0, 0), datetime.datetime(2011, 1, 31, 0, 0)], [10, 18], [14, 21])
    >>> collapse_values(t, v, tot, 999)
    ([datetime.datetime(2011, 1, 31, 0, 0)], [28], [35])
    """
    if not radius > 0:
        raise ValueError("Radius must be > 0")
    time = []
    ser = []
    tot = []
    delta = timedelta(days=radius)
    first = timestamps[0]
    curr = []
    i = 0
    for j in timestamps:
        if (j - first) < delta:
            curr.append(j)
        else:
            try:
                time.append(curr[-1])  # Use last timestamp of the group
                # Sum values and totals of the current group
                ser.append(sum(values[i-len(curr):i]))
                tot.append(sum(totals[i-len(curr):i]))
            except IndexError:
                time.append(j)
                ser.append(values[i])
                tot.append(totals[i])
            curr = [j]
            first = j
        i += 1
    time.append(curr[-1])
    ser.append(sum(values[i-len(curr):i]))
    tot.append(sum(totals[i-len(curr):i]))
    return time, ser, tot

def _gen_data(line, id_col, ignorecols, onlycols):
    """
    Generator to extract only desired columns from csv content
    """
    for i, elem in enumerate(line):
        if i != id_col and \
           (not ignorecols or not i in ignorecols) and \
           (not onlycols or i in onlycols) and \
           i != len(line) - 1 and  \
           i != len(line) - 2: # don't count last two cols
            yield elem

def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] input_file output_file")
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output")
    p.add_option('-i', '--ignorecols', action="store", dest="ignorecols",
                 help="Coulmns numbers of the source file to ignore" + \
                      "(comma separated and starting from 0)")
    p.add_option('-I', '--id', action="store", dest="id_col", type="int",
                 help="Id column number (starting from 0)", default=0)
    p.add_option('-o', '--onlycols', action="store", dest="onlycols",
                 help="Select only this set of columns" + \
                      "(comma separated and starting from 0)")
    p.add_option('-p', '--percentages', action="store_true", dest="perc",
                 help="Use percentages instead of absolute value")
    p.add_option('-w', '--window', action="store", dest="window", type=int,
                 help="Collapse days")
    opts, files = p.parse_args()

    if len(files) != 2:
        p.error("Wrong parameters")
    if opts.verbose:
        logging.basicConfig(stream=sys.stderr,
                            level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
    csv_reader = csv.reader(open(files[0]), delimiter="\t")
    onlycols = None
    ignorecols = None
    if opts.onlycols:
        onlycols = [int(x) for x in opts.onlycols.split(",")]
    if opts.ignorecols:
        ignorecols = [int(x) for x in opts.ignorecols.split(",")]

    # content contains all the csv file
    content = [row for i, row in enumerate(csv_reader)]
    # CSV header, only of interesting columns
    header = [x for x in _gen_data(content[0], opts.id_col,
                                   ignorecols, onlycols)]

    # Creates a matrix (list) with percentages of the occurrencies of every
    # category. Don't count id, total, text, ignore columns. If onlycols is set
    # consider only them.
    mat = []
    timestamps = []
    totals = []

    for line in content[1:]:
        mat.append([x for x in _gen_data(line, opts.id_col,
                                         ignorecols, onlycols)])
        totals.append(float(line[-2]))
        timestamps.append(dt.strptime(line[opts.id_col],
                          "%Y-%m-%dT%H:%M:%SZ"))

    mat = np.array(mat, dtype=np.float).transpose()
    logging.info("Input file read. Ready to plot")
    pdf_pag = PdfPages(files[1])

    with Timr("Plotting"):
        for i, series in enumerate(mat):
            logging.info("Plotting page %d", i+1)
            plt.clf()
            plt.subplots_adjust(bottom=0.2)
            plt.xticks(rotation=25)
            axis = plt.gca()
            xfmt = md.DateFormatter('%Y-%m-%d')
            axis.xaxis.set_major_formatter(xfmt)
            #axis.yaxis.set_data_interval(0.0001, None, False)
            plt.xlabel("Revisions Timestamp")

            # Don't plot zeros and skip zero revisions!
            ser = [x for x in series if x != 0]
            time = [x for k, x in enumerate(timestamps) if series[k] != 0]
            tot = [x for k, x in enumerate(totals) if series[k] != 0]

            if opts.window and time and ser and tot:
                time, ser, tot = collapse_values(time, ser, tot,
                                                   opts.window)

            if opts.perc:
                # Calculate percentages
                ser = [x/tot[k]*100 for k, x in enumerate(ser)]
                # Set axis limit 0-100 IS IT GOOD OR BAD?
                #axis.set_ylim(0, 100)
                plt.ylabel("%")

            if time and ser:
                plt.plot(matplotlib.dates.date2num(time), ser, "-o")
                plt.title(header[i])
                pdf_pag.savefig()
        pdf_pag.close()

if __name__ == "__main__":
    main()

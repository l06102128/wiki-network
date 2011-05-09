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
from sonet.mediawiki import ts2dt

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
        if (j.date() - first.date()) < delta:
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
           i != len(line) - 1 and \
           i != len(line) - 2: # don't count last two cols
            yield elem

def calc_perc(x, tot):
    try:
        return float(x) / float(tot)
    except ZeroDivisionError:
        return 0

def main():
    import optparse
    from sonet.lib import SonetOption
    p = optparse.OptionParser(
        usage="usage: %prog [options] input_file output_file",
        option_class=SonetOption)
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output")
    p.add_option('-i', '--ignorecols', action="store", dest="ignorecols",
                 help="Coulmns numbers of the source file to ignore"
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
    p.add_option('-s', '--start', action="store",
        dest='start', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions starting from this date")
    p.add_option('-e', '--end', action="store",
        dest='end', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions until this date")
    p.add_option('-d', '--dic', action="store_true", dest="dic", default=False,
                 help="Calculate percentage over dic column instead of total")
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
    content = [row for row in csv_reader]

    # CSV header, only of interesting columns
    header = [x for x in _gen_data(content[0], opts.id_col,
                                   ignorecols, onlycols)]

    # Creates a matrix (list) with percentages of the occurrencies of every
    # category. Don't count id, total, text, ignore columns. If onlycols is set
    # consider only them.
    mat = []
    timestamps = []
    totals = []
    tot_index = -2
    if opts.dic:
        tot_index = -4

    for line in content[1:]:
        mat.append([x for x in _gen_data(line, opts.id_col,
                                         ignorecols, onlycols)])
        totals.append(float(line[tot_index]))
        timestamps.append(ts2dt(line[opts.id_col]))
    del content

    mat = np.array(mat, dtype=np.float).transpose()
    logging.info("Input file read. Ready to plot")
    pdf_pag = PdfPages(files[1])

    with Timr("Plotting"):
        for i, series in enumerate(mat):
            logging.info("Plotting page %d", i+1)

            # Don't plot zeros and skip zero revisions!
            #ser = [x for x in series if x != 0]
            #time = [x for k, x in enumerate(timestamps) if series[k] != 0]
            #tot = [x for k, x in enumerate(totals) if series[k] != 0]
            ser = [x for k, x in enumerate(series) \
                   if (not opts.start or timestamps[k] >= opts.start) and \
                      (not opts.end or timestamps[k] <= opts.end)]
            time = [x for k, x in enumerate(timestamps) \
                    if (not opts.start or x >= opts.start) and \
                       (not opts.end or x <= opts.end)]
            tot = [x for k, x in enumerate(totals) \
                   if (not opts.start or timestamps[k] >= opts.start) and \
                      (not opts.end or timestamps[k] <= opts.end)]

            if opts.window and len(time) and len(ser) and len(tot):
                time, ser, tot = collapse_values(time, ser, tot,
                                                 opts.window)

            mean = float(sum(series)) / len(series)
            if opts.perc:
                # Calculate percentages
                ser = [calc_perc(x, tot[k]) for k, x in enumerate(ser)]
                # Set axis limit 0-1 IS IT GOOD OR BAD?
                #axis.set_ylim(0, 1)
                plt.ylabel("%")
                try:
                    mean = float(sum(series)) / sum(totals)
                except ZeroDivisionError:
                    mean = 0

            first_time = time[0].date()
            last_time = time[-1].date()
            plt.clf()
            plt.subplots_adjust(bottom=0.25)
            plt.xticks(rotation=90)
            fig = plt.gcf()
            fig.set_size_inches(11.7, 8.3)
            axis = plt.gca()
            axis.xaxis.set_major_formatter(md.DateFormatter('%Y-%m-%d'))
            axis.set_xlim(matplotlib.dates.date2num(first_time),
                          matplotlib.dates.date2num(last_time))
            if last_time - first_time < timedelta(days=30):
                axis.xaxis.set_major_locator(md.DayLocator(interval=1))
                axis.xaxis.set_minor_locator(md.DayLocator(interval=1))
            else:
                axis.xaxis.set_minor_locator(md.MonthLocator(interval=1))
                #auto_loc = md.AutoDateLocator(minticks=8, maxticks=12, interval_multiples=True)
                #auto_loc.intervald[md.MONTHLY] = [6]
                rule = md.rrulewrapper(md.MONTHLY, interval=4)
                auto_loc = md.RRuleLocator(rule)
                axis.xaxis.set_major_locator(auto_loc)
            axis.tick_params(labelsize='x-small')
            plt.xlabel("Revisions Timestamp")

            if len(time) and len(ser):
                if opts.window:
                    time = [t.date() for t in time]
                logging.info("Mean: %f", mean)
                if header[i] == "negemo" or header[i] == "posemo":
                    print ser # ONLY FOR TESTING, FIXME WHEN FINISHED
                plt.plot(matplotlib.dates.date2num(time), ser, "b.-")
                plt.axhline(y=mean, color="r")
                plt.title("%s, Mean: %.5f" % (header[i], round(mean, 5)))
                pdf_pag.savefig()
        pdf_pag.close()

if __name__ == "__main__":
    main()

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

def calc_perc(n, total, perc):
    if perc:
        try:
            return float(n)/float(total)*100
        except ZeroDivisionError:
            return 0
    else:
        return float(n)

def collapse_values(timestamps, values, radius):
    t = []
    s = []
    delta = timedelta(days=radius)
    first = timestamps[0]
    curr = []
    i = 0
    for j in timestamps:
        if (j - first) < delta:
            curr.append(j)
        else:
            t.append(curr[-1])
            s.append(sum([x for x in values[i:i+len(curr)]]))
        first = j
        i += 1
    print t, s
    return t, s

def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] input_file output_file")
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output (like timings)")
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

    header = [name for j, name in enumerate(content[0])
              if j != opts.id_col and \
                 (not ignorecols or not j in ignorecols) and \
                 (not onlycols or j in onlycols) and
                 j != len(content[0]) - 1 and  # don't count last two columns
                 j != len(content[0]) - 2]     # (total and text)

    # Creates a matrix (list) with percentages of the occurrencies of every
    # category. Don't count id, total, text, ignore columns. If onlycols is set
    # consider only them.
    mat = []
    timestamps = []

    for line in content[1:]:
        mat.append([calc_perc(e, line[-2], opts.perc) for i, e \
                    in enumerate(line) \
                    if i != opts.id_col and \
                       (not ignorecols or not i in ignorecols) and \
                       (not onlycols or i in onlycols) and
                       i != len(line) - 1 and  # don't count last two cols
                       i != len(line) - 2])    # (total and text)
        timestamps.append(dt.strptime(line[opts.id_col],
                          "%Y-%m-%dT%H:%M:%SZ"))

    collapse_values(timestamps, [], 5)

    mat = np.array(mat, dtype=np.float).transpose()

    pp = PdfPages(files[1])
    for i, series in enumerate(mat):
        plt.clf()
        plt.subplots_adjust(bottom=0.2)
        plt.xticks(rotation=25)
        ax=plt.gca()
        xfmt = md.DateFormatter('%Y-%m-%d')
        ax.xaxis.set_major_formatter(xfmt)
        ax.yaxis.set_data_interval(0.0001, None, False)
        if opts.perc:
            plt.ylabel("%")
        else:
            plt.xlabel("")
        plt.xlabel("Revisions Timestamp")

        s = [x for x in series if x != 0]  # Don't plot zeros!
        t = [x for k, x in enumerate(timestamps) if series[k] != 0]
        if opts.window:
           t, s = collapse_values(t, s, opts.window)
        if t and s:
            plt.plot(matplotlib.dates.date2num(t), s, "-o")
            plt.title(header[i])
            pp.savefig()
    pp.close()

if __name__ == "__main__":
    main()

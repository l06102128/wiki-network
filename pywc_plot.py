#!/usr/bin/env python

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import csv
import numpy as np

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

    # Creates a matrix (list) with percentages of the occurrencies of every
    # category. Don't count id, total, text, ignore columns. If onlycols is set
    # consider only them.
    mat = []
    header = [name for j, name in enumerate(content[0])
              if j != opts.id_col and \
                 (not ignorecols or not j in ignorecols) and \
                 (not onlycols or j in onlycols) and
                 j != len(content[0]) - 1 and  # don't count last two columns
                 j != len(content[0]) - 2]     # (total and text)

    for line in content[1:]:
        try:
            mat.append([float(e)/float(line[-2])*100 for i, e \
                        in enumerate(line) \
                        if i != opts.id_col and \
                           (not ignorecols or not i in ignorecols) and \
                           (not onlycols or i in onlycols) and
                           i != len(line) - 1 and  # don't count last two cols
                           i != len(line) - 2])    # (total and text)
        except ZeroDivisionError:
            pass

    mat = np.array(mat, dtype=np.float).transpose()
    plt.ylabel("%")
    plt.xlabel("Revisions")

    for series in mat:
        plt.plot(series)
    plt.legend(header)
    plt.savefig(files[1])

if __name__ == "__main__":
    main()

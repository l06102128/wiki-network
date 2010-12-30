import csv
from sys import stdout

def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] file")
    p.add_option('-d', '--delimiter', action="store", dest="delimiter",
                 default="\t", help="CSV delimiter")
    p.add_option('-q', '--quotechar', action="store", dest="quotechar",
                 default='"', help="CSV quotechar")
    p.add_option('-l', '--lines', action="store", dest="lines",
                 type="int", help="Number of lines to print")
    p.add_option('-p', '--page', action="store", dest="page",
                 help="Select a specific page")
    opts, files = p.parse_args()
    if len(files) != 1:
        p.error("Wrong parameters")

    fn = files[0]
    csv_reader = csv.reader(open(fn, 'r'),
                            delimiter=opts.delimiter,
                            quotechar=opts.quotechar,
                            quoting=csv.QUOTE_ALL)
    csv_writer = csv.writer(stdout,
                            delimiter=opts.delimiter,
                            quotechar=opts.quotechar,
                            quoting=csv.QUOTE_ALL)
    csv.field_size_limit(1000000000)

    # really ugly but doesn't eat memory
    i = 0
    for line in csv_reader:
        if opts.lines is not None and i >= opts.lines:
            break
        if opts.page is not None:
            if line[2] != opts.page:
                continue
        csv_writer.writerow(line)
        i += 1

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

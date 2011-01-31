#!/usr/bin/env python

## SYSTEM
import sys
import gc
import logging

from datetime import timedelta
from math import ceil

## PROJECT LIBS
from sonet.timr import Timr
from sonet import mediawiki as mwlib, graph as sg, lib


def graph_loader(file_name):
    """
    Loads a sonet.graph object from a pickle/graphml/... file
    """
    try:
        with Timr("GRAPH LOADING"):
            return sg.load(file_name)
    except IOError:
        logging.exception("unable to load a graph from passed file: %s",
                          file_name)
        sys.exit()


def cumulative_analysis(fn, start, end, freq):

    logging.info("running cumulative analysis")

    graph = graph_loader(fn) ## loading graph

    freq_range = int(ceil(((end - start).days + 1) / float(freq)))
    for d in range(freq_range):
        s, e = start, end - timedelta(d * freq)

        if e <= s: continue

        ## processing
        if s != start or e != end:
            with Timr("SUBGRAPHING"):
                process_graph(graph, s, e)

        ## printing stats
        print_graph_stats(graph.g)
    del graph

    return

def time_slice_analysis(fn, start, end, freq, time_window):

    logging.info("running time-slice analysis")

    counter = 0

    ## date range used for sub-graph analysis
    freq_range = int( ceil( ( (end - start).days + 1) / float(freq) ) )
    for s in [start + timedelta(freq * d) for d in range(freq_range)]:

        d = s + timedelta(time_window)
        e = d if (d <= end) else end + timedelta(1)

        graph = graph_loader(fn) ## loading graph

        ## processing
        if s != start or e != end:
            process_graph(graph, s, e)

        ## printing stats
        print_graph_stats(graph.g)

        ## saving memory
        del graph.g, graph

        if not counter % 10:
            logging.info(counter)
            gc.collect()

def process_graph(graph, start, end):

    df = "%Y-%m-%d %H:%M"
    logging.debug("SINCE %s TO %s", start.strftime(df), end.strftime(df))

    ## create a sub-graph on time boundaries
    graph.time_slice_subgraph(start=start, end=end)


def print_graph_stats(g):

    logging.debug("Nodes: %d - Edges: %d\n" % (len(g.vs), len(g.es)))


def create_option_parser():
    import argparse

    p = argparse.ArgumentParser(
            description='Process a graph file running a longitudinal'
                        'analysis over it.')

    ## optional parameters
    p.add_argument('-s', '--start', type=lib.yyyymmdd_to_datetime,
                   metavar="YYYYMMDD",
                   help="Look for revisions starting from this date",
                   default="20010101")
    p.add_argument('-e', '--end', action="store", dest='end',
                   type=lib.yyyymmdd_to_datetime, default=None,
                   metavar="YYYYMMDD",
                   help="Look for revisions until this date")
    p.add_argument('-t', '--time-window',
                   help='length for each time window (default: %(default)s)',
                   type=int, default=7)
    p.add_argument('-f', '--frequency', help='time window frequency',
                   type=int, default=0)
    p.add_argument('-c', '--cumulative',
                   help='cumulative graph analysis, fixed start date',
                   action='store_true')
    ## positional arguments
    p.add_argument('file_name',
                   help="file containing the graph to be analyzed",
                   metavar="GRAPH_FILE")
    return p


def main():
    logging.basicConfig(#filename="graph_longiudinal_analysis.log",
                                stream=sys.stderr,
                                level=logging.DEBUG)
    logging.info('---------------------START---------------------')

    op = create_option_parser()
    args = op.parse_args()

    ## explode dump filename in order to obtain wiki lang, dump date and type
    _, date_, _ = mwlib.explode_dump_filename(args.file_name)

    fn, start, tw = args.file_name, args.start, args.time_window
    ## if end argument is not specified, then use the dump date
    end = args.end if args.end else lib.yyyymmdd_to_datetime(date_)
    ## frequency not to be considered in case of cumulative analysis
    freq = args.frequency if (args.frequency and not args.cumulative) else tw

    if args.cumulative:
        logging.info("Cumulative longitudinal analysis chosen,"
                     "hence not considering following option: frequency")

    with Timr("RUNNING ANALYSIS"):
        if args.cumulative:
            cumulative_analysis(fn, start, end, freq)
        else:
            time_slice_analysis(fn, start, end, freq, tw)


if __name__ == '__main__':
    main()

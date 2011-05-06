import simplejson
import urllib
import sys
import csv
from sonet.mediawiki import _diff_text
from django.utils.encoding import smart_str
import logging


def get_revisions(title, csv_writer, lang, startid=None, prev_text=""):
    api_base = 'http://%s.wikipedia.org/w/api.php' % lang
    options = {}
    options.update({
        'action':'query',
        'prop': 'revisions',
        'rvlimit': 500,
        'titles': title,
        'rvprop': 'ids|timestamp|content',
        'rvdir': 'newer',
        'format': 'json'
    })
    if startid != None:
        options.update({
            'rvstartid': startid
        })
    url = api_base + '?' + urllib.urlencode(options)
    logging.info(url)
    result = simplejson.load(urllib.urlopen(url))
    pages = result["query"]["pages"]
    for page in pages:
        revs = pages[page]["revisions"]
        for r in revs:
            text =  smart_str(_diff_text(prev_text, r["*"])[0])
            csv_writer.writerow([r["timestamp"], smart_str(title), "", text])
            prev_text = r["*"]
    try:
        cont = result['query-continue']['revisions']['rvstartid']
        logging.info("Continue to %d", cont)
        get_revisions(title, csv_writer, lang, cont, prev_text)
    except KeyError:
        logging.info("Finished!")


def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] output_file")
    p.add_option('-l', '--lang', action="store", dest="lang", default="en",
                 help="Wikipedia language")
    p.add_option('-t', '--title', action="store", dest="title",
                 help="Page to download")
    opts, files = p.parse_args()
    if len(files) != 1:
        p.error("Wrong parameters")
    logging.basicConfig(stream=sys.stderr,
                        level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    csv_writer = csv.writer(open(files[0], "w"),
                 delimiter="\t",
                 quotechar='"',
                 quoting=csv.QUOTE_ALL)
    get_revisions(opts.title, csv_writer, opts.lang)

if __name__ == "__main__":
    main()

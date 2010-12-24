from sonet.mediawiki import HistoryPageProcessor, \
                            get_translations, get_tags, \
                            explode_dump_filename, only_inserted_text
from sonet import lib
from django.utils.encoding import smart_str
import csv
import difflib

class HistoryRevisionsPageProcessor(HistoryPageProcessor):
    queue = None
    _skip = None
    threshold = 0
    _prev_text = ""

    def __init__(self, **kwargs):
        super(HistoryRevisionsPageProcessor, self).__init__(**kwargs)
        self.queue = []
        f = open(self.output, 'w')
        self._keys = ["timestamp", "lang", "title", "type", "text"]
        self.csv_writer = csv.DictWriter(f, fieldnames = self._keys,
                                         delimiter = '\t', quotechar = '"',
                                         quoting = csv.QUOTE_ALL)

    def flush(self):
        pages = [{'title': page['title'],
                  'lang': self.lang,
                  'timestamp': page['timestamp'],
                  'text': page['text'],
                  'type': page['type']
                } for page in self.queue]
        self.csv_writer.writerows(pages)
        self.queue = []

    def save(self):
        sm = difflib.SequenceMatcher(None, self._prev_text, self._text)
        self._prev_text = self._text
        page = {
            'title': smart_str(self._title),
            'lang': self.lang,
            'timestamp': self._date,
            'text': smart_str(only_inserted_text(sm)),
            'type': self._type
        }
        self.queue.append(page)

    def process_timestamp(self, elem):
        if self._skip is False:
            return
        self._date = elem.text

    def process_text(self, elem):
        if self._skip is False:
            return
        self._text = elem.text
        self.save()

    def process_page(self, elem):
        self._skip = False

    def process_redirect(self, elem):
        self._skip = True
        raise ValueError, "The page %s is a redirect. " % self._title + \
                          "Pages in the input list must not be redirect"


def main():
    import optparse
    p = optparse.OptionParser(
        usage="usage: %prog [options] file_input desired_list file_output")
    opts, files = p.parse_args()
    if len(files) != 3:
        p.error("Wrong parameters")

    xml = files[0]
    desired_pages_fn = files[1]
    output = files[2]

    with open(desired_pages_fn, 'rb') as f:
        desired_pages = [l[0].decode('latin-1') for l in csv.reader(f)
                                        if l and not l[0][0] == '#']
    lang, _, _ = explode_dump_filename(xml)
    deflate, _lineno = lib.find_open_for_this_file(xml)

    if _lineno:
        src = deflate(xml, 51)
    else:
        src = deflate(xml)

    translation = get_translations(src)
    tag = get_tags(src, tags='page,title,revision,timestamp,text,redirect')
    src.close()
    src = deflate(xml)

    processor = HistoryRevisionsPageProcessor(tag=tag, lang=lang,
                                              output=output)
    processor.talkns = translation["Talk"]
    processor.set_desired(desired_pages)
    processor.start(src)
    processor.flush()


if __name__ == "__main__":
    main()


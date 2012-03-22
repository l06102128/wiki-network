from utpedits2graph import HistoryPageProcessor
import sonet.mediawiki as mwlib
from sonet.lib import find_open_for_this_file
from collections import defaultdict
from django.utils.encoding import smart_str
import unittest


class TestUTPEdits(unittest.TestCase):

    def setUp(self):
        xml = "tests/utpedits2graph/" + \
              "vecwiki-20100307-stub-meta-history-TEST.xml.bz2"
        self.lang, self.date_, self.type_ = mwlib.explode_dump_filename(xml)

        deflate, _lineno = find_open_for_this_file(xml)
        welcome = defaultdict(str)
        welcome.update({'it': r'Benvenut',
                        'en': r'Welcome'})
        if _lineno:
            src = deflate(xml, 51)  # Read first 51 lines to extract namespaces
        else:
            src = deflate(xml)
        tag = mwlib.get_tags(src,
                        tags='page,title,revision,timestamp,contributor,'
                                  'username,ip,comment,id')
        translations = mwlib.get_translations(src)

        try:
            lang_user = unicode(translations['User'])
            lang_user_talk = unicode(translations['User talk'])
        except UnicodeDecodeError:
            lang_user = smart_str(translations['User'])
            lang_user_talk = smart_str(translations['User talk'])
        src.close()
        src = deflate(xml)
        self.processor = HistoryPageProcessor(tag=tag,
                         user_talk_names=(lang_user_talk, u"User talk"))
        self.processor.welcome_pattern = welcome[self.lang]
        self.processor.start(src)
        self.g = self.processor.get_network()

    def test_graph(self):
        self.assertEquals(len(self.g.vs), 7)  # Nodes
        self.assertEquals(len(self.g.es), 9)  # Edges
        self.assertEquals(self.processor.count, 4)
        self.assertEquals(self.processor.count_archive, 0)
        self.assertEquals(self.processor.counter_deleted, 0)
        # Self-loop
        self.assertEquals(1, len([edge for edge in self.g.es \
                                  if edge.target == edge.source]))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestUTPEdits)
    runner = unittest.TextTestRunner()
    runner.run(suite)

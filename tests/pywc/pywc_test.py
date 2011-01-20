import unittest
from pywc import PyWC
import re
class TestPyWC(unittest.TestCase):

    def setUp(self):
        self.pywc = PyWC()
        self.pywc.set_dic("tests/pywc/simple-dic.dic")

    def testReadDic(self):
        self.assertEquals(len(self.pywc.categories), 4)
        self.assertEquals(len(self.pywc.keywords), 9)

    def testClean(self):
        t = ("born in the U.S.A.! Yeah. :D",
             "I feel sick today :S",
             "My favourite TV series: The Big Bang Theory")
        e = ("born in the! Yeah. ",
             "I feel sick today ",
             "My favourite TV series: The Big Bang Theory")
        for i, s in enumerate(t):
            self.pywc._text = s
            self.pywc.clean_text()
            self.assertEquals(self.pywc._text, e[i])

    def testCleanHTML(self):
        t = ("<div><b>42</b> is the <a href='#'>answer</a></div>",
             "<span>Hello World</span>",
             "<!-- I mustn't read this --> Are comments being filtered?")
        e = ("42 is the answer",
             "Hello World",
             " Are comments being filtered?")
        for i, s in enumerate(t):
            self.pywc._text = s
            self.pywc.clean_html_syntax()
            self.assertEquals(self.pywc._text, e[i])

    def testCleanWiki(self):
        t = ("Less taxes for everyone! {{citation needed}}",
             "look here http://google.it lol lol :D http://wikipedia.com",
             "drink a relaxing [Jack Daniel's]",
             "If you want some [Wikipedia:Help] look here",
             "| name =goofy, |city =New York",
             "[File:Case di Volano.jpg|thumb|250px|Volano vista da un dosso]",
             "vicino a [[Calliano (Trentino-Alto Adige)|Calliano]] c'e' un",
             "[[nap:test:Volano (TN)]]",
             "andare in S.Marco")
        e = ("Less taxes for everyone! ",
             "look here  lol lol :D ",
             "drink a relaxing Jack Daniel's",
             "If you want some Help look here",
             "",
             "Volano vista da un dosso",
             "vicino a Calliano c'e' un",
             "Volano (TN)",
             "andare in S.Marco")
        for i, s in enumerate(t):
            self.pywc._text = s
            self.pywc.clean_wiki_syntax()
            self.assertEquals(self.pywc._text, e[i])

    def testOutput(self):
        expected = "".join([line for line in \
                            open("tests/pywc/pywc_expected.csv")])
        self.pywc.csv_out = open("tests/pywc/pywc_result.csv", "w")
        src = open("tests/pywc/pywc_input.csv")
        self.pywc.start(src)
        self.pywc.flush()
        self.pywc.csv_out.close()
        result = "".join([line for line in open("tests/pywc/pywc_result.csv")])
        self.assertEquals(expected, result)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestPyWC)
    runner = unittest.TextTestRunner()
    runner.run(suite)

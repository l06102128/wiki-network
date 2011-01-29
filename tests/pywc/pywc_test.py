import unittest
from pywc import PyWC
import re
class TestPyWC(unittest.TestCase):

    def setUp(self):
        self.pywc = PyWC()
        self.pywc.set_dic("tests/pywc/simple-dic.dic")

    def test_read_dic(self):
        self.assertEquals(len(self.pywc.categories), 4)
        self.assertEquals(len(self.pywc.keywords), 9)

    def test_clean(self):
        t = (";D :E born in the U.S.A.! Yeah. A. :-D",
             "I feel sick today :S",
             ":My favourite TV series: The Big Bang Theory",
             "F.B.K.")
        e = ("born in the! Yeah. ",
             "I feel sick today ",
             ":My favourite TV series: The Big Bang Theory",
             "")
        for i, s in enumerate(t):
            self.pywc._text = s
            self.pywc.clean_text()
            self.assertEquals(self.pywc._text, e[i])

    def test_clean_HTML(self):
        t = ("<div><b>42</b> is the <a href='#'>answer</a></div>",
             "<span>Hello World</span>",
             "<!-- I mustn't read this --> Are comments being filtered?",
             "I don't &amp; like HTML entities &dioji; LO&ppp;L")
        e = ("42 is the answer",
             "Hello World",
             " Are comments being filtered?",
             "I don't  like HTML entities  LOL")
        for i, s in enumerate(t):
            self.pywc._text = s
            self.pywc.clean_html_syntax()
            self.assertEquals(self.pywc._text, e[i])

    def test_clean_wiki(self):
        t = ("Less taxes for everyone! {{citation needed}}",
             "look here http://google.it/a/lol.html lol lol :D http://wiki.com",
             "drink a relaxing [Jack Daniel's]",
             "If you want some [Wikipedia:Help] look here",
             "| name =goofy, |city =New York",
             "[File:Case di Volano.jpg|thumb|250px|Volano vista da un dosso]",
             "vicino a [[Calliano (Trentino-Alto Adige)|Calliano]] c'e' un",
             "[[nap:test:Volano (TN)]]",
             "andare in S.Marco",
             "[[Pagina|link fatto male poiche' manca una parentesi quadra " \
             "e c'e' caratteri strani dentro? ;)]",
             "[http://www.nps.gov/ Oklahoma City National Memorial] National")
        e = ("Less taxes for everyone! ",
             "look here  lol lol :D ",
             "drink a relaxing Jack Daniel's",
             "If you want some Help look here",
             "",
             "Volano vista da un dosso",
             "vicino a Calliano c'e' un",
             "Volano (TN)",
             "andare in S.Marco",
             "link fatto male poiche' manca una parentesi quadra " \
             "e c'e' caratteri strani dentro? ;)",
             " Oklahoma City National Memorial National")
        for i, s in enumerate(t):
            self.pywc._text = s
            self.pywc.clean_wiki_syntax()
            self.assertEquals(self.pywc._text, e[i])

    def test_output(self):
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

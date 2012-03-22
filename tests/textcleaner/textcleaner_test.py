import unittest
from sonet.mediawiki import TextCleaner


class TestTextCleaner(unittest.TestCase):

    def setUp(self):
        self.textcleaner = TextCleaner()

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
            self.assertEquals(self.textcleaner.clean_text(s), e[i])

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
            self.assertEquals(self.textcleaner.clean_html_syntax(s), e[i])

    def test_clean_wiki(self):
        t = ("Less taxes for everyone! {{citation needed}}",
             "look here http://google.it/a/lol.html lol :D http://wiki.com",
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
             "look here  lol :D ",
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
            self.assertEquals(self.textcleaner.clean_wiki_syntax(s), e[i])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestTextCleaner)
    runner = unittest.TextTestRunner()
    runner.run(suite)

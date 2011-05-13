import unittest
from pywc import PyWC

class TestPyWC(unittest.TestCase):

    def setUp(self):
        self.pywc = PyWC()
        self.pywc.set_dic("tests/pywc/simple-dic.dic")

    def test_read_dic(self):
        self.assertEquals(len(self.pywc.categories), 4)
        self.assertEquals(len(self.pywc.keywords), 9)

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

import unittest
from pywc import PyWC

class TestPyWC(unittest.TestCase):
    def setUp(self):
        self.pywc = PyWC()
        self.pywc.set_dic("tests/simple-dic.dic")
    def testReadDic(self):
        pass
    def testOutput(self):
        expected = "".join([line for line in open("tests/pywc_expected.csv")])
        self.pywc.csv_out = open("tests/pywc_result.csv", "w")
        src = open("tests/pywc_input.csv")
        self.pywc.start(src)
        self.pywc.flush()
        self.pywc.csv_out.close()
        result = "".join([line for line in open("tests/pywc_result.csv")])
        self.assertEquals(expected, result)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestPyWC)
    runner = unittest.TextTestRunner()
    runner.run(suite)

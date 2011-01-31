import unittest
import os

class TestCSVManipulation(unittest.TestCase):
    def test_output(self):
        done = False
        i = 0
        src = "tests/csv_manipulation/input0.csv"
        args = ["-l 2",
                "-p page1",
                "",
                "-t talk",
                "-p page3 -t normal -l 1"
                ]
        while not done:
            try:
                out = (os.popen('./csv_manipulation.py %s %s' % \
                       (args[i], src))).read()
                expected = "".join([line for line in \
                           open("tests/csv_manipulation/expected%d.csv" % i)])
                self.assertEquals(expected, out)
                i += 1
            except IndexError:
                done = True


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestPyWC)
    runner = unittest.TextTestRunner()
    runner.run(suite)

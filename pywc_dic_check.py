from sys import argv, exit
import urllib
import csv
import simplejson

def main():
    if len(argv) < 4:
        print "Error: Wrong parameters"
        exit(0)
    ns = argv[1]
    inp = open(argv[2])
    out = open(argv[3], "w")
    csv_writer = csv.writer(out)
    content = inp.read().split("%")
    if (len(content)) != 3:
        raise ValueError("Invalid dic file!")
    keywords =  list(x.split("\t")[0] for x in content[2].split("\n")
                     if x and not x.startswith("//"))

    for k in keywords:
        print "Processing keyword: %s" % k
        url = "http://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=%s&srnamespace=%s&srprop=&srwhat=text&format=json" % (k, ns)
        result = simplejson.load(urllib.urlopen(url))
        try:
            occurrencies = result["query"]["searchinfo"]["totalhits"]
        except KeyError:
            occurrencies = 0
        print url
        print occurrencies
        csv_writer.writerow([k, ns, occurrencies])

if __name__ == "__main__":
    main()

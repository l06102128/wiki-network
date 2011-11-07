import os
import sys
import csv
from collections import Counter


def main():
    output_file = sys.argv[2]
    output_data = {}
    fielnames = None
    for filename in os(listdir(sys.argv[1])):
        if not filename.endswith(".csv"):
            continue
        current_file = csv.DictReader(open(filename))
        fieldnames = current_file.fieldnames
        for line in current_file:
            if not line["date"] in output_data:
                output[line["date"]] = Counter()
            for key in line:
                if key != "date":
                    output[line["date"]][key] += line[key]
    out = csv.DictWriter(open(output_file, "w"), fieldnames=fieldnames)
    for date in output_data:
        row = output_data[date]
        row["date"] = date
        out.writerow(row)


if __name__ == "__main__":
    main()

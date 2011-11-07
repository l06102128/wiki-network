import os
import sys
import csv
from collections import Counter


def main():
    output_file = sys.argv[2]
    input_dir = sys.argv[1]
    output_data = {}
    fieldnames = None
    for filename in os.listdir(input_dir):
        if not filename.endswith(".csv"):
            continue
        current_file = csv.DictReader(open(os.path.join(input_dir, filename)),
                                      delimiter="\t")
        fieldnames = current_file.fieldnames
        for line in current_file:
            date = line["date"]
            ns = line["ns"]
            if not ns in output_data:
                output_data[ns] = {}
            if not date in output_data[ns]:
                output_data[ns][date] = Counter()
            for key in line:
                if line[key].isdigit():
                    output_data[ns][date][key] += int(line[key])
    out = csv.DictWriter(open(output_file, "w"), fieldnames=fieldnames,
                         delimiter="\t")
    out.writeheader()
    for ns in sorted(output_data):
        for date in sorted(output_data[ns]):
            row = output_data[ns][date]
            row["date"] = date
            row["ns"] = ns
            out.writerow(row)


if __name__ == "__main__":
    main()

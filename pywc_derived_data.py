"""
This is script is used only for testing purposes.
It's needed to add derived columns to pywc output
"""

if __name__ == "__main__":
    from sys import argv, stdout
    import csv

    if len(argv) != 2:
        exit(0)

    # CSV handlers
    csv_reader = csv.DictReader(open(argv[1], 'r'),
                                delimiter="\t")
    fields = csv_reader.fieldnames
    fields.insert(-4, "emotivity")
    csv_writer = csv.DictWriter(stdout,
                                fieldnames=fields,
                                delimiter="\t")
    csv.field_size_limit(1000000000)  # Used for big cells, prevents exception

    csv_writer.writeheader()

    for line in csv_reader:
        emotivity = float(line["posemo"]) - float(line["negemo"])
        line["emotivity"] = emotivity
        csv_writer.writerow(line)


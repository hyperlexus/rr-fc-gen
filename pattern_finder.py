import ijson
import time
import os
import re
import json


def find_regex_pattern_to_json(input_filename, output_filename, regex_string):
    if not regex_string:
        print("error, no pattern.")
        return

    print(f"scanning '{input_filename}'... with pattern: r'{regex_string}' to '{output_filename}'.")

    try:
        pattern = re.compile(regex_string)
    except re.error as e:
        print(f"error {e}")
        return

    start_time = time.time()
    found_count = 0
    scanned_count = 0

    try:
        with open(input_filename, 'rb') as infile, open(output_filename, 'w') as outfile:
            outfile.write('{')
            is_first_match = True
            fc_stream = ijson.kvitems(infile, '')

            for pid, fc_value in fc_stream:
                scanned_count += 1

                if pattern.fullmatch(fc_value):
                    if found_count < 50:
                        print(f"match number {found_count}! {pid} -> {fc_value}")
                    found_count += 1

                    if not is_first_match:
                        outfile.write(',')

                    outfile.write(f'{json.dumps(pid)}:{json.dumps(fc_value)}')

                    is_first_match = False

                if scanned_count % 25_000_000 == 0:
                    print(f"  ...scanned {scanned_count:,} records...")

            outfile.write('}')

    except FileNotFoundError:
        print(f"file '{input_filename}' was not found.")
        return
    except Exception as e:
        print(f"error: {e}")
        return

    end_time = time.time()
    print(f"\ndone. scanned {scanned_count:,}, found {found_count}, took {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    input_file = "final_data.json"
    output_file = "matches.json"

    # regex pattern
    REGEX_PATTERN_TO_FIND = r"\d*31415926\d*"

    find_regex_pattern_to_json(input_file, output_file, REGEX_PATTERN_TO_FIND)

from pattern_finder import find_regex_pattern_to_json

def narrow():
    input_file = "resources/matches.json"  # after narrowing it down once you can narrow it down again by copying the results from narrowed_it_down.json to matches.json
    output_file = "resources/narrowed_it_down.json"

    # regex pattern
    REGEX_PATTERN_TO_FIND = r"^[^0]*(?:0[^0]*){0,8}$"

    find_regex_pattern_to_json(input_file, output_file, REGEX_PATTERN_TO_FIND)

if __name__ == "__main__":
    narrow()

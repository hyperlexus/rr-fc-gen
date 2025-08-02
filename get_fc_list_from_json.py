import json

def fclist(mode):
    if mode == "normal":
        input_file = "resources/matches.json"
        output_file = "resources/userfriendlylist.txt"
    elif mode == "narrowed":
        input_file = "resources/narrowed_it_down.json"
        output_file = "resources/narroweddownuserfriendlylist.txt"
    else:
        print("please enter a valid mode in line 28.")

    with open(input_file, "r") as f:
        matches = json.load(f)

    fclist = []
    for key, value in matches.items():
        value = f"{value[0:4]}-{value[4:8]}-{value[8:12]}"
        fclist.append(f"{key} - {value}")

    open(output_file, 'w').close()

    with open(output_file, "a") as f:
        for entry in fclist:
            f.write(entry + "\n")

if __name__ == "__main__":
    MODE = "narrowed"  # this has to be "normal" or "narrowed", depending on what you want to use
    fclist(MODE)


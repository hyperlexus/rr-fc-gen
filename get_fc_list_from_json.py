import json

with open("matches.json", "r") as f:
    matches = json.load(f)

for i in matches:
    print(matches[i])

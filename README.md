# rr-fc-gen
generates all possible fcs with all pids and lets you search them using patterns
# you need ~~52gb~~ 13gb of space and like 12gb of ram!!!! 
(holy optimization)
## how to use:

option 1: download the exe from releases, read below and run\
option 2: use from source:
- clone using pycharm or vscode
- set a python interpreter (a venv)
- `pip install -r requirements.txt`

this tool has completely changed since last time and now has a gui.
1. put the exe somewhere you want it, it will create a folder called `fc-gen-resources`
2. click the "generate fcs" button and wait for it to be done, should take about 500-600 seconds depending on your pc
3. enter a regex pattern (ask chatgpt to make you one according to your wishes or make it yourself) and search for codes that match
4. click format matches.json to text and open the file, boom you can now search through fcs

enjoy!\
<br>note it can sometimes be a little bit finnicky when generating (or sorting through) a billion fcs.\
since it does everything in parallel, you might have to press the cancel button a few times,
or when it shows 60/100 done but the file is already 14,000,000,000 bytes you can just close it

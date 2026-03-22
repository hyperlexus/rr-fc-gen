# rr-fc-gen v2.0
generates all possible fcs with all pids and lets you search them using SQL and patterns
### note that this generates a database about 9.6GB in size.
## how to use:

option 1: download the zip from releases, extract, read below and run\
option 2: from source:
- clone using pycharm or vscode
- set up a python interpreter (venv)
- `pip install -r requirements.txt`
- run main.py

this tool received a huge update march 26 and now builds into a database.
1. press the top button to generate and populate the database with all friend codes.
2. use the number wheels to select how many of each digit your desired friend code should have.\
searching this takes now about 3 seconds.
3. you may additionally use regex patterns,
this will be way slower but possibly output fcs more closely aligned with what you're looking for. 
4. hit the search button.
5. hit the format button, and check the fc-gen-resources folder for matches.txt
6. enjoy your new friend code! for information on how to set it, check either:
   - https://hyperlexus.uk/mkwii/fc
   - https://hyperlexus.uk/mkwii/rksys (coming soon)
   - https://github.com/hyperlexus/change-license-fc
   - https://gabrlel.github.io/godtool.html
   - Modified Torran is Silly!
## make sure to check if a friend code is available before taking it!!!!

notes:
- it can look like it's not doing anything when generating, it takes a while and you can watch the file sizes growing.
- regex is wonky, use regex helpers and patterns on stackoverflow to help with it, it sucks lol
- credits to ki for helping develop this! ur amazing

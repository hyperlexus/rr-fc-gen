# rr-fc-gen
generates all possible fcs with all pids

# you need 52gb of space and like 12gb of ram!!!!

## how to use:
- clone using pycharm or vscode
- `pip install -r requirements.txt`

- run [main.py](main.py)
- wait for like 10 minutes
- run [combine_chunks.py](combine_chunks.py) when done, takes like 3 minutes
- delete data_chunk_1 - data_chunk_100.json (u have to do this manually bc i dont wanna automate it and waste 10min if smth goes wrong)

## how to find unique fcs with a pattern:

- put a regex pattern at the bottom of [pattern_finder.py](pattern_finder.py)
- wait like 3 minutes for matches
- find them in matches.json :)


### you can do this more in depth:
- you can use pattern_finder.py to find an approximate pattern that matches everything, and then use [narrow_it_down.py](narrow_it_down.py) to search those patterns as it's faster.
- for example, you can find all fcs with 9 repeating digits (hi lex), and then search those for certain digits you want.
<br><br>
- if you want to print a user friendly list, you can use [get_fc_list_from_json.py](get_fc_list_from_json.py) and select the mode at the bottom depending on if you want to
use [the original matches](resources/matches.json) or the [narrowed down matches](resources/narrowed_it_down.json).


## patterns i've tried:
`^[^0]*(?:0[^0]*){0,8}$` - matches all fcs that have less than 9 zeroes (in case you want to find cool fcs but omit all boring pid=fc ones)
<br><br>
`^(?!(?:[^0]*0){9}).*$` - same as above but more efficient
<br><br>
`^(?=.*(\d)(?:[^\1]*\1){`n`}[^\1]*$)\d{12}$` - checks all fcs that have n same digits where n has to be replaced by 2-12. returns for example 4033-3303-3333 with n=9
<br><br>
`^(?=.{12}$)(?:0*[^0]{3}0*|1*[^1]{3}1*|2*[^2]{3}2*|3*[^3]{3}3*|4*[^4]{3}4*|5*[^5]{3}5*|6*[^6]{3}6*|7*[^7]{3}7*|8*[^8]{3}8*|9*[^9]{3}9*)$` bit of a goofy one,
checks if the 3 numbers that don't match the other 9 numbers are in a row. returns for example 4003-3333-3333.

**if you have any more patterns, please let me know!**

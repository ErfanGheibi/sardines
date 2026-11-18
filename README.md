Make transportNSW account:
`https://opendata.transport.nsw.gov.au/data/user/register?id=`

You can use a fake email: `https://temp-mail.org/en/`

- login
- click your username in top-right corner
- create an API key with a random name
- you will be prompted for this when you run the "first time" command below.

first time, run this:
`git clone https://github.com/ErfanGheibi/sardines.git && cd sardines && chmod +x run_me.sh && ./run_me.sh
`

every time after, run this:
`./run_me.sh`

# TODO
- improve GUI, add "FROM" and "TO" text to the left of the drop-down selectors (easy)
- add a feature which gradually collects data over time and uses it to predict the train distributions at each platform, we don't want a user to think that they can wait for the next train since it seems to be less packed if that train is going to become packed by the time it reaches them (medium)
- experimentally discover turn-around times at end-points, when a train disappears at the end of the line, make it instantly appear as due in x minutes on the same platform but going the other way (harder)
- add similar functionality for train lines T1, T2, ... (harder)

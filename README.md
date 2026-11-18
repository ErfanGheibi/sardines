# get free API Key
Goto: `https://opendata.transport.nsw.gov.au/data/user/register?id=`
And sign up, perhaps with a fake email like this: `https://temp-mail.org/en/`

- After you login, click your username in the top-right corner.
- Pick and a random name, generate the API token.
- After you paste the setup command below, paste your token in.

# Setup
```bash
mkdir ~/sardines && cd ~/sardines
# put app.py, index.html, tfnsw_metro.proto, setup.sh here
chmod +x setup.sh && ./setup.sh
# then open http://localhost:8000
```

# Todo:
* Add text to clarify what fields are for:
- "To:" Tallawong or Bankstown
- "From:" current station
* Add in a historical data since a metro might seem full but then drastically empty at Chatswood.
* predict empty trains at end-points (Tallawong and Bankstown).
* Expand to include other train lines, like T1, T2, etc.

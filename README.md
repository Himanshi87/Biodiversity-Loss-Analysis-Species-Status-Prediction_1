# BioRisk: IUCN Extinction-Risk Predictor

Website with login. An email is sent to the user when they create an account and each time they log in. Requires Python 3.9+.

## Run
    pip install -r requirements-web.txt
    python server.py          # open http://127.0.0.1:5000

## Email (SMTP)
Set these environment variables before running (example for Gmail with an app password):
    SMTP_HOST=smtp.gmail.com  SMTP_PORT=587  SMTP_USER=you@gmail.com  SMTP_PASS=<app password>  SMTP_FROM=you@gmail.com
Without them the server runs in development mode and prints emails in its console.
Optional: SECRET_KEY (session signing), HTTPS=1 (secure cookies when served over HTTPS), PORT.

## Real predictions
Put `Markov_Random_Forest (1).xlsx` in `biodiversity_app/data/`, copy `export_model.py` into `biodiversity_app/`, run `python export_model.py`, restart the server.

## Notes
- Accounts are stored in `users.db` (passwords hashed). Do not commit `users.db` or `.secret_key`.
- Reasons and conservation measures shown for EN/CR species are informational; verify them at iucnredlist.org.

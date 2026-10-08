# Disney Cruise Data Explorer — Bonus Challenge

Simple Flask web app using the cleaned `disney_cruises.csv` as the data source. No Supabase required.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Deploy on Render

1. Create a GitHub repository and upload all files in this folder.
2. On Render, create **New + Web Service** and connect the GitHub repository.
3. Runtime: Python.
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app`
6. Choose the free instance if available.
7. Deploy and copy the generated `onrender.com` URL into the challenge form.

Health check: `/health`

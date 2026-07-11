# Stock Comparison Tool

Compares stock levels between a WASP export and a Dynamics export, matching on
Item Number and reporting the minimum stock available in both systems.

## Files

- `stock_logic.py` — the actual comparison logic (file loading, filtering, pivoting, matching). Shared by both interfaces below.
- `app.py` — the Streamlit web app (upload files in a browser, see results, download Excel).
- `stock_comparison_cli.py` — command-line version, for running locally without a browser.
- `requirements.txt` — Python dependencies.

## Run the web app locally

```
pip install -r requirements.txt
streamlit run app.py
```

This opens a local browser tab where you upload the WASP file and Dynamics
file, click **Compare Stock**, and download the results as Excel.

## Run the command-line version

```
python stock_comparison_cli.py wasp_export.xlsx dynamics_export.xlsx -o comparison.xlsx
```

## Deploy for free with Streamlit Community Cloud

1. **Push this folder to a new GitHub repo:**
   - Create a repo at https://github.com/new (don't add a README — keep it empty)
   - On the empty repo page, click "uploading an existing file"
   - Drag in `stock_logic.py`, `app.py`, `stock_comparison_cli.py`, `requirements.txt`, and this `README.md`
   - Commit changes

2. **Deploy it:**
   - Go to https://share.streamlit.io
   - Sign in with your GitHub account
   - Click **New app**, select your repo, and set the main file path to `app.py`
   - Click **Deploy**

You'll get a free, live URL (something like `yourapp.streamlit.app`) that
your team can open directly in a browser — no installation needed on their
end.

## Business rules

- Only rows whose **Site** is in the included-sites list are kept.
- Rows whose **Location** contains any of the excluded patterns are dropped.
- Remaining WASP rows are summed per Item Number (a "pivot").
- WASP totals are matched against the Dynamics file by Item Number.
- Only items with **positive stock in both systems** are included in the
  final result, reported as the minimum of the two stock levels.

Both the included-sites list and the excluded-location patterns are defined
at the top of `stock_logic.py` — edit them there if the business rules change.

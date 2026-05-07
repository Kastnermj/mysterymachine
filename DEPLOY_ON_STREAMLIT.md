# Deploy Online

Recommended first URL:

`https://mysterymachine.streamlit.app`

If that exact subdomain is taken, try:

- `mystery-machine-alpha`
- `scoobyflow`
- `pricing-gap-lab`
- `tenbagger-board`
- `contrarian-mystery`

## What You Do

1. Create a private GitHub repository.

   Suggested repo name:

   `mysterymachine`

2. Upload/push the project files from this folder into that repository.

   The repository root should contain:

   - `streamlit_app.py`
   - `requirements.txt`
   - `main.py`
   - `app/dashboard.py`
   - `modules/`
   - `data/`

3. Open Streamlit Community Cloud.

   Go to:

   `https://share.streamlit.io`

4. Click `Create app`.

5. Choose the GitHub repo.

6. Use this app entrypoint:

   `streamlit_app.py`

7. For the app URL/subdomain, try:

   `mysterymachine`

8. Deploy.

## Refresh Behavior

The included GitHub Actions workflow can refresh the research data:

`.github/workflows/refresh-data.yml`

It supports:

- manual refresh from the GitHub Actions tab
- scheduled weekday refresh at 10:30 UTC

The workflow commits updated files under:

- `data/processed`
- `outputs/watchlists`

Streamlit then redeploys or reruns from the updated repository data.

## Privacy

The app currently has no password gate. Use Streamlit sharing controls or keep the app/repo private if you want access limited.

This app is a research watchlist engine, not investment advice.

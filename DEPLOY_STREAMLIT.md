# Deploy on Streamlit Community Cloud

You connect **GitHub** once; Streamlit hosts the app and gives you a **`.streamlit.app`** URL. No EC2 bill for typical public-app use (see [Streamlit pricing](https://streamlit.io/cloud)).

## 1. Put the project on GitHub

1. Create a **new repository** (can be private if your Streamlit plan allows it; free tier is often **public**).
2. From your machine (with [Git](https://git-scm.com/) installed):

   ```bash
   cd path/to/playlist
   git init
   git add binge_schedule config streamlit_app.py main.py requirements.txt Run_UI.bat README_FOR_OTHER_PC.txt .gitignore .streamlit config/cloud.yaml DEPLOY_STREAMLIT.md
   git commit -m "Initial commit: BINGE UI"
   git branch -M main
   git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
   git push -u origin main
   ```

   Do **not** commit `venv/`, `out/`, or personal YAML with real `C:/Users/...` paths if the repo is public. This repo includes **`config/cloud.yaml`** for the hosted app default.

## 2. Sign in to Streamlit Community Cloud

1. Open **https://share.streamlit.io** (or **https://streamlit.io/cloud** → deploy).
2. Sign in with **GitHub** and authorize Streamlit to read the repos you choose.

## 3. Create the app

1. Click **New app** (or **Create app**).
2. **Repository:** pick `YOUR_USER/YOUR_REPO`.
3. **Branch:** `main` (or your default branch).
4. **Main file path:** `streamlit_app.py` (at the repo root).
5. **App URL (optional):** pick a short subdomain, e.g. `binge-grids-yourname`.
6. **Advanced settings** (optional):
   - **Python version:** 3.12 is fine.
   - **Secrets:** only if you add API keys later (not required for this app).
7. **Deploy.**

First build can take a few minutes while dependencies install.

## 4. Share the link

After deploy, Streamlit shows a URL like:

`https://your-subdomain.streamlit.app`

Send that link to anyone who should use the UI. They need a browser only.

## 5. Local vs cloud config

- **Cloud:** the sidebar defaults to **`config/cloud.yaml`** (Gracenote ID only; no real content workbook).
- **Your machine:** you can type **`config/april_2026.yaml`** (or any path) in the sidebar if you use paths that exist on disk.

## Updates

Push to `main`; Streamlit usually **redeploys automatically** (or use “Reboot app” in settings if something sticks).

## Troubleshooting

- **Import errors:** ensure the `binge_schedule` **package folder** is committed (not empty).
- **Build fails on `requirements.txt`:** check the deploy logs on Community Cloud; pin a version if a package broke on a new release.

# Desktop App Download Link (from Streamlit)

Use this when you want people to click a button in the Streamlit app and download your Windows installer.

## How it works

The app includes a **Download Desktop App (Windows)** button and links to GitHub Releases by default:

`https://github.com/h3artfield/playlist/releases/latest/download/ScheduleBuilderSetup.exe`

The installer file should be hosted outside Streamlit (for example GitHub Releases, S3, or Cloudflare R2).

## Configure the button

Set these values as environment variables or Streamlit secrets if you want to override defaults:

- `DESKTOP_APP_DOWNLOAD_URL` (optional override)  
  Direct link to installer
- `DESKTOP_APP_GITHUB_REPO` (optional)  
  Repo slug used for default latest-release URL. Example: `my-org/my-repo`
- `DESKTOP_APP_LABEL` (optional)  
  Default: `Download Desktop App (Windows)`
- `DESKTOP_APP_VERSION` (optional)  
  Example: `1.0.0`
- `DESKTOP_APP_RELEASE_NOTES_URL` (optional)  
  Link to release notes page

## Example (Streamlit secrets)

```toml
# Optional override; without this, app uses latest release URL in h3artfield/playlist.
DESKTOP_APP_DOWNLOAD_URL = "https://github.com/h3artfield/playlist/releases/download/v1.0.0/ScheduleBuilderSetup.exe"
DESKTOP_APP_LABEL = "Download Desktop App (Windows)"
DESKTOP_APP_VERSION = "1.0.0"
DESKTOP_APP_RELEASE_NOTES_URL = "https://github.com/h3artfield/playlist/releases/tag/v1.0.0"
```

## Recommended hosting pattern

1. Build installer on CI or release machine (`ScheduleBuilderSetup.exe`)
2. Upload installer to GitHub Releases (or S3/R2)
3. Update the URL/version secrets
4. App automatically shows the new download CTA

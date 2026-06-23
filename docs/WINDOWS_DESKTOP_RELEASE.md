# Build and Publish Windows Desktop Installer

This project can be packaged as a Windows desktop installer (`ScheduleBuilderSetup.exe`).

## What the desktop app runs

When `ScheduleBuilder.exe` starts:

1. It looks for bundled `scheduler-ui/dist/index.html`.
2. If found, it starts **FastAPI + the React Schedule Builder** on `http://127.0.0.1:8765` and opens a **native desktop window** (not a separate browser tab). A bundled intro video (`splash.mp4`) plays first, then the app loads in the same window.
3. If the React bundle is missing, it falls back to the legacy **Streamlit** UI.

The React desktop app includes:

- Schedule builder (auto-generate, save, export)
- **Available Content** catalog
- **Add content** — manual entry, file upload import wizard, format guide
- **Sheet editor** — click a show to edit episodes in a spreadsheet view

User data (saved schedules, imported catalog) is stored under the install folder, typically:

`%LOCALAPPDATA%\ScheduleBuilder\`

## Intro video (splash)

Place your MP4 at `packaging/windows/assets/splash.mp4` (copied into `scheduler-ui/public/` during desktop builds). Replace that file to change the opening clip. Users can press **Esc** or click to skip.

## Installer branding

`scripts/build_app_icon.py` (run automatically in `build_desktop.ps1`) generates from `packaging/windows/ScheduleBuilder.png`:

- `ScheduleBuilder.ico` — setup `.exe` icon and app icon
- `WizardImageLarge.bmp` (164×314) — left banner on installer wizard pages
- `WizardImageSmall.bmp` (55×58) — logo on inner wizard pages

These are wired in `packaging/windows/ScheduleBuilder.iss` via `SetupIconFile`, `WizardImageFile`, and `WizardSmallImageFile`.

## License agreement (installer)

The installer shows `legal/EULA.txt` on the standard Inno Setup license page (`LicenseFile` in `ScheduleBuilder.iss`). Users must accept before installation continues. The running app does not show a separate legal dialog.

## One-time setup

Version number lives in `packaging/windows/app_version.txt` (currently **1.0.56**). The build script writes `app_version.inc` for Inno Setup and `VERSION.txt` into the desktop bundle.

1. Keep installer asset name as `ScheduleBuilderSetup.exe`
2. Publish it to GitHub Releases
3. In Streamlit, the **Download Desktop App (Windows)** button points to:

`https://github.com/h3artfield/playlist/releases/latest/download/ScheduleBuilderSetup.exe`

## Upgrade installs

Installing a newer `ScheduleBuilderSetup.exe` over an existing install:

- Uses the same folder: `%LOCALAPPDATA%\ScheduleBuilder`
- **Keeps** `saved_schedules/` (saved reports and schedules)
- **Keeps** `config/imported_content_catalog.json` (imported content)
- **Keeps** `settings.json` and `logs/`
- Replaces only application binaries and bundled app files

The installer shows a confirmation that user data will be preserved.

## Automated build (recommended)

Use GitHub Actions workflow:

- `.github/workflows/build-windows-installer.yml`

Triggers:

- Manual run (`workflow_dispatch`)
- New published release

Outputs:

- Workflow artifact: `ScheduleBuilderSetup`
- Release asset upload (on release events)

## Local build (Windows)

From repository root in PowerShell:

```powershell
./packaging/windows/build_desktop.ps1 -Clean
choco install innosetup -y
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "packaging/windows/ScheduleBuilder.iss"
```

Installer output:

- `packaging/windows/Output/ScheduleBuilderSetup.exe`

The build script:

- Builds `scheduler-ui` with `npm run build`
- Writes `scheduler-ui/dist/content-catalog.json` from config
- Bundles `binge_schedule`, `config`, `data`, and `scheduler-ui/dist` via PyInstaller
- Includes import wizard modules and `python-multipart` for file uploads

## Dev vs desktop

- **Do not run** `.\scripts\start-dev-api.ps1` while the desktop app is open — both use port **8765**.
- The packaged `.exe` **never** launches the legacy Streamlit UI. If you see Streamlit in a browser tab, reinstall the latest installer (1.0.30+).
- For development, use `http://localhost:5173` (Vite) with the dev API on 8765.

## Troubleshooting

- Startup logs: `%LOCALAPPDATA%\ScheduleBuilder\logs\startup-*.log`
- If upload fails in desktop, rebuild with a recent `build_desktop.ps1` and reinstall.
- `GET /api/health` should report `"content_import_wizard": true`.
- **`api-ms-win-core-path-l1-1-0.dll` missing:** Install [Microsoft Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe), run Windows Update, then reinstall Schedule Builder **1.0.37+** (installer runs the redist automatically when needed). Requires **Windows 10 version 1607** or later (or Windows 11).

## App icon

Source artwork: `packaging/windows/ScheduleBuilder.png` (square-cropped with black padding if not 1:1).

Before each desktop build, `scripts/build_app_icon.py` writes `packaging/windows/ScheduleBuilder.ico` (16–256 px) for the `.exe` and installer, and copies favicons into `scheduler-ui/public/` for the browser tab (`favicon.ico`, `favicon-32.png`).

## Notes

- Installer target folder is per-user: `%LOCALAPPDATA%\ScheduleBuilder` (writable by the user).
- If you need to change default download repo, set `DESKTOP_APP_GITHUB_REPO` in env/secrets.

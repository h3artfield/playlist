# Build and Publish Windows Desktop Installer

This project can be packaged as a Windows desktop installer (`ScheduleBuilderSetup.exe`).

## What the desktop app runs

When `ScheduleBuilder.exe` starts:

1. It looks for bundled `scheduler-ui/dist/index.html`.
2. If found, it starts **FastAPI + the React Schedule Builder** on `http://127.0.0.1:8765` and opens that URL in your default browser.
3. If the React bundle is missing, it falls back to the legacy **Streamlit** UI.

The React desktop app includes:

- Schedule builder (auto-generate, save, export)
- **Available Content** catalog
- **Add content** — manual entry, file upload import wizard, format guide
- **Sheet editor** — click a show to edit episodes in a spreadsheet view

User data (saved schedules, imported catalog) is stored under the install folder, typically:

`%LOCALAPPDATA%\ScheduleBuilder\`

## One-time setup

1. Keep installer asset name as `ScheduleBuilderSetup.exe`
2. Publish it to GitHub Releases
3. In Streamlit, the **Download Desktop App (Windows)** button points to:

`https://github.com/h3artfield/playlist/releases/latest/download/ScheduleBuilderSetup.exe`

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
- For development, use `http://localhost:5173` (Vite) with the dev API on 8765.

## Troubleshooting

- Startup logs: `%LOCALAPPDATA%\ScheduleBuilder\logs\startup-*.log`
- If upload fails in desktop, rebuild with a recent `build_desktop.ps1` and reinstall.
- `GET /api/health` should report `"content_import_wizard": true`.

## Notes

- Installer target folder is per-user: `%LOCALAPPDATA%\ScheduleBuilder` (writable by the user).
- If you need to change default download repo, set `DESKTOP_APP_GITHUB_REPO` in env/secrets.

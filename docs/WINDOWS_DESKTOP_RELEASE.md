# Build and Publish Windows Desktop Installer

This project can be packaged as a Windows desktop installer (`ScheduleBuilderSetup.exe`).

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

## Notes

- Installer target folder is per-user: `%LOCALAPPDATA%\ScheduleBuilder` (writable by the user).
- The app launches Streamlit locally and opens in the default browser.
- If you need to change default download repo, set `DESKTOP_APP_GITHUB_REPO` in env/secrets.

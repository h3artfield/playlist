Schedule Builder (UI + command line)
================================

ON THIS COMPUTER
-----------------
1. Install Python 3.10 or newer from https://www.python.org/downloads/
   During setup, turn ON "Add python.exe to PATH".

2. Copy this whole folder onto the PC (do not rely on the "venv" folder
   from another machine — you can delete venv before zipping; the batch
   file will recreate it).

3. Double-click:  Run_UI.bat
   First run may take a minute while packages install. A browser tab opens.

4. Put your YAML next to config\april_2026.yaml or edit the path in the
   Streamlit sidebar. The UI reads Gracenote ID from that YAML.

COMMAND LINE (optional)
-----------------------
Open Command Prompt in this folder, then:
  venv\Scripts\activate
  python -m binge_schedule -c config\april_2026.yaml -o out

That builds BINGE.xlsx and BINGE GRIDS.xlsx from your grids workbook paths
in the YAML (needs the content workbook + grid files on disk at those paths).

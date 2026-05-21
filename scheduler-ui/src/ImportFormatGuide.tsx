export default function ImportFormatGuide() {
  return (
    <section className="import-format-guide" aria-labelledby="import-format-guide-title">
      <h3 id="import-format-guide-title">File format before you upload</h3>
      <p className="import-format-intro muted">
        Use a <strong>CSV or Excel</strong> file with <strong>one tab per show</strong> (or one movies tab). Each tab should be a simple table:
        column headings on one row, then one row per episode or movie. We will auto-detect headers when possible; matching the names below makes import faster and more accurate.
      </p>

      <div className="import-format-grid">
        <div className="import-format-block import-format-required">
          <h4>Required column headings</h4>
          <p className="muted">At least one title column is required on every tab you want to import.</p>
          <dl>
            <div>
              <dt>Series episodes</dt>
              <dd>
                <strong>Episode</strong> (or Episode title, Title) — the episode name for each row.
              </dd>
            </div>
            <div>
              <dt>Movies / specials</dt>
              <dd>
                <strong>Title</strong> (or Movie title, Asset title) — the program title for each row.
              </dd>
            </div>
          </dl>
        </div>

        <div className="import-format-block import-format-optional">
          <h4>Optional column headings</h4>
          <p className="muted">Include any of these when you have the data; they improve scheduling and metadata.</p>
          <ul>
            <li>
              <strong>Season/Episode</strong> — episode code (e.g. <code>01_01</code>, <code>S01E01</code>)
            </li>
            <li>
              <strong>TRT</strong> or <strong>Runtime</strong> — length (<code>0:47:03</code> or minutes)
            </li>
            <li>
              <strong>Synopsis</strong> or <strong>Description</strong> — episode or movie summary
            </li>
            <li>
              <strong>Year/Original Airdate</strong> — air date or production year
            </li>
            <li>
              <strong>Genre</strong> — primary genre
            </li>
            <li>
              <strong>Playable</strong> — <code>Yes</code> or <code>No</code>. Only <strong>Yes</strong> rows are used when building the on-air schedule. Leave blank = <strong>No</strong>. Keep every episode in the file; use this column instead of row colors or “do not play” notes.
            </li>
            <li>
              <strong>Stars</strong> — cast (stored with the row; not required for import)
            </li>
            <li>
              <strong>Series</strong> or <strong>Show</strong> — only needed on multi-show tabs (e.g. NEW SHOWS); otherwise the tab name is used as the show name
            </li>
          </ul>
        </div>
      </div>

      <div className="import-format-rules">
        <h4>Important</h4>
        <ul>
          <li>
            <strong>Use the Playable column</strong> to control what can go on air. Every row stays in the catalog for inventory; only <strong>Yes</strong> rows are scheduled. Blank Playable = <strong>No</strong>.
          </li>
          <li>If the first <strong>Yes</strong> for a show is episode 6, scheduling starts at episode 6 — earlier rows remain in the file but are skipped.</li>
          <li>Do not rely on row colors or notes like “only play green” — map a <strong>Playable</strong> column instead.</li>
          <li>Put <strong>column headings on a single header row</strong> (e.g. Episode, Season/Episode, TRT, Synopsis). If a tab has no headings, we can try to infer columns from the data, but labeled columns work best.</li>
          <li>Use <strong>one worksheet per series</strong> when you can (e.g. a tab named <em>Stingray</em> with only Stingray episodes).</li>
          <li>Skip blank separator rows and notes-only rows inside the episode table.</li>
          <li>After upload you can review each tab, fix column mapping, and exclude tabs you do not want before importing.</li>
        </ul>
      </div>
    </section>
  )
}

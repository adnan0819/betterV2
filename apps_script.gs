// Google Apps Script for the crown-outline rater study (v2: adds rating columns).
// Bound to a Google Sheet. Creates two tabs: "responses" and "assignments".
//
// GET  ?pid=...&n=<number of blocks>   -> assigns (or returns) the rater's block
// POST JSON body                        -> appends one response row

const RESP_HEADER = ["ts", "pid", "block", "pos", "sid", "crop", "left", "right", "type", "choice", "rating", "reminders", "ms", "ms_rate"];

function sheet_(name, header) {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.appendRow(header); sh.setFrozenRows(1); }
  return sh;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  const pid = (e.parameter.pid || "").trim();
  const n = parseInt(e.parameter.n, 10);
  if (!pid || !n) return json_({ error: "pid and n required" });
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sh = sheet_("assignments", ["ts", "pid", "block"]);
    const rows = sh.getDataRange().getValues();
    for (let r = 1; r < rows.length; r++) {
      if (String(rows[r][1]) === pid) return json_({ block: Number(rows[r][2]), existing: true });
    }
    const block = (rows.length - 1) % n;
    sh.appendRow([new Date().toISOString(), pid, block]);
    return json_({ block: block, existing: false });
  } finally {
    lock.releaseLock();
  }
}

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    const sh = sheet_("responses", RESP_HEADER);
    sh.appendRow(RESP_HEADER.map(k => d[k] === undefined ? "" : d[k]));
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

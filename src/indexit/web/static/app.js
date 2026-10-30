// IndexIt page: sends questions to the local server, streams the answer in, and turns citations like
// [NVIDIA FY2026 10-K, p.51] into links that open that page's tables in the side panel.

const thread = document.getElementById("thread");
const empty = document.getElementById("empty");
const form = document.getElementById("composer");
const input = document.getElementById("question");
const send = document.getElementById("send");
const panel = document.getElementById("panel");
const panelTitle = document.getElementById("panel-title");
const panelBody = document.getElementById("panel-body");
const historyList = document.getElementById("history");

// Shown while Claude researches, before the first word of the answer arrives.
const VERBS = [
  "Thinking", "Leafing through the filings", "Crunching the numbers", "Reading the fine print",
  "Cross-checking figures", "Lining up the columns", "Connecting the dots", "Tallying",
  "Checking the footnotes", "Sharpening the pencil",
];

let filings = [];
let busy = false;
let controller = null;
let conversationId = null; // the saved conversation on screen (null until the first answer of a new one)

// ---------- Filings (for the tagline, the drawer, and resolving citations) ----------

async function loadFilings() {
  const data = await (await fetch("/api/filings")).json();
  filings = data.filings;
  const companies = new Set(filings.map((f) => f.company)).size;
  document.getElementById("library-count").textContent =
    `${filings.length} filings · ${companies} companies`;
}

function findFiling(source) {
  // "AMD FY2025 10-K" -> the AMD FY2025 filing (labels use full names, Claude often uses short ones).
  const year = source.match(/FY\s?(\d{4})/i);
  if (!year) return null;
  const text = source.toLowerCase();
  return filings.find((f) => f.fiscal_year === Number(year[1]) &&
    [f.company, ...f.aliases].some((name) => text.includes(name.toLowerCase()))) || null;
}

// ---------- A small, safe renderer for IndexIt's answer format ----------
// Escapes everything first (filing text is data, never HTML), then adds headings, lists, bold,
// italics, tables and citation links.

const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function citation(inner) {
  const parts = inner.split(";").map((part) => {
    const at = part.indexOf("10-K");
    const filing = at >= 0 ? findFiling(part) : null;
    if (!filing) return null;
    const pages = [];
    for (const m of part.slice(at + 4).matchAll(/(\d+)\s*[–-]\s*(\d+)|(\d+)/g)) {
      for (const n of m[3] ? [m[3]] : [m[1], m[2]]) {
        const page = Number(n);
        if (page >= 1 && page <= filing.pages && !pages.includes(page)) pages.push(page);
      }
    }
    const links = pages.map((p) =>
      `<a href="#" role="button" class="cite-page" data-file="${escapeHtml(filing.file)}" data-page="${p}">p.${p}</a>`);
    return `${part.slice(0, at + 4).trim()}${links.length ? ", " + links.join(", ") : ""}`;
  });
  if (parts.some((p) => p === null)) return null;
  return `<span class="cite">[${parts.join("; ")}]</span>`;
}

function inline(text) {
  let s = escapeHtml(text);
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*\w])\*(?!\s)(.+?)\*(?!\w)/g, "$1<em>$2</em>");
  s = s.replace(/\[([^\[\]]*?10-K[^\[\]]*?)\]/g, (match, inner) => citation(inner) ?? match);
  return s;
}

const isNumber = (cell) => /^[\s$€£(−–-]*[\d.,]+\s*%?\)?\s*(pts?)?$/.test(cell) && /\d/.test(cell);

function tableHtml(rows, className = "") {
  if (!rows.length) return "";
  const [head, ...body] = rows;
  const cell = (tag, c) => `<${tag}${isNumber(c) ? ' class="num"' : ""}>${inline(c)}</${tag}>`;
  return `<div class="table-wrap"><table class="${className}"><thead><tr>${head.map((c) => cell("th", c)).join("")}</tr></thead>` +
    `<tbody>${body.map((r) => `<tr>${r.map((c) => cell("td", c)).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function render(markdown) {
  const lines = markdown.replace(/\r/g, "").split("\n");
  let html = "";
  let para = [];
  let section = false;
  let table = [];
  const lists = []; // open lists: {type, indent}

  const flushPara = () => { if (para.length) { html += `<p>${inline(para.join(" "))}</p>`; para = []; } };
  const closeLists = () => { while (lists.length) html += `</li></${lists.pop().type}>`; };
  const flushTable = () => {
    if (!table.length) return;
    const rows = table.filter((l) => !/^\|?[\s|:-]+\|?$/.test(l))
      .map((l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
    html += tableHtml(rows);
    table = [];
  };

  for (const line of lines) {
    if (/^\s*\|/.test(line)) { flushPara(); closeLists(); table.push(line); continue; }
    flushTable();
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    const item = line.match(/^(\s*)([-*•]|\d+[.)])\s+(.*)$/);
    if (heading) {
      flushPara(); closeLists();
      if (section) html += "</section>";
      const title = heading[1];
      const kind = /filing says/i.test(title) ? "facts" : /might mean/i.test(title) ? "note" : /dig deeper/i.test(title) ? "dig" : "";
      html += `<section class="sec ${kind}"><h3>${inline(title)}</h3>`;
      section = true;
    } else if (item) {
      flushPara();
      const indent = item[1].replace(/\t/g, "  ").length;
      const type = /\d/.test(item[2]) ? "ol" : "ul";
      while (lists.length && (indent < lists.at(-1).indent || (indent === lists.at(-1).indent && type !== lists.at(-1).type))) {
        html += `</li></${lists.pop().type}>`;
      }
      if (!lists.length || indent > lists.at(-1).indent) { html += `<${type}>`; lists.push({ type, indent }); }
      else html += "</li>";
      html += `<li>${inline(item[3])}`;
    } else if (!line.trim()) {
      flushPara();
    } else if (lists.length && /^\s+/.test(line)) {
      html += ` ${inline(line.trim())}`; // continuation of a list item
    } else {
      closeLists();
      para.push(line.trim());
    }
  }
  flushTable(); flushPara(); closeLists();
  if (section) html += "</section>";
  return html;
}

// ---------- Asking ----------

function newExchange(question) {
  empty.hidden = true;
  const el = document.createElement("article");
  el.className = "exchange";
  el.innerHTML = `<p class="q"></p><p class="status-line"><span class="verb"></span><span class="clock"></span></p>` +
    `<ol class="trail"></ol><div class="answer"></div>`;
  el.querySelector(".q").textContent = question;
  thread.appendChild(el);
  return el;
}

function typeVerb(el, verb) {
  // Types the status verb out letter by letter, like a typewriter. Only the status: the answer
  // itself appears at the real speed it's written.
  clearInterval(el._typing);
  let i = 0;
  el.textContent = "";
  el._typing = setInterval(() => {
    el.textContent = verb.slice(0, ++i);
    if (i >= verb.length) clearInterval(el._typing);
  }, 28);
}

// The conversation column scrolls on its own; the sidebar stays put.
const scroller = document.getElementById("main");

function nearBottom() {
  return scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 160;
}

async function ask(question) {
  question = question.trim();
  if (!question || busy) return;
  busy = true;
  send.disabled = true;
  input.value = "";
  autosize();

  const el = newExchange(question);
  const status = el.querySelector(".status-line");
  const verb = el.querySelector(".verb");
  const clock = el.querySelector(".clock");
  const trail = el.querySelector(".trail");
  const answer = el.querySelector(".answer");
  el.scrollIntoView({ behavior: "smooth", block: "start" });

  const started = performance.now();
  let v = 0;
  typeVerb(verb, VERBS[0]);
  const verbTimer = setInterval(() => typeVerb(verb, VERBS[++v % VERBS.length]), 2600);
  const clockTimer = setInterval(() => { clock.textContent = `${Math.round((performance.now() - started) / 1000)} s`; }, 500);

  let text = "";
  let frame = 0;
  const draw = () => {
    frame = 0;
    const follow = nearBottom();
    answer.innerHTML = render(text) + '<span class="caret"></span>';
    if (follow) scroller.scrollTo(0, scroller.scrollHeight);
  };
  const stopThinking = () => { clearInterval(verbTimer); clearInterval(clockTimer); clearInterval(verb._typing); status.remove(); };

  const handle = (event) => {
    if (event.type === "conversation") {
      const isNew = conversationId !== event.id;
      conversationId = event.id;
      if (isNew) loadHistory();
    } else if (event.type === "step") {
      text = ""; // anything written before a tool call was a preamble, not the answer
      answer.innerHTML = "";
      const li = document.createElement("li");
      li.textContent = event.text;
      trail.appendChild(li);
    } else if (event.type === "text") {
      if (status.isConnected) stopThinking();
      text += event.text;
      if (!frame) frame = requestAnimationFrame(draw);
    } else if (event.type === "done") {
      if (status.isConnected) stopThinking();
      cancelAnimationFrame(frame);
      answer.innerHTML = render(event.answer);
      finishDigDeeper(answer);
      collapseTrail(el, trail, event);
      loadHistory();
    } else if (event.type === "error") {
      if (status.isConnected) stopThinking();
      answer.innerHTML = `<p class="error"></p>`;
      answer.querySelector(".error").textContent = event.message;
    }
  };

  controller = new AbortController();
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: conversationId }),
      signal: controller.signal,
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        if (line.trim()) handle(JSON.parse(line));
      }
    }
  } catch (error) {
    if (error.name !== "AbortError") handle({ type: "error", message: "Lost the connection to IndexIt. Is the app still running?" });
  } finally {
    if (status.isConnected) stopThinking();
    answer.querySelector(".caret")?.remove();
    busy = false;
    send.disabled = false;
    controller = null;
    input.focus();
  }
}

function finishDigDeeper(answer) {
  // The 3 follow-up questions become buttons that ask them in this conversation.
  for (const li of answer.querySelectorAll(".sec.dig li")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "dig-q";
    button.innerHTML = li.innerHTML;
    li.replaceChildren(button);
    button.addEventListener("click", () => ask(button.textContent));
  }
}

function collapseTrail(el, trail, event) {
  const parts = [`${event.searches} search${event.searches === 1 ? "" : "es"}`];
  if (event.pages_read) parts.push(`${event.pages_read} page${event.pages_read === 1 ? "" : "s"} read`);
  parts.push(`${Math.round(event.seconds)} s`);
  const details = document.createElement("details");
  details.className = "research";
  details.innerHTML = `<summary>Research trail · ${parts.join(" · ")}</summary>`;
  details.appendChild(trail);
  el.querySelector(".answer").before(details);
}

function showSaved(exchange) {
  // A finished exchange from a saved conversation, drawn the way it looked when it was answered.
  const el = newExchange(exchange.question);
  el.querySelector(".status-line").remove();
  const trail = el.querySelector(".trail");
  for (const step of exchange.steps || []) {
    const li = document.createElement("li");
    li.textContent = step;
    trail.appendChild(li);
  }
  const answer = el.querySelector(".answer");
  answer.innerHTML = render(exchange.answer);
  finishDigDeeper(answer);
  collapseTrail(el, trail, exchange);
}

function clearThread() {
  controller?.abort();
  for (const el of thread.querySelectorAll(".exchange")) el.remove();
  empty.hidden = false;
  panel.hidden = true;
}

async function openConversation(id) {
  const saved = await (await fetch(`/api/conversations/${encodeURIComponent(id)}`)).json();
  clearThread();
  conversationId = saved.id;
  saved.exchanges.forEach(showSaved);
  scroller.scrollTo(0, scroller.scrollHeight);
  loadHistory();
  closeSidebar();
  input.focus();
}

const when = (iso) => {
  const d = new Date(iso);
  const sameDay = d.toDateString() === new Date().toDateString();
  return sameDay ? `Today, ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`
    : d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
};

async function loadHistory() {
  const { conversations } = await (await fetch("/api/conversations")).json();
  if (!conversations.length) {
    historyList.innerHTML = '<li class="none">Your conversations will appear here.</li>';
    return;
  }
  historyList.innerHTML = conversations.map((c) =>
    `<li class="${c.id === conversationId ? "current" : ""}"><button type="button" data-id="${escapeHtml(c.id)}">` +
    `<span class="history-title">${escapeHtml(c.title)}</span>` +
    `<span class="history-meta">${when(c.updated)} · ${c.questions} question${c.questions === 1 ? "" : "s"}</span>` +
    `</button></li>`).join("");
  for (const button of historyList.querySelectorAll("button")) {
    button.addEventListener("click", () => openConversation(button.dataset.id));
  }
}

// ---------- Side panel ----------

function openPanel(title) {
  panelTitle.textContent = title;
  panelBody.innerHTML = '<p class="muted">Loading…</p>';
  panel.hidden = false;
}

async function showPage(file, page) {
  const filing = filings.find((f) => f.file === file);
  openPanel(`${filing ? filing.label : file} · p.${page}`);
  const data = await (await fetch(`/api/page?file=${encodeURIComponent(file)}&page=${page}`)).json();
  const pdfLink = `<a class="page-link" href="/pdf/${encodeURIComponent(file)}#page=${page}" target="_blank" rel="noopener">Open this page in the PDF ↗</a>`;
  const tables = data.tables.map((t) =>
    `<figure><figcaption>${escapeHtml(t.title || "Table")}</figcaption>${tableHtml(t.rows, "panel-table")}</figure>`).join("");
  panelBody.innerHTML = pdfLink +
    (tables || '<p class="muted">No tables on this page. The page text is below.</p>') +
    `<details${tables ? "" : " open"}><summary>Page text</summary><p class="page-text"></p></details>`;
  panelBody.querySelector(".page-text").textContent = data.text;
}

// ---------- Library (D-024) ----------
// Companies and their filings, with indexing progress; adding filings (upload PDFs, or fetch from the SEC)
// always ends in confirmation cards; filings can be removed (the PDF moves to the "removed" folder) or re-indexed.

const companiesList = document.getElementById("companies");
const incomingBox = document.getElementById("incoming");
const addForm = document.getElementById("add-form");
const addStatus = document.getElementById("add-status");
const drop = document.getElementById("drop");
const dropLabel = document.getElementById("drop-label");
const fileInput = document.getElementById("file-input");
const secBox = document.getElementById("sec-contact");
const addDialog = document.getElementById("add-dialog");
const addTitle = document.getElementById("add-title");
const pendingNote = document.getElementById("pending-note");
const expanded = new Set(); // companies opened in the list
let chosenFiles = [];
let secContactSet = false;
let libraryTimer = 0;
let searchableKey = "";

async function post(url, body) {
  const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

const isWorking = (f) => ["queued", "indexing"].includes(f.status) || f.tables === "running" ||
  (f.status === "searchable" && f.tables === "pending");

// Status, kept minimal: a pulsing hollow circle while indexing, a tick for a minute once done.
const DONE_SHOWN_MS = 60000;
const doneAt = new Map(); // file -> when it finished (seen while this page was open)
let wasWorking = new Set();

function statusHtml(f) {
  if (f.status === "failed" || f.tables === "failed") {
    const what = f.status === "failed" ? "Failed" : "Tables failed (text is searchable)";
    return `<span class="status bad">✕ ${what}</span>`;
  }
  if (isWorking(f)) {
    const detail = f.status === "searchable" ? "Searchable now; tables are still being extracted" : "Indexing the text";
    return `<span class="status busy" title="${detail}"><span class="ring"></span>Indexing</span>`;
  }
  if (Date.now() - (doneAt.get(f.file) || 0) < DONE_SHOWN_MS) return '<span class="status busy"><span class="tick">✓</span>Done</span>';
  return "";
}

async function loadLibrary() {
  clearTimeout(libraryTimer);
  let data;
  try {
    data = await (await fetch("/api/library")).json();
  } catch {
    libraryTimer = setTimeout(loadLibrary, 5000);
    return;
  }
  secContactSet = data.sec_contact_set;
  const all = data.companies.flatMap((c) => c.filings);
  for (const f of all) if (wasWorking.has(f.file) && f.status === "ready") doneAt.set(f.file, Date.now());
  wasWorking = new Set(all.filter(isWorking).map((f) => f.file));
  renderCompanies(data.companies);
  renderIncoming(data.incoming);
  updateMethod();
  // Citation links need the list of searchable filings: refresh it when that changes.
  const key = data.companies.flatMap((c) => c.filings.filter((f) => ["searchable", "ready"].includes(f.status))
    .map((f) => f.file)).sort().join("|");
  if (key !== searchableKey) { searchableKey = key; loadFilings(); }
  const recentlyDone = [...doneAt.values()].some((t) => Date.now() - t < DONE_SHOWN_MS);
  libraryTimer = setTimeout(loadLibrary, wasWorking.size ? 2000 : recentlyDone ? 5000 : 15000);
}

function renderCompanies(companies) {
  companiesList.innerHTML = companies.map(({ company, filings: list }) => {
    const open = expanded.has(company);
    return `<li class="company">` +
      `<button type="button" class="company-row" data-company="${escapeHtml(company)}" aria-expanded="${open}">` +
      `<span class="company-name">${escapeHtml(company)}</span><span class="company-count">${list.length}</span></button>` +
      list.map((f) => statusHtml(f) && !open ? `<p class="working">FY${f.fiscal_year} · ${statusHtml(f)}</p>` : "").join("") +
      `<ul class="filings"${open ? "" : " hidden"}>${list.map(filingHtml).join("")}</ul></li>`;
  }).join("") || '<li class="muted">No filings yet. Add one above.</li>';
}

function filingHtml(f) {
  const status = statusHtml(f);
  const meta = [f.period_end && f.period_end !== "unknown" ? `year ended ${f.period_end}` : "",
    f.pages ? `${f.pages} pages` : ""].filter(Boolean).join(" · ");
  const retry = f.status === "failed" || f.tables === "failed"
    ? `<button type="button" class="link" data-reindex="${escapeHtml(f.file)}">Retry</button>` : "";
  return `<li class="filing"><div class="filing-line"><span>FY${f.fiscal_year}</span><span class="filing-actions">` +
    `<a href="/pdf/${encodeURIComponent(f.file)}" target="_blank" rel="noopener">Open</a>${retry}` +
    `<button type="button" class="link" data-remove="${escapeHtml(f.file)}" data-label="${escapeHtml(f.label)}">Delete</button>` +
    `</span></div><div class="filing-meta">${escapeHtml(meta)}</div>` +
    (status ? `<div>${status}</div>` : "") + `</li>`;
}

companiesList.addEventListener("click", async (e) => {
  const row = e.target.closest(".company-row");
  if (row) {
    const company = row.dataset.company;
    if (expanded.has(company)) expanded.delete(company); else expanded.add(company);
    row.setAttribute("aria-expanded", expanded.has(company));
    row.parentElement.querySelector(".filings").hidden = !expanded.has(company);
    return;
  }
  const remove = e.target.closest("[data-remove]");
  const reindex = e.target.closest("[data-reindex]");
  try {
    if (remove) {
      if (!window.confirm(`Delete ${remove.dataset.label} from the library?\n\nIndexIt will stop searching it. ` +
        `The PDF moves to the "removed" folder, so you can add it back later.`)) return;
      await post("/api/library/remove", { file: remove.dataset.remove });
    } else if (reindex) {
      await post("/api/library/reindex", { file: reindex.dataset.reindex });
    } else return;
  } catch (error) {
    window.alert(error.message);
  }
  loadLibrary();
});

// Confirmation cards: always shown before a filing joins the library (one per file).
function renderIncoming(cards) {
  pendingNote.hidden = !cards.length;
  pendingNote.innerHTML = cards.length
    ? `${cards.length} filing${cards.length === 1 ? "" : "s"} waiting for your check · <button type="button" class="link">Review</button>` : "";
  if (!cards.length && addDialog.open && !incomingBox.hidden) addDialog.close(); // nothing left to check
  const key = cards.map((c) => c.id).join("|");
  if (incomingBox.dataset.key === key) return; // don't wipe edits the user is typing
  incomingBox.dataset.key = key;
  const addable = cards.filter((c) => !c.blocking).length;
  incomingBox.innerHTML = cards.map(cardHtml).join("") + (addable > 1
    ? `<div class="review-actions"><button type="button" class="new-btn" data-confirm-all>Add all ${addable} to library</button></div>` : "");
}

pendingNote.addEventListener("click", (e) => { if (e.target.closest("button")) openReview(); });

function cardHtml(c) {
  const source = c.source === "folder" ? "found in the library folder" : "";
  const title = c.company ? `${c.company} · FY${c.fiscal_year || "?"} 10-K` : c.file;
  const meta = [c.company ? c.file : "", c.period_end && c.period_end !== "unknown" ? `year ended ${c.period_end}` : "",
    c.pages ? `${c.pages} pages` : "", c.sec?.ticker || "", source].filter(Boolean).join(" · ");
  const okNote = c.source === "sec" ? "The cover page matches what you asked for." : "Read from the cover page. Check the company and year.";
  return `<div class="card" data-id="${escapeHtml(c.id)}">` +
    `<p class="card-title">${escapeHtml(title)}</p><p class="meta">${escapeHtml(meta)}</p>` +
    (c.warnings.length ? `<ul class="warnings">${c.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul>`
      : `<p class="ok-note">${okNote}</p>`) +
    (c.blocking ? "" : `<div class="fields"><label>Company <input name="company" value="${escapeHtml(c.company || "")}"></label>` +
      `<label>Year <input name="year" inputmode="numeric" maxlength="4" value="${c.fiscal_year || ""}"></label></div>`) +
    `<p class="add-status"></p><div class="row-actions">` +
    `<button type="button" class="link" data-cancel>${c.blocking ? "Dismiss" : "Cancel"}</button>` +
    (c.blocking ? "" : `<button type="button" class="new-btn" data-confirm>Add to library</button>`) + `</div></div>`;
}

async function confirmCard(card) {
  const company = card.querySelector('[name="company"]').value.trim();
  try {
    return await post("/api/library/confirm", { id: card.dataset.id, company, year: card.querySelector('[name="year"]').value });
  } catch (error) {
    const status = card.querySelector(".add-status");
    status.textContent = error.message;
    status.classList.add("bad");
    return null;
  }
}

incomingBox.addEventListener("click", async (e) => {
  const added = [];
  if (e.target.closest("[data-confirm-all]")) {
    for (const card of incomingBox.querySelectorAll(".card")) {
      if (card.querySelector("[data-confirm]")) added.push(await confirmCard(card));
    }
  } else {
    const card = e.target.closest(".card");
    if (!card) return;
    if (e.target.closest("[data-cancel]")) {
      await post("/api/library/cancel", { id: card.dataset.id }).catch(() => {});
    } else if (e.target.closest("[data-confirm]")) {
      added.push(await confirmCard(card));
    } else return;
  }
  incomingBox.dataset.key = "";
  await loadLibrary();
  if (added.some(Boolean)) showAdded(added.filter(Boolean));
});

// "Added to your library": what was added and roughly how long indexing takes; closes itself after 10 s.
const addedDialog = document.getElementById("added-dialog");
let addedTimer = 0;

function showAdded(results) {
  document.getElementById("added-list").innerHTML = results.map((r) => `<li>${escapeHtml(r.label)}</li>`).join("");
  const minutes = Math.max(...results.map((r) => r.minutes));
  document.getElementById("added-eta").textContent =
    `It'll take about ${minutes} minute${minutes === 1 ? "" : "s"} to IndexIt!`;
  document.getElementById("added-hint").textContent = results.length === 1
    ? "You can start asking about it in under a minute. The tables finish in the background."
    : "You can start asking about each one as soon as its text is indexed. The tables finish in the background.";
  const bar = addedDialog.querySelector(".countdown");
  bar.innerHTML = "<span></span>"; // restarts the 10-second bar
  if (!addedDialog.open) addedDialog.showModal();
  clearTimeout(addedTimer);
  addedTimer = setTimeout(() => addedDialog.close(), 10000);
}

document.getElementById("added-close").addEventListener("click", () => addedDialog.close());
addedDialog.addEventListener("close", () => clearTimeout(addedTimer));

// The add form: upload PDFs (company and year come from each cover), or fetch one from the SEC.
const method = () => addForm.querySelector('[name="method"]:checked').value;
const secFields = document.getElementById("sec-fields");
const isPdf = (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf");

function setStatus(text, bad = false) {
  addStatus.textContent = text;
  addStatus.classList.toggle("bad", bad);
}

function updateMethod() {
  drop.hidden = method() !== "upload";
  secFields.hidden = method() !== "sec";
  secBox.hidden = !(method() === "sec" && !secContactSet);
}

function chooseFiles(files) {
  chosenFiles = [...files].filter(isPdf);
  drop.classList.toggle("chosen", chosenFiles.length > 0);
  dropLabel.textContent = chosenFiles.length
    ? `${chosenFiles.length} PDF${chosenFiles.length === 1 ? "" : "s"} chosen: ${chosenFiles.map((f) => f.name).join(", ")} ·`
    : "Drop one or more PDFs here or";
}

function openAddForm(files) {
  addTitle.textContent = "Add filings";
  incomingBox.hidden = true;
  addForm.hidden = false;
  if (files) chooseFiles(files);
  updateMethod();
  if (!addDialog.open) addDialog.showModal();
  (method() === "sec" ? addForm.elements.company : addForm.querySelector('[name="method"]:checked')).focus();
}

function openReview() {
  addTitle.textContent = "Check before adding";
  addForm.hidden = true;
  incomingBox.hidden = false;
  if (!addDialog.open) addDialog.showModal();
  incomingBox.querySelector("input, button")?.focus();
}

function resetAddForm() {
  addForm.reset();
  chosenFiles = [];
  drop.classList.remove("chosen", "over");
  dropLabel.textContent = "Drop one or more PDFs here or";
  setStatus("");
  updateMethod();
}

document.getElementById("add-btn").addEventListener("click", () => openAddForm());
document.getElementById("add-cancel").addEventListener("click", () => addDialog.close());
document.getElementById("add-close").addEventListener("click", () => addDialog.close());
addDialog.addEventListener("close", resetAddForm); // anything still to check stays in the sidebar note
addForm.addEventListener("change", (e) => { if (e.target.name === "method") updateMethod(); });
fileInput.addEventListener("change", () => chooseFiles(fileInput.files));

// Dropping PDFs anywhere on the page starts adding them.
window.addEventListener("dragover", (e) => {
  if (![...e.dataTransfer.types].includes("Files")) return;
  e.preventDefault();
  if (addDialog.open) drop.classList.add("over");
});
window.addEventListener("dragleave", (e) => { if (!e.relatedTarget) drop.classList.remove("over"); });
window.addEventListener("drop", (e) => {
  if (![...e.dataTransfer.types].includes("Files")) return;
  e.preventDefault();
  drop.classList.remove("over");
  const files = [...e.dataTransfer.files].filter(isPdf);
  if (!files.length) return;
  addForm.querySelector('[value="upload"]').checked = true;
  openAddForm(files);
});

async function uploadAll() {
  if (!chosenFiles.length) throw new Error("Choose or drop at least one PDF.");
  const failed = [];
  for (const [i, file] of chosenFiles.entries()) {
    setStatus(`Reading ${chosenFiles.length > 1 ? `${i + 1} of ${chosenFiles.length}: ` : ""}${file.name}…`);
    const response = await fetch(`/api/library/upload?${new URLSearchParams({ filename: file.name })}`, { method: "POST", body: file });
    if (!response.ok) failed.push(`${file.name}: ${(await response.json().catch(() => ({}))).error || "couldn't read it"}`);
  }
  if (failed.length === chosenFiles.length) throw new Error(failed.join(" · "));
  return failed;
}

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submit = document.getElementById("add-submit");
  submit.disabled = true;
  try {
    let failed = [];
    if (method() === "upload") {
      failed = await uploadAll();
    } else {
      const company = addForm.elements.company.value.trim();
      const year = addForm.elements.year.value.trim();
      if (!company || !/^\d{4}$/.test(year)) throw new Error("Enter the company and a 4-digit fiscal year.");
      if (!secContactSet) throw new Error("Save the SEC contact email first.");
      setStatus("Fetching from the SEC and saving it as a PDF… (up to a minute)");
      await post("/api/library/fetch", { company, year });
    }
    resetAddForm();
    incomingBox.dataset.key = "";
    await loadLibrary();
    openReview();
    if (failed.length) window.alert(`Some files couldn't be read:\n${failed.join("\n")}`);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    submit.disabled = false;
  }
});

// The SEC contact: typed here, saved on this Mac by the server, never shown again.
async function saveSecContact() {
  const field = document.getElementById("sec-email");
  try {
    await post("/api/settings/sec-contact", { value: field.value });
    field.value = "";
    secContactSet = true;
    updateMethod();
    setStatus("Contact saved on this Mac.");
  } catch (error) {
    setStatus(error.message, true);
  }
}
document.getElementById("sec-save").addEventListener("click", saveSecContact);
document.getElementById("sec-email").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); saveSecContact(); }
});

// ---------- Wiring ----------

function autosize() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

form.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
input.addEventListener("input", autosize);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(input.value); }
});

document.addEventListener("click", (e) => {
  const cite = e.target.closest(".cite-page");
  if (cite) { e.preventDefault(); showPage(cite.dataset.file, Number(cite.dataset.page)); }
  const suggestion = e.target.closest(".ask-this");
  if (suggestion) ask(suggestion.textContent);
});

document.getElementById("panel-close").addEventListener("click", () => { panel.hidden = true; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") panel.hidden = true; });

document.getElementById("new-btn").addEventListener("click", async () => {
  clearThread();
  conversationId = null;
  input.value = "";
  closeSidebar();
  input.focus();
  await fetch("/api/new", { method: "POST" });
  loadHistory();
});

// Narrow windows: the left column opens as an overlay.
const sidebar = document.getElementById("sidebar");
function closeSidebar() { sidebar.classList.remove("open"); }
document.getElementById("sidebar-toggle").addEventListener("click", () => sidebar.classList.toggle("open"));

loadFilings();
loadHistory();
loadLibrary();

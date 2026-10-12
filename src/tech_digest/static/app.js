// 絞り込み・並べ替え・続きの表示・キーワード検索。
// ページは JavaScript なしでも読めるように作ってあり、ここでは表示を補助するだけ。
// 外部から来た文字列（記事のタイトルなど）は textContent でだけ画面に出す（innerHTML は使わない）。
"use strict";

document.addEventListener("DOMContentLoaded", () => {
  initDayPage();
  initSearchPage();
});

// ---- 日付ごとのページ ----

function initDayPage() {
  const controls = document.querySelector("[data-controls]");
  if (!controls) return;
  controls.hidden = false;

  const sections = [...document.querySelectorAll("[data-source]")];
  const lists = [...document.querySelectorAll("ol[data-preview]")];
  lists.forEach(applyPreview);

  for (const button of controls.querySelectorAll("[data-filter]")) {
    button.addEventListener("click", () => {
      const source = button.dataset.filter;
      for (const b of controls.querySelectorAll("[data-filter]")) {
        b.setAttribute("aria-pressed", String(b === button));
      }
      for (const section of sections) {
        section.hidden = source !== "all" && section.dataset.source !== source;
      }
    });
  }

  controls.querySelector("[data-sort]").addEventListener("change", (event) => {
    for (const list of lists) {
      sortItems(list, event.target.value);
      applyPreview(list);
    }
  });
}

function sortItems(list, key) {
  const items = [...list.children];
  const byPublished = (a, b) => b.dataset.published.localeCompare(a.dataset.published);
  const byScore = (a, b) => Number(b.dataset.score) - Number(a.dataset.score) || byPublished(a, b);
  items.sort(key === "published" ? byPublished : byScore);
  list.append(...items); // 既存の要素を並べ直すだけ（新しい HTML は作らない）
}

// 最初は data-preview 件だけ表示し、残りはボタンで開く
function applyPreview(list) {
  const limit = Number(list.dataset.preview);
  const expanded = list.dataset.expanded === "true";
  const items = [...list.children];
  items.forEach((item, i) => {
    item.hidden = !expanded && i >= limit;
  });

  let button = list.nextElementSibling;
  if (!button || !button.matches("[data-more]")) {
    if (items.length <= limit) return;
    button = document.createElement("button");
    button.type = "button";
    button.className = "more";
    button.dataset.more = "";
    button.addEventListener("click", () => {
      list.dataset.expanded = "true";
      applyPreview(list);
    });
    list.after(button);
  }
  button.textContent = `残り ${items.length - limit} 件を表示`;
  button.hidden = expanded;
}

// ---- 検索ページ ----

const MAX_RESULTS = 100;
const SOURCE_TITLES = { qiita: "Qiita", zenn: "Zenn", hatena: "はてなブックマーク" };

async function initSearchPage() {
  const root = document.querySelector("[data-search]");
  if (!root) return;
  const form = root.querySelector(".search-form");
  const input = root.querySelector("[data-search-input]");
  const sourceSelect = root.querySelector("[data-search-source]");
  const sortSelect = root.querySelector("[data-search-sort]");
  const status = root.querySelector("[data-search-status]");
  const results = root.querySelector("[data-search-results]");

  status.textContent = "読み込み中…";
  let index;
  try {
    const res = await fetch(root.dataset.index);
    if (!res.ok) throw new Error(res.status);
    index = await res.json();
  } catch {
    status.textContent = "検索データを読み込めませんでした。";
    return;
  }
  form.hidden = false;
  status.textContent = `${index.length} 件の記事から検索できます。`;

  // URL の ?q= で検索語を受け取れるようにする（ブックマークや共有用）
  input.value = new URLSearchParams(location.search).get("q") ?? "";

  let timer;
  const run = () => search(index, input.value, sourceSelect.value, sortSelect.value, status, results);
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(run, 150);
  });
  sourceSelect.addEventListener("change", run);
  sortSelect.addEventListener("change", run);
  if (input.value) run();
  input.focus();
}

function search(index, query, source, sort, status, results) {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  results.replaceChildren();
  if (terms.length === 0) {
    status.textContent = `${index.length} 件の記事から検索できます。`;
    return;
  }

  const hits = index.filter((a) => {
    if (source && a.s !== source) return false;
    const text = (a.t + " " + a.g.join(" ")).toLowerCase();
    return terms.every((term) => text.includes(term));
  });
  hits.sort(sort === "date"
    ? (a, b) => b.d.localeCompare(a.d) || (b.c ?? -1) - (a.c ?? -1)
    : (a, b) => (b.c ?? -1) - (a.c ?? -1) || b.d.localeCompare(a.d));

  status.textContent = hits.length > MAX_RESULTS
    ? `${hits.length} 件見つかりました（上位 ${MAX_RESULTS} 件を表示）。`
    : `${hits.length} 件見つかりました。`;
  results.append(...hits.slice(0, MAX_RESULTS).map(resultItem));
}

function resultItem(a) {
  const li = document.createElement("li");
  li.className = "article";

  const title = document.createElement(isHttpUrl(a.u) ? "a" : "span");
  title.className = "title";
  title.textContent = a.t;
  if (title instanceof HTMLAnchorElement) {
    title.href = a.u;
    title.rel = "noopener noreferrer";
  }

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.append(span("source", SOURCE_TITLES[a.s] ?? a.s));
  if (a.c !== null && a.c !== undefined && a.s !== "zenn") meta.append(span("score", String(a.c)));
  const day = document.createElement("a");
  day.href = `days/${encodeURIComponent(a.d)}.html`;
  day.textContent = a.d;
  meta.append(day);
  for (const tag of a.g) meta.append(span("tag", tag));

  li.append(title, meta);
  return li;
}

function span(className, text) {
  const el = document.createElement("span");
  el.className = className;
  el.textContent = text;
  return el;
}

function isHttpUrl(url) {
  return /^https?:\/\//i.test(url);
}

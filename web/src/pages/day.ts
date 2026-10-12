import { ApiError, type Article, type Source, getDay, getDays, getSources } from "../api";
import { h } from "../dom";
import { type ArticleSort, dateLabel, shortDateLabel, sortArticles } from "../format";
import { dayHref } from "../router";
import { articleItem, publishedTime, scoreLabel, span, tags } from "./common";

const PREVIEW_ITEMS = 30; // 1 つの取得元で最初に表示する件数（残りはボタンで開く）

// 日付のページ。date が null なら最新の日
export async function dayPage(date: string | null): Promise<Node[]> {
  const [sources, days] = await Promise.all([getSources(), getDays()]);
  const target = date ?? days[0]?.date;
  if (!target) {
    document.title = "技術ブログダイジェスト";
    return [
      h("h1", {}, "技術ブログダイジェスト"),
      h("p", { class: "empty" }, "まだダイジェストがありません。最初の実行をお待ちください。"),
    ];
  }

  let articles: Article[];
  try {
    articles = (await getDay(target)).articles;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      document.title = "ページが見つかりません - 技術ブログダイジェスト";
      return [h("h1", {}, dateLabel(target)), h("p", { class: "empty" }, "この日のダイジェストはありません。")];
    }
    throw error;
  }
  document.title = `${target} の技術ブログダイジェスト`;

  // 一覧は新しい順なので、前の要素が「新しい日」、次の要素が「古い日」
  const index = days.findIndex((d) => d.date === target);
  const newer = index > 0 ? days[index - 1] : undefined;
  const older = index >= 0 ? days[index + 1] : undefined;

  const state = { filter: "all", sort: "score" as ArticleSort, expanded: new Set<string>() };
  const sectionsRoot = h("div");
  const render = () => {
    const visible = sources.filter((s) => state.filter === "all" || s.name === state.filter);
    sectionsRoot.replaceChildren(
      ...visible.map((s) =>
        section(s, articles.filter((a) => a.source === s.name), state, () => {
          state.expanded.add(s.name);
          render();
        }),
      ),
    );
  };
  render();

  const filterButtons = [{ name: "all", title: "すべて" }, ...sources].map((s) => {
    const pressed = String(s.name === "all");
    const button = h("button", { type: "button", "aria-pressed": pressed }, s.title);
    button.addEventListener("click", () => {
      state.filter = s.name;
      for (const b of filterButtons) b.setAttribute("aria-pressed", String(b === button));
      render();
    });
    return button;
  });

  const sortSelect = h(
    "select",
    {},
    h("option", { value: "score" }, "人気順"),
    h("option", { value: "published" }, "新着順"),
  );
  sortSelect.addEventListener("change", () => {
    state.sort = sortSelect.value === "published" ? "published" : "score";
    render();
  });

  return [
    h(
      "div",
      { class: "day-header" },
      h("h1", {}, dateLabel(target), h("span", { class: "count" }, `${articles.length} 件`)),
      h(
        "nav",
        { class: "pager", "aria-label": "日付の移動" },
        older ? h("a", { href: dayHref(older.date) }, `← ${shortDateLabel(older.date)}`) : null,
        newer ? h("a", { href: dayHref(newer.date) }, `${shortDateLabel(newer.date)} →`) : null,
      ),
    ),
    h(
      "div",
      { class: "controls" },
      h("div", { class: "filter", role: "group", "aria-label": "取得元で絞り込み" }, ...filterButtons),
      h("label", { class: "sort" }, "並び順", sortSelect),
    ),
    sectionsRoot,
  ];
}

function section(
  source: Source,
  articles: Article[],
  state: { sort: ArticleSort; expanded: Set<string> },
  expand: () => void,
): HTMLElement {
  const heading = h(
    "h2",
    {},
    source.title,
    h("span", { class: "desc" }, `${source.description}・${articles.length} 件`),
  );
  if (articles.length === 0) {
    const empty = h("p", { class: "empty" }, "新しい記事はありませんでした。");
    return h("section", { class: "source-section" }, heading, empty);
  }

  const sorted = sortArticles(articles, state.sort);
  const shown = state.expanded.has(source.name) ? sorted : sorted.slice(0, PREVIEW_ITEMS);
  const list = h(
    "ol",
    { class: "articles" },
    ...shown.map((a) =>
      articleItem(a, [
        span("score", scoreLabel(a, source)),
        span("author", a.author),
        publishedTime(a),
        ...tags(a),
      ]),
    ),
  );

  let more: HTMLButtonElement | null = null;
  if (shown.length < sorted.length) {
    const label = `残り ${sorted.length - shown.length} 件を表示`;
    more = h("button", { type: "button", class: "more" }, label);
    more.addEventListener("click", expand);
  }
  return h("section", { class: "source-section" }, heading, list, more);
}

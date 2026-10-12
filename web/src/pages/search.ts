import { ApiError, type SearchResponse, getSources, search } from "../api";
import { h } from "../dom";
import { dayHref, type Route, searchHref } from "../router";
import { articleItem, scoreLabel, span, tags } from "./common";

const SEARCH_DAYS = 30; // API の routes.SEARCH_DAYS と同じ

type SearchRoute = Extract<Route, { page: "search" }>;

// 検索は API 側で行う（1 回で直近 30 日分を読むので、入力のたびではなく「検索」を押したときだけ呼ぶ）。
// 条件は URL（#/search?q=...）に入れる。戻るボタンで前の検索に戻れて、URL を共有もできる
export async function searchPage(route: SearchRoute): Promise<Node[]> {
  const sources = await getSources();
  document.title = route.q
    ? `「${route.q}」の検索結果 - 技術ブログダイジェスト`
    : "検索 - 技術ブログダイジェスト";

  const input = h("input", {
    type: "search",
    name: "q",
    placeholder: "例: Docker, Terraform, Python",
    "aria-label": "キーワード",
    autocomplete: "off",
    maxlength: "100",
  });
  input.value = route.q;
  const sourceSelect = h(
    "select",
    { "aria-label": "取得元" },
    h("option", { value: "" }, "すべて"),
    ...sources.map((s) => h("option", { value: s.name }, s.title)),
  );
  sourceSelect.value = route.source;
  const sortSelect = h(
    "select",
    { "aria-label": "並び順" },
    h("option", { value: "score" }, "人気順"),
    h("option", { value: "date" }, "新着順"),
  );
  sortSelect.value = route.sort;

  const submit = h("button", { type: "submit" }, "検索");
  const form = h(
    "form",
    { class: "search-form", role: "search" },
    input,
    sourceSelect,
    sortSelect,
    submit,
  );
  const go = () => {
    const sort = sortSelect.value === "date" ? "date" : "score";
    location.hash = searchHref(input.value.trim(), sourceSelect.value, sort);
  };
  form.addEventListener("submit", (event) => {
    event.preventDefault(); // フォームの送信（ページの移動）はせず、URL の # だけ変える
    go();
  });
  // 絞り込みと並び順は、検索語があればすぐに反映する
  for (const select of [sourceSelect, sortSelect]) {
    select.addEventListener("change", () => {
      if (input.value.trim()) go();
    });
  }
  if (!route.q) requestAnimationFrame(() => input.focus());

  const status = h("p", { class: "search-status", "aria-live": "polite" });
  const results = h("ol", { class: "articles" });
  const note = `直近 ${SEARCH_DAYS} 日分の記事を、タイトルとタグから探します。`;
  const nodes = [h("h1", {}, "検索"), h("p", { class: "note" }, note), form, status, results];
  if (!route.q) return nodes;

  let response: SearchResponse;
  try {
    response = await search(route.q, route.source, route.sort);
  } catch (error) {
    // 検索語が長すぎるなどの 400 は、理由をそのまま見せる
    if (error instanceof ApiError && error.status === 400) {
      status.append(error.message);
      return nodes;
    }
    throw error;
  }

  const titles = new Map(sources.map((s) => [s.name, s]));
  status.append(
    response.total > response.articles.length
      ? `${response.total} 件見つかりました（上位 ${response.articles.length} 件を表示）。`
      : `${response.total} 件見つかりました。`,
  );
  results.append(
    ...response.articles.map((a) => {
      const source = titles.get(a.source);
      return articleItem(a, [
        span("source", source?.title ?? a.source),
        span("score", scoreLabel(a, source)),
        h("a", { href: dayHref(a.date) }, a.date),
        ...tags(a),
      ]);
    }),
  );
  return nodes;
}

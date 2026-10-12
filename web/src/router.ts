// URL の # 以降でページを切り替える（ハッシュルーティング）。
// # 以降はサーバーに送られないので、S3 や GitHub Pages に index.html を 1 つ置くだけで、
// どのページの URL を直接開いても動く（/days/... のような普通のパスにすると、
// 存在しないパスを index.html に向ける設定がサーバー側に要る）

import type { SearchSort } from "./api";

export type Route =
  | { page: "latest" }
  | { page: "day"; date: string }
  | { page: "archive" }
  | { page: "search"; q: string; source: string; sort: SearchSort }
  | { page: "notFound" };

export function parseRoute(hash: string): Route {
  const target = hash.replace(/^#/, "");
  const separator = target.indexOf("?");
  const path = separator === -1 ? target : target.slice(0, separator);
  const query = new URLSearchParams(separator === -1 ? "" : target.slice(separator + 1));

  if (path === "" || path === "/") return { page: "latest" };
  if (path === "/archive") return { page: "archive" };
  if (path === "/search") {
    return {
      page: "search",
      q: query.get("q") ?? "",
      source: query.get("source") ?? "",
      sort: query.get("sort") === "date" ? "date" : "score",
    };
  }
  const day = /^\/days\/(\d{4}-\d{2}-\d{2})$/.exec(path);
  if (day?.[1]) return { page: "day", date: day[1] };
  return { page: "notFound" };
}

export function dayHref(date: string): string {
  return `#/days/${encodeURIComponent(date)}`;
}

export function searchHref(q: string, source: string, sort: SearchSort): string {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (source) params.set("source", source);
  if (sort !== "score") params.set("sort", sort);
  const query = params.toString();
  return query ? `#/search?${query}` : "#/search";
}

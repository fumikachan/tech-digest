import type { Article, Source } from "../api";
import { externalLink, h } from "../dom";
import { publishedLabel } from "../format";

export const MAX_TAGS = 3;

export function scoreLabel(article: Article, source: Source | undefined): string | null {
  // スコアの単位がない取得元（Zenn）は数字だけでは意味が伝わらないので出さない
  if (article.score === null || !source?.score_unit) return null;
  return `${article.score} ${source.score_unit}`;
}

// 記事 1 件。meta はタイトルの下に並べる情報（ページごとに違う）
export function articleItem(article: Article, meta: (Node | null)[]): HTMLLIElement {
  return h(
    "li",
    { class: "article" },
    externalLink(article.url, article.title, "title"),
    h("div", { class: "meta" }, ...meta),
  );
}

export function publishedTime(article: Article): HTMLTimeElement {
  return h("time", { datetime: article.published_at }, publishedLabel(article.published_at));
}

export function tags(article: Article): HTMLSpanElement[] {
  return article.tags.slice(0, MAX_TAGS).map((tag) => h("span", { class: "tag" }, tag));
}

export function span(className: string, text: string | null): HTMLSpanElement | null {
  return text === null ? null : h("span", { class: className }, text);
}

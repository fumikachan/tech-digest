import type { Article } from "./api";

export type ArticleSort = "score" | "published";

// "2026-10-13" → "2026年10月13日"
export function dateLabel(date: string): string {
  const [year, month, day] = date.split("-").map(Number);
  return `${year}年${month}月${day}日`;
}

// "2026-10-13" → "10/13"
export function shortDateLabel(date: string): string {
  const [, month, day] = date.split("-").map(Number);
  return `${month}/${day}`;
}

const publishedFormat = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

// "2026-10-11T00:30:00+00:00" → "10/11 09:30"（日本時間。見る人の PC のタイムゾーンによらない）
export function publishedLabel(iso: string): string {
  return publishedFormat.format(new Date(iso));
}

// 人気順はスコアの高い順（スコアのないものは最後）、同じなら新しい順。新着順は公開日時の新しい順
export function sortArticles<T extends Article>(articles: readonly T[], sort: ArticleSort): T[] {
  const byPublished = (a: T, b: T) => b.published_at.localeCompare(a.published_at);
  const byScore = (a: T, b: T) => (b.score ?? -1) - (a.score ?? -1) || byPublished(a, b);
  return [...articles].sort(sort === "score" ? byScore : byPublished);
}

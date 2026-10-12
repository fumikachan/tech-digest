import { describe, expect, it } from "vitest";
import type { Article } from "./api";
import { dateLabel, publishedLabel, shortDateLabel, sortArticles } from "./format";

function article(title: string, score: number | null, published_at: string): Article {
  return { source: "qiita", url: null, title, author: null, score, tags: [], published_at };
}

describe("labels", () => {
  it("formats dates", () => {
    expect(dateLabel("2026-10-03")).toBe("2026年10月3日");
    expect(shortDateLabel("2026-10-03")).toBe("10/3");
  });

  it("shows published time in JST regardless of the viewer's time zone", () => {
    // UTC の 10/11 15:30 は、日本時間では 10/12 00:30
    expect(publishedLabel("2026-10-11T15:30:00+00:00")).toBe("10/12 00:30");
  });
});

describe("sortArticles", () => {
  const articles = [
    article("old-high", 50, "2026-10-10T00:00:00+00:00"),
    article("none", null, "2026-10-12T00:00:00+00:00"),
    article("new-high", 50, "2026-10-11T00:00:00+00:00"),
    article("low", 1, "2026-10-09T00:00:00+00:00"),
  ];

  it("orders by score, nulls last, then newest", () => {
    expect(sortArticles(articles, "score").map((a) => a.title)).toEqual([
      "new-high",
      "old-high",
      "low",
      "none",
    ]);
  });

  it("orders by published time", () => {
    expect(sortArticles(articles, "published").map((a) => a.title)).toEqual([
      "none",
      "new-high",
      "old-high",
      "low",
    ]);
  });

  it("does not change the input", () => {
    sortArticles(articles, "published");
    expect(articles[0]?.title).toBe("old-high");
  });
});

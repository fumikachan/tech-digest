import { describe, expect, it } from "vitest";
import { dayHref, parseRoute, searchHref } from "./router";

describe("parseRoute", () => {
  it.each([
    ["", { page: "latest" }],
    ["#/", { page: "latest" }],
    ["#/archive", { page: "archive" }],
    ["#/days/2026-10-13", { page: "day", date: "2026-10-13" }],
    ["#/days/2026-10-13/x", { page: "notFound" }],
    ["#/days/abc", { page: "notFound" }],
    ["#/nope", { page: "notFound" }],
  ])("%s", (hash, route) => {
    expect(parseRoute(hash)).toEqual(route);
  });

  it("reads search conditions and falls back to score order", () => {
    expect(parseRoute("#/search?q=aws%20lambda&source=qiita&sort=date")).toEqual({
      page: "search",
      q: "aws lambda",
      source: "qiita",
      sort: "date",
    });
    expect(parseRoute("#/search?sort=unknown")).toEqual({
      page: "search",
      q: "",
      source: "",
      sort: "score",
    });
  });
});

describe("hrefs", () => {
  it("round-trips search conditions", () => {
    const href = searchHref("C# & .NET", "", "date");
    expect(parseRoute(href)).toMatchObject({ q: "C# & .NET", source: "", sort: "date" });
  });

  it("omits defaults", () => {
    expect(searchHref("", "", "score")).toBe("#/search");
    expect(dayHref("2026-10-13")).toBe("#/days/2026-10-13");
  });
});

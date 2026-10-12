import { getDays, getSources } from "../api";
import { h } from "../dom";
import { dayHref } from "../router";

export async function archivePage(): Promise<Node[]> {
  const [sources, days] = await Promise.all([getSources(), getDays()]);
  document.title = "アーカイブ - 技術ブログダイジェスト";
  if (days.length === 0) {
    return [h("h1", {}, "アーカイブ"), h("p", { class: "empty" }, "まだダイジェストがありません。")];
  }
  return [
    h("h1", {}, "アーカイブ"),
    h(
      "table",
      { class: "archive" },
      h(
        "thead",
        {},
        h(
          "tr",
          {},
          h("th", { scope: "col" }, "日付"),
          ...sources.map((s) => h("th", { scope: "col" }, s.title)),
        ),
      ),
      h(
        "tbody",
        {},
        ...days.map((d) =>
          h(
            "tr",
            {},
            h("td", {}, h("a", { href: dayHref(d.date) }, d.date.replaceAll("-", "/"))),
            ...sources.map((s) => h("td", { class: "num" }, d.counts[s.name] ?? 0)),
          ),
        ),
      ),
    ),
  ];
}

import { ApiError } from "./api";
import { h } from "./dom";
import { archivePage } from "./pages/archive";
import { dayPage } from "./pages/day";
import { searchPage } from "./pages/search";
import { type Route, parseRoute } from "./router";

const app = document.getElementById("app");
if (!app) throw new Error("#app がありません");
const root = app;

function page(route: Route): Promise<Node[]> {
  switch (route.page) {
    case "latest":
      return dayPage(null);
    case "day":
      return dayPage(route.date);
    case "archive":
      return archivePage();
    case "search":
      return searchPage(route);
    case "notFound":
      document.title = "ページが見つかりません - 技術ブログダイジェスト";
      return Promise.resolve([
        h("h1", {}, "ページが見つかりません"),
        h("p", {}, h("a", { href: "#/" }, "最新のダイジェストへ")),
      ]);
  }
}

let current = 0;

async function render(): Promise<void> {
  const id = ++current;
  root.replaceChildren(h("p", { class: "note" }, "読み込み中…"));
  try {
    const nodes = await page(parseRoute(location.hash));
    // 読み込みの途中で別のページに移っていたら、古いページの結果は捨てる
    if (id !== current) return;
    root.replaceChildren(...nodes);
  } catch (error) {
    if (id !== current) return;
    console.error(error);
    root.replaceChildren(
      h("h1", {}, "読み込めませんでした"),
      h("p", { class: "empty" }, error instanceof ApiError ? error.message : "予期しないエラーが起きました。"),
      h("p", { class: "note" }, "時間をおいて、ページを再読み込みしてください。"),
    );
  }
}

window.addEventListener("hashchange", () => {
  void render();
  window.scrollTo(0, 0);
});
void render();

// 画面の要素はすべてここで作る。
// 外部から来た文字列（記事のタイトルなど）は append でテキストノードとして入れるだけで、
// HTML として解釈させない（textContent と同じ。innerHTML は使わない）。

type Child = Node | string | number | null | undefined | false;

export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  // 属性の値はコードの中で決めたものだけを渡す（外部の URL は externalLink を通す）
  for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    element.append(typeof child === "number" ? String(child) : child);
  }
  return element;
}

export function isHttpUrl(url: string | null): url is string {
  return url !== null && /^https?:\/\//i.test(url);
}

// 外部サイトへのリンク。http(s) 以外（javascript: など）はリンクにせず文字だけにする。
// API でも同じ確認をしているが、画面側でも確かめる（どちらかに漏れがあっても防げるように）
export function externalLink(url: string | null, text: string, className: string): HTMLElement {
  if (!isHttpUrl(url)) return h("span", { class: className }, text);
  return h("a", { class: className, href: url, rel: "noopener noreferrer" }, text);
}

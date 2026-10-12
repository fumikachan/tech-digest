// API の呼び出しと、レスポンスの型。
// 型は docs/API_DESIGN.md と src/tech_digest/api/routes.py に合わせる（API を変えたらここも直す）

export interface Source {
  name: string;
  title: string;
  description: string;
  score_unit: string | null;
}

export interface Article {
  source: string;
  url: string | null; // http(s) 以外は API が null にする
  title: string;
  author: string | null;
  score: number | null;
  tags: string[];
  published_at: string; // ISO 8601（UTC）
}

export interface DaySummary {
  date: string; // YYYY-MM-DD
  counts: Record<string, number>;
}

export interface DayResponse {
  date: string;
  articles: Article[];
}

export interface SearchHit extends Article {
  date: string;
}

export interface SearchResponse {
  total: number;
  articles: SearchHit[];
}

export type SearchSort = "score" | "date";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

async function get<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE_URL + path, { headers: { accept: "application/json" } });
  } catch {
    throw new ApiError(0, "API に接続できませんでした。");
  }
  if (!response.ok) {
    // 400 や 404 では API が理由を message に入れて返す
    let message = `API がエラーを返しました（${response.status}）。`;
    try {
      const body: unknown = await response.json();
      if (typeof body === "object" && body !== null && "message" in body) {
        if (typeof body.message === "string") message = body.message;
      }
    } catch {
      // 本文が JSON でなければ既定のメッセージのまま
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

// 取得元と日付の一覧はページを移っても変わらないので、1 回だけ取得して使い回す（失敗したら次は取り直す）
let sources: Promise<Source[]> | undefined;
let days: Promise<DaySummary[]> | undefined;

export function getSources(): Promise<Source[]> {
  sources ??= get<{ sources: Source[] }>("/sources").then(
    (body) => body.sources,
    (error: unknown) => {
      sources = undefined;
      throw error;
    },
  );
  return sources;
}

export function getDays(): Promise<DaySummary[]> {
  days ??= get<{ days: DaySummary[] }>("/days").then(
    (body) => body.days,
    (error: unknown) => {
      days = undefined;
      throw error;
    },
  );
  return days;
}

export function getDay(date: string): Promise<DayResponse> {
  return get<DayResponse>(`/days/${encodeURIComponent(date)}`);
}

export function search(q: string, source: string, sort: SearchSort): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, sort });
  if (source) params.set("source", source);
  return get<SearchResponse>(`/search?${params}`);
}

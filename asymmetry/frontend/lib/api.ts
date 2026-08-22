import {
  MOCK_AGENT_RUNS,
  MOCK_CANDIDATES,
  MOCK_DETAILS,
  MOCK_SIGNALS,
  MOCK_SIGNAL_ATTRIBUTION,
  MOCK_STATS,
  MOCK_THESES,
  MOCK_TOP,
} from "./mockData";
import type {
  AgentRun,
  Candidate,
  CandidateDetail,
  CandidateList,
  CandidateQuery,
  DashboardStats,
  Signal,
  ThesisEntry,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Tracks whether the last read came from the live API or from the bundled
 * research fixtures. Pages surface this so a reader is never misled about
 * where a number came from.
 */
export type DataSource = "live" | "fixtures";

export interface Result<T> {
  data: T;
  source: DataSource;
  error: string | null;
}

const TIMEOUT_MS = 2500;

async function get<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      cache: "no-store",
      headers: { accept: "application/json" },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

async function withFallback<T>(
  path: string,
  fallback: () => T,
): Promise<Result<T>> {
  try {
    const data = await get<T>(path);
    return { data, source: "live", error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { data: fallback(), source: "fixtures", error: message };
  }
}

function qs(query: CandidateQuery): string {
  const p = new URLSearchParams();
  if (query.limit !== undefined) p.set("limit", String(query.limit));
  if (query.offset !== undefined) p.set("offset", String(query.offset));
  if (query.verdict) p.set("verdict", query.verdict);
  if (query.sector) p.set("sector", query.sector);
  if (query.q) p.set("q", query.q);
  const s = p.toString();
  return s ? `?${s}` : "";
}

function filterMock(query: CandidateQuery): CandidateList {
  let items = MOCK_CANDIDATES;
  if (query.verdict) items = items.filter((c) => c.verdict === query.verdict);
  if (query.sector) items = items.filter((c) => c.sector === query.sector);
  if (query.q) {
    const needle = query.q.toLowerCase();
    items = items.filter(
      (c) =>
        c.name.toLowerCase().includes(needle) ||
        (c.ticker ?? "").toLowerCase().includes(needle) ||
        c.sector.toLowerCase().includes(needle) ||
        c.description.toLowerCase().includes(needle),
    );
  }
  const total = items.length;
  const offset = query.offset ?? 0;
  const limit = query.limit ?? total;
  return { items: items.slice(offset, offset + limit), total };
}

export function getStats(): Promise<Result<DashboardStats>> {
  return withFallback<DashboardStats>("/api/stats", () => MOCK_STATS);
}

export function getCandidates(
  query: CandidateQuery = {},
): Promise<Result<CandidateList>> {
  return withFallback<CandidateList>(`/api/candidates${qs(query)}`, () =>
    filterMock(query),
  );
}

export async function getCandidate(
  id: string,
): Promise<Result<CandidateDetail | null>> {
  return withFallback<CandidateDetail | null>(
    `/api/candidates/${encodeURIComponent(id)}`,
    () => MOCK_DETAILS[id] ?? null,
  );
}

export function getTopOpportunities(limit = 10): Promise<Result<Candidate[]>> {
  return withFallback<Candidate[]>(`/api/opportunities/top?limit=${limit}`, () =>
    MOCK_TOP.slice(0, limit),
  );
}

export function getSignals(limit = 50): Promise<Result<Signal[]>> {
  return withFallback<Signal[]>(`/api/signals?limit=${limit}`, () =>
    MOCK_SIGNALS.slice(0, limit),
  );
}

export function getTheses(): Promise<Result<ThesisEntry[]>> {
  return withFallback<ThesisEntry[]>("/api/theses", () => MOCK_THESES);
}

export function getAgentRuns(limit = 50): Promise<Result<AgentRun[]>> {
  return withFallback<AgentRun[]>(`/api/agent-runs?limit=${limit}`, () =>
    MOCK_AGENT_RUNS.slice(0, limit),
  );
}

export interface AttributedSignal {
  signal: Signal;
  candidate_id: string | null;
  candidate_name: string | null;
  ticker: string | null;
}

/**
 * The `/api/signals` contract returns bare signals. Where a signal can be
 * matched back to a candidate we attach the attribution so the feed is
 * readable; unmatched signals still render, just without a name.
 */
export async function getSignalFeed(
  limit = 50,
): Promise<Result<AttributedSignal[]>> {
  const res = await getSignals(limit);
  const attributed = res.data.map((signal) => {
    // The live feed carries its own attribution, so use it directly. The
    // description lookup is only a fallback for fixtures, which have no
    // candidate fields on the signal itself.
    if (signal.candidate_id && signal.candidate_name) {
      return {
        signal,
        candidate_id: signal.candidate_id,
        candidate_name: signal.candidate_name,
        ticker: MOCK_SIGNAL_ATTRIBUTION[signal.description]?.ticker ?? null,
      };
    }
    const hit = MOCK_SIGNAL_ATTRIBUTION[signal.description];
    return {
      signal,
      candidate_id: hit?.candidate_id ?? null,
      candidate_name: hit?.candidate_name ?? null,
      ticker: hit?.ticker ?? null,
    };
  });
  return { data: attributed, source: res.source, error: res.error };
}

/**
 * バックエンド API クライアント。
 * next.config.ts の rewrite により /api/* → FastAPI に転送される。
 */
import type { StatusResponse, AlertMessage } from "@/types/quakemind";

const BASE = "/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 30 } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  getStatus: () => fetchJson<StatusResponse>("/status"),
  getLatestAlert: () => fetchJson<AlertMessage>("/alert/latest"),
};

import { invoke } from "@tauri-apps/api/core";

export type BackendConfig = { url: string; token: string; wsUrl: string };
let configPromise: Promise<BackendConfig> | null = null;

export function backendConfig(): Promise<BackendConfig> {
  if (!configPromise) {
    configPromise = ("__TAURI_INTERNALS__" in window
      ? invoke<{ url: string; token: string; ws_url: string }>("backend_config").then(c => ({ url: c.url, token: c.token, wsUrl: c.ws_url }))
      : Promise.resolve({
          url: import.meta.env.VITE_API_URL || "http://127.0.0.1:8765",
          token: import.meta.env.VITE_API_TOKEN || "dev-token",
          wsUrl: import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8765",
        }));
  }
  return configPromise;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const config = await backendConfig();
  const headers = new Headers(init.headers);
  headers.set("X-OAT-Token", config.token);
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`${config.url}/api/v1${path}`, { ...init, headers });
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try { const body = await response.json(); message = body.detail || message; } catch { /* 非 JSON 错误 */ }
    throw new Error(Array.isArray(message) ? message.map((item: { msg: string }) => item.msg).join("；") : message);
  }
  return response.json() as Promise<T>;
}

export async function apiBlob(path: string): Promise<Blob> {
  const config = await backendConfig();
  const response = await fetch(`${config.url}/api/v1${path}`, { headers: { "X-OAT-Token": config.token } });
  if (!response.ok) throw new Error("窗口预览失败");
  return response.blob();
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return api<T>(path, { method: "POST", ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
}

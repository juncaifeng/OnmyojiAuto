import { useEffect, useRef, useState } from "react";
import { Bot, GalleryVerticalEnd, Home, Layers3, Settings as SettingsIcon } from "lucide-react";
import { api, backendConfig } from "@/lib/api";
import type { AppEvent, LogRecord, Settings, SyncState, TaskState } from "@/lib/types";
import { cn } from "@/lib/utils";
import HomePage from "@/pages/HomePage";
import SyncPage from "@/pages/SyncPage";
import MultiPage from "@/pages/MultiPage";
import SettingsPage from "@/pages/SettingsPage";

type Page = "home" | "sync" | "multi" | "settings";
const navigation = [
  { id: "home" as const, label: "自动化", icon: Home },
  { id: "sync" as const, label: "窗口同步", icon: Layers3 },
  { id: "multi" as const, label: "多开管理", icon: GalleryVerticalEnd },
  { id: "settings" as const, label: "设置", icon: SettingsIcon },
];
const emptyTask: TaskState = { status: "idle", error: null, done: 0, total: 0, paused: false, request: null };

export default function App() {
  const [page, setPage] = useState<Page>("home");
  const [task, setTask] = useState<TaskState>(emptyTask);
  const [sync, setSync] = useState<SyncState>({ enabled: false, main_hwnd: null, sub_hwnds: [] });
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [connected, setConnected] = useState(false);
  const seenEvents = useRef(new Set<string>());

  useEffect(() => {
    api<Settings>("/settings").then(s => document.documentElement.classList.toggle("dark", s.theme === "dark")).catch(() => undefined);
    api<TaskState>("/tasks/current").then(setTask).catch(() => undefined);
    api<SyncState>("/sync").then(setSync).catch(() => undefined);
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;
    const connect = async () => {
      const config = await backendConfig();
      if (disposed) return;
      socket = new WebSocket(`${config.wsUrl}/api/v1/events?token=${encodeURIComponent(config.token)}`);
      socket.onopen = () => setConnected(true);
      socket.onclose = () => { setConnected(false); if (!disposed) retry = setTimeout(connect, 1500); };
      socket.onmessage = message => {
        const event = JSON.parse(message.data) as AppEvent;
        const key = `${event.type}:${event.timestamp}:${JSON.stringify(event.data)}`;
        if (seenEvents.current.has(key)) return;
        seenEvents.current.add(key);
        if (seenEvents.current.size > 1000) seenEvents.current.clear();
        if (event.type === "log") setLogs(old => [...old.slice(-499), event.data as LogRecord]);
        if (event.type === "task") setTask(event.data as TaskState);
        if (event.type === "progress") {
          const progress = event.data as { done: number; total: number };
          setTask(old => ({ ...old, ...progress }));
        }
      };
    };
    connect().catch(() => { if (!disposed) retry = setTimeout(connect, 1500); });
    return () => { disposed = true; if (retry) clearTimeout(retry); socket?.close(); };
  }, []);

  return <div className="flex h-screen overflow-hidden">
    <aside className="flex w-52 shrink-0 flex-col border-r bg-card/60 p-4">
      <div className="mb-8 flex items-center gap-3 px-2">
        <div className="rounded-xl bg-primary p-2 text-primary-foreground"><Bot className="h-5 w-5" /></div>
        <div><div className="font-bold tracking-tight">OnmyojiAuto</div><div className="text-xs text-muted-foreground">自动化工作台</div></div>
      </div>
      <nav className="space-y-1">{navigation.map(item => <button key={item.id} onClick={() => setPage(item.id)} className={cn("flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors", page === item.id ? "bg-accent font-medium text-accent-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground")}><item.icon className="h-4 w-4" />{item.label}</button>)}</nav>
      <div className="mt-auto flex items-center gap-2 px-3 text-xs text-muted-foreground"><span className={cn("h-2 w-2 rounded-full", connected ? "bg-emerald-500" : "bg-amber-500")} />{connected ? "后端已连接" : "正在连接后端"}</div>
    </aside>
    <main className="min-w-0 flex-1 overflow-y-auto">
      {page === "home" && <HomePage task={task} setTask={setTask} logs={logs} syncEnabled={sync.enabled} />}
      {page === "sync" && <SyncPage sync={sync} setSync={setSync} />}
      {page === "multi" && <MultiPage />}
      {page === "settings" && <SettingsPage />}
    </main>
  </div>;
}

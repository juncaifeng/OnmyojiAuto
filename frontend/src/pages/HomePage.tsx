import { useCallback, useEffect, useRef, useState } from "react";
import { Pause, Play, RefreshCw, Square } from "lucide-react";
import { api, post } from "@/lib/api";
import type { Client, LogRecord, Mode, TaskState } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

const statusText = { idle: "空闲", running: "运行中", paused: "已暂停", stopping: "正在停止", stopped: "已停止", completed: "已完成", failed: "失败" };
type Props = { task: TaskState; setTask: (task: TaskState) => void; logs: LogRecord[]; syncEnabled: boolean };

export default function HomePage({ task, setTask, logs, syncEnabled }: Props) {
  const [modes, setModes] = useState<Mode[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [mode, setMode] = useState("");
  const [subMode, setSubMode] = useState("");
  const [clientId, setClientId] = useState("");
  const [times, setTimes] = useState(1);
  const [hidden, setHidden] = useState(true);
  const [syncMode, setSyncMode] = useState(false);
  const [exploreOnly, setExploreOnly] = useState(false);
  const [exploreCount, setExploreCount] = useState(5);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const logEnd = useRef<HTMLDivElement>(null);
  const currentMode = modes.find(item => item.name === mode);
  const running = ["running", "paused", "stopping"].includes(task.status);

  const refreshClients = useCallback(async () => {
    try { const data = await api<Client[]>("/clients"); setClients(data); setClientId(old => data.some(c => c.id === old) ? old : data[0]?.id || ""); }
    catch (e) { setError((e as Error).message); }
  }, []);
  useEffect(() => {
    api<Mode[]>("/modes").then(data => { setModes(data); setMode(data[0]?.name || ""); }).catch(e => setError(e.message));
    refreshClients();
  }, [refreshClients]);
  useEffect(() => { setSubMode(currentMode?.sub_modes[0] || ""); }, [mode, modes]);
  useEffect(() => { logEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  const start = async () => {
    const client = clients.find(item => item.id === clientId);
    if (!client) { setError("请先刷新并选择游戏窗口"); return; }
    setSubmitting(true); setError("");
    try { setTask(await post<TaskState>("/tasks/start", { mode, sub_mode: subMode, times, client: { hwnd: client.hwnd, title: client.title }, hidden_window: hidden, sync_mode: syncMode, explore_per_round: exploreCount, explore_only: exploreOnly })); }
    catch (e) { setError((e as Error).message); } finally { setSubmitting(false); }
  };
  const control = async (action: "pause" | "resume" | "stop") => {
    try { setTask(await post<TaskState>(`/tasks/${action}`)); } catch (e) { setError((e as Error).message); }
  };
  const percent = task.total ? Math.round(task.done / task.total * 100) : 0;

  return <div className="p-7">
    <header className="mb-6 flex items-center justify-between"><div><h1 className="text-2xl font-bold tracking-tight">自动化任务</h1><p className="mt-1 text-sm text-muted-foreground">选择副本与客户端，剩下的交给 OAT。</p></div><Badge variant={task.status === "failed" ? "destructive" : "secondary"}>{statusText[task.status]}</Badge></header>
    {error && <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>}
    <div className="grid gap-5 xl:grid-cols-[minmax(340px,0.85fr)_minmax(400px,1.15fr)]">
      <Card><CardHeader><CardTitle>任务配置</CardTitle><CardDescription>后台模式支持窗口遮挡；MuMu 可最小化运行。</CardDescription></CardHeader><CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-4"><div className="space-y-2"><Label>副本模式</Label><Select value={mode} onChange={e => setMode(e.target.value)} options={modes.map(m => ({ value: m.name, label: m.name }))} /></div><div className="space-y-2"><Label>挑战次数</Label><Input type="number" min={1} max={10000} value={times} onChange={e => setTimes(Number(e.target.value))} /></div></div>
        {!!currentMode?.sub_modes.length && <div className="space-y-2"><Label>子模式</Label><Select value={subMode} onChange={e => setSubMode(e.target.value)} options={currentMode.sub_modes.map(m => ({ value: m, label: m }))} /></div>}
        {mode === "绘卷刷分" && <div className="grid grid-cols-2 gap-4 rounded-lg bg-muted/50 p-4"><div className="space-y-2"><Label>绘卷打法</Label><Select value={exploreOnly ? "only" : "all"} onChange={e => setExploreOnly(e.target.value === "only")} options={[{ value: "all", label: "探索 + 突破" }, { value: "only", label: "仅探索" }]} /></div><div className="space-y-2"><Label>每轮探索次数</Label><Input type="number" min={1} value={exploreCount} onChange={e => setExploreCount(Number(e.target.value))} /></div></div>}
        <div className="space-y-2"><Label>游戏客户端</Label><div className="flex gap-2"><Select className="min-w-0 flex-1" value={clientId} onChange={e => setClientId(e.target.value)} options={clients.map(c => ({ value: c.id, label: c.label }))} /><Button variant="outline" size="icon" onClick={refreshClients} title="刷新窗口"><RefreshCw /></Button></div></div>
        <div className="flex flex-wrap gap-x-6 gap-y-3"><label className="flex items-center gap-2 text-sm"><Switch checked={hidden} onCheckedChange={setHidden} />后台运行</label><label className="flex items-center gap-2 text-sm"><Switch checked={syncMode} onCheckedChange={setSyncMode} disabled={!syncEnabled} />同步挑战{!syncEnabled && <span className="text-xs text-muted-foreground">(先启动同步)</span>}</label></div>
        <div className="space-y-3 border-t pt-4"><div className="flex justify-between text-sm"><span className="text-muted-foreground">挑战进度</span><span>{task.done} / {task.total}</span></div><Progress value={percent} /></div>
        <div className="flex gap-2"><Button className="flex-1" disabled={running || submitting || !mode} onClick={start}><Play />开始挑战</Button>{running && <><Button variant="outline" size="icon" onClick={() => control(task.paused ? "resume" : "pause")}>{task.paused ? <Play /> : <Pause />}</Button><Button variant="destructive" size="icon" onClick={() => control("stop")}><Square /></Button></>}</div>
      </CardContent></Card>
      <Card className="flex min-h-[590px] flex-col"><CardHeader><CardTitle>运行日志</CardTitle><CardDescription>来自 FastAPI 的实时事件流</CardDescription></CardHeader><CardContent className="min-h-0 flex-1"><div className="h-full max-h-[650px] overflow-y-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs leading-6 text-zinc-300">{logs.length === 0 ? <span className="text-zinc-500">暂无日志，启动任务后可在此查看。</span> : logs.map((log, index) => <div key={`${log.timestamp}-${index}`} className="break-words"><span className="mr-2 text-zinc-600">{log.timestamp.slice(11, 19)}</span><span className={log.level === "ERROR" ? "text-red-400" : log.level === "WARNING" ? "text-amber-300" : "text-zinc-300"}>{log.message}</span></div>)}<div ref={logEnd} /></div></CardContent></Card>
    </div>
  </div>;
}

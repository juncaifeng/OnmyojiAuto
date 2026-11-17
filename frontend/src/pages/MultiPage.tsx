import { useEffect, useState } from "react";
import { FolderOpen, Play, Trash2 } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { api, post } from "@/lib/api";
import type { MultiInstance } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function MultiPage() {
  const [path, setPath] = useState("");
  const [count, setCount] = useState(2);
  const [interval, setIntervalValue] = useState(5);
  const [instances, setInstances] = useState<MultiInstance[]>([]);
  const [error, setError] = useState("");
  const refresh = () => api<MultiInstance[]>("/multi").then(setInstances).catch(e => setError(e.message));
  useEffect(() => { refresh(); const timer = setInterval(refresh, 3000); return () => clearInterval(timer); }, []);
  const browse = async () => { if ("__TAURI_INTERNALS__" in window) { const selected = await invoke<string | null>("pick_executable"); if (selected) setPath(selected); } };
  const start = async () => { setError(""); try { setInstances(await post<MultiInstance[]>("/multi/start", { exe_path: path, count, interval })); } catch (e) { setError((e as Error).message); } };
  const close = async (id: number) => { try { await api(`/multi/${id}`, { method: "DELETE" }); refresh(); } catch (e) { setError((e as Error).message); } };
  return <div className="p-7"><header className="mb-6"><h1 className="text-2xl font-bold tracking-tight">多开管理</h1><p className="mt-1 text-sm text-muted-foreground">通过 yyx-launcher 直接创建游戏进程，不经过命令行 shell。</p></header>{error && <div className="mb-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}<div className="space-y-5">
    <Card><CardHeader><CardTitle>启动游戏实例</CardTitle><CardDescription>启动间隔至少 3 秒，避免游戏初始化竞争。</CardDescription></CardHeader><CardContent className="space-y-5"><div className="space-y-2"><Label>游戏 exe 路径</Label><div className="flex gap-2"><Input value={path} onChange={e => setPath(e.target.value)} placeholder="例如 C:\Program Files\Onmyoji\Launch.exe" /><Button variant="outline" onClick={browse}><FolderOpen />浏览</Button></div></div><div className="grid grid-cols-2 gap-4"><div className="space-y-2"><Label>启动数量</Label><Input type="number" min={1} max={20} value={count} onChange={e => setCount(Number(e.target.value))} /></div><div className="space-y-2"><Label>启动间隔（秒）</Label><Input type="number" min={3} value={interval} onChange={e => setIntervalValue(Number(e.target.value))} /></div></div><Button onClick={start} disabled={!path}><Play />批量启动</Button></CardContent></Card>
    <Card><CardHeader><CardTitle>实例列表</CardTitle></CardHeader><CardContent><div className="space-y-2">{instances.map(item => <div key={item.id} className="flex items-center gap-4 rounded-lg border p-3 text-sm"><span className="font-medium">实例 {item.id}</span><span className="text-muted-foreground">PID {item.pid || "—"}</span><span>{item.status}</span><span className="ml-auto text-xs text-muted-foreground">{item.launched_at}</span><Button variant="ghost" size="icon" onClick={() => close(item.id)}><Trash2 /></Button></div>)}{!instances.length && <div className="py-8 text-center text-sm text-muted-foreground">本次后端运行期间尚未启动实例。</div>}</div></CardContent></Card>
  </div></div>;
}

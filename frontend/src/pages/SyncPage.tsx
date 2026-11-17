import { useCallback, useEffect, useState } from "react";
import { LayoutGrid, RefreshCw } from "lucide-react";
import { api, apiBlob, post } from "@/lib/api";
import type { Client, SyncState } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type Props = { sync: SyncState; setSync: (state: SyncState) => void };
export default function SyncPage({ sync, setSync }: Props) {
  const [clients, setClients] = useState<Client[]>([]);
  const [main, setMain] = useState<number | null>(null);
  const [subs, setSubs] = useState<number[]>([]);
  const [preview, setPreview] = useState<string>("");
  const [error, setError] = useState("");
  const refresh = useCallback(async () => { try { setClients((await api<Client[]>("/clients")).filter(c => c.hwnd)); } catch (e) { setError((e as Error).message); } }, []);
  useEffect(() => { refresh(); return () => { if (preview) URL.revokeObjectURL(preview); }; }, [refresh]);
  const toggleSub = (hwnd: number) => setSubs(old => old.includes(hwnd) ? old.filter(id => id !== hwnd) : [...old, hwnd]);
  const action = async (name: "start" | "stop" | "arrange") => {
    setError("");
    try {
      if (name === "start" && !main) throw new Error("请选择一个主窗口");
      const body = name === "start" ? { main_hwnd: main, sub_hwnds: subs.filter(id => id !== main) } : undefined;
      setSync(await post<SyncState>(`/sync/${name}`, body));
    } catch (e) { setError((e as Error).message); }
  };
  const showPreview = async (hwnd: number) => { try { if (preview) URL.revokeObjectURL(preview); setPreview(URL.createObjectURL(await apiBlob(`/clients/${hwnd}/preview`))); } catch (e) { setError((e as Error).message); } };
  return <div className="p-7"><header className="mb-6"><h1 className="text-2xl font-bold tracking-tight">窗口同步</h1><p className="mt-1 text-sm text-muted-foreground">设置一个主窗口，将键鼠或程序操作同步到多个副窗口。</p></header>{error && <div className="mb-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}<div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
    <Card><CardHeader className="flex-row items-center justify-between space-y-0"><div><CardTitle>客户端窗口</CardTitle><CardDescription className="mt-2">单选主窗口，勾选一个或多个副窗口。</CardDescription></div><Button variant="outline" size="icon" onClick={refresh}><RefreshCw /></Button></CardHeader><CardContent><div className="overflow-hidden rounded-lg border"><table className="w-full text-sm"><thead className="bg-muted/60 text-left text-muted-foreground"><tr><th className="p-3">主窗口</th><th className="p-3">副窗口</th><th className="p-3">客户端</th><th className="p-3">句柄</th><th className="p-3"></th></tr></thead><tbody>{clients.map(client => <tr key={client.id} className="border-t"><td className="p-3"><input type="radio" name="main" checked={main === client.hwnd} onChange={() => setMain(client.hwnd)} /></td><td className="p-3"><input type="checkbox" checked={client.hwnd !== null && subs.includes(client.hwnd)} disabled={main === client.hwnd} onChange={() => client.hwnd && toggleSub(client.hwnd)} /></td><td className="max-w-64 truncate p-3" title={client.label}>{client.label}</td><td className="p-3 font-mono text-xs">{client.hwnd}</td><td className="p-3"><Button variant="ghost" size="sm" onClick={() => client.hwnd && showPreview(client.hwnd)}>预览</Button></td></tr>)}</tbody></table>{!clients.length && <div className="p-10 text-center text-sm text-muted-foreground">未发现游戏窗口，请先启动游戏并刷新。</div>}</div><div className="mt-5 flex flex-wrap gap-2"><Button onClick={() => action("start")} disabled={!main || !subs.some(id => id !== main)}>开始同步</Button><Button variant="outline" onClick={() => action("arrange")}><LayoutGrid />窗口排列</Button><Button variant="destructive" onClick={() => action("stop")} disabled={!sync.enabled}>停止同步</Button></div></CardContent></Card>
    <Card><CardHeader><CardTitle>窗口预览</CardTitle><CardDescription>截图仅在本机后端生成，不上传网络。</CardDescription></CardHeader><CardContent>{preview ? <img src={preview} alt="游戏窗口预览" className="w-full rounded-lg border object-contain" /> : <div className="grid h-64 place-items-center rounded-lg border border-dashed text-sm text-muted-foreground">选择窗口后点击“预览”</div>}<div className="mt-4 text-sm text-muted-foreground">状态：{sync.enabled ? `同步中 · ${sync.sub_hwnds.length} 个副窗口` : "未启动"}</div></CardContent></Card>
  </div></div>;
}

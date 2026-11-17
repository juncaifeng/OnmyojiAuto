# OnmyojiAuto - 阴阳师自动化

Windows 平台的《阴阳师》图像识别自动化工具。当前版本 **2.3.4**。

## 新架构

```text
Tauri v2 桌面窗口（Rust）
  └─ 直接创建 oat-backend.exe 子进程（不使用 shell）
       └─ FastAPI（仅监听 127.0.0.1，随机令牌认证）
            └─ 原有 OpenCV / RapidOCR / Win32 / MuMu 自动化核心

React + Vite + shadcn/ui
  └─ HTTP + WebSocket 调用本地 FastAPI
```

- 前端不直接访问 Windows 自动化对象，也没有任意命令执行接口。
- Tauri 未启用 `tauri-plugin-shell`，使用 Rust `std::process::Command` 和参数数组启动 sidecar。
- FastAPI 提供任务、日志、设置、客户端预览、窗口同步与多开 API。
- 旧 `OAT/app` PyQt 页面仅作迁移参考，不再是默认入口。

## 主要功能

- 魂土、魂王、业原火、觉醒、爬塔、灵染试炼、御灵、契灵探查、结界突破、绘卷刷分。
- 阴阳师桌面版与 MuMu 模拟器。
- 前台/后台识别、窗口预览、多窗口同步和多开管理。
- 实时日志、挑战进度、暂停与停止。

## 目录

```text
OAT/server/              FastAPI 路由、模型、事件总线和服务层
OAT/source/              副本声明式配置、模板和绘卷脚本
OAT/pipeline/            识别与任务管道
frontend/                React + Vite + shadcn/ui
frontend/src-tauri/      Tauri v2 Rust 壳与 sidecar 生命周期
scripts/build_backend.py CI 中的 sidecar 构建脚本
packaging/               PyInstaller spec
.github/workflows/       dev prerelease 与 tag 正式 release
```

## 依赖与 Python 运行时

Python 依赖统一由 **uv + `pyproject.toml` + `uv.lock`** 管理，不再使用 `requirements.txt`。打包时 CI 设置：

```text
UV_PYTHON_PREFERENCE=only-managed
uv python install 3.12
```

uv 下载的 managed CPython 来自 **python-build-standalone**，随后用 PyInstaller 生成 `oat-backend.exe`，Tauri 将它作为 externalBin sidecar 打进 NSIS 安装包。旧 Nuitka 构建流程已移除。

## GitHub Actions 构建与发布

本项目要求**所有构建、打包和测试都在 GitHub Actions 在线执行**。

### dev：每次提交自动发布 prerelease

推送到 `dev` 分支触发 `.github/workflows/dev.yml`：

1. 安装 uv 和 python-build-standalone Python 3.12。
2. 在线安装锁定依赖并运行 pytest。
3. 构建 FastAPI sidecar、React 和 Tauri NSIS 安装包。
4. 创建 `dev-<run_number>-<short_sha>` prerelease 并上传安装包。

```bash
git switch dev
git add -A
git commit -m "feat: your change"
git push origin dev
gh run list --workflow dev.yml --limit 5
gh run watch
```

### tags：只有版本标签触发正式 release

`.github/workflows/release.yml` 只监听 `v*` 标签，且标签必须与应用版本一致。例如版本为 `2.3.4`：

```bash
git tag v2.3.4
git push origin v2.3.4
gh run list --workflow release.yml --limit 5
gh run watch
```

正式 release 只由标签工作流创建，普通提交不会触发。

## 本地开发接口说明

以下是接口说明，**CI 迁移验证期间不要在本地执行构建或测试命令**：

- API 前缀：`/api/v1`
- 健康检查：`GET /health`
- 事件流：`WebSocket /events?token=...`
- 其他接口要求 `X-OAT-Token` 请求头。
- 服务只接受回环监听地址，生产环境由 Tauri 随机选择端口与令牌。

## 使用注意

- 仅支持 Windows，窗口识别和后台控制通常需要管理员权限。
- 保持游戏窗口分辨率稳定；模板不匹配时需更新 `OAT/source` 中对应图片。
- PC 后台模式允许遮挡但不支持最小化；MuMu 可使用 IPC 后台通道。
- 本项目采用 GPL v3，详见 `LICENSE`。

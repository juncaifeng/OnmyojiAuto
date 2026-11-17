use rand::{distributions::Alphanumeric, Rng};
use serde::Serialize;
use std::{
    net::{SocketAddr, TcpListener, TcpStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};
use tauri::{AppHandle, Manager, RunEvent, State};

struct BackendState {
    url: String,
    ws_url: String,
    token: String,
    child: Mutex<Option<Child>>,
}

#[derive(Serialize)]
struct BackendConfig {
    url: String,
    token: String,
    ws_url: String,
}

#[tauri::command]
fn backend_config(state: State<'_, BackendState>) -> BackendConfig {
    BackendConfig {
        url: state.url.clone(),
        token: state.token.clone(),
        ws_url: state.ws_url.clone(),
    }
}

#[tauri::command]
fn pick_executable() -> Option<String> {
    rfd::FileDialog::new()
        .add_filter("可执行文件", &["exe"])
        .pick_file()
        .map(|path| path.to_string_lossy().into_owned())
}

fn sidecar_path() -> Result<PathBuf, String> {
    if let Some(path) = std::env::var_os("OAT_BACKEND_BIN") {
        return Ok(PathBuf::from(path));
    }
    let executable = if cfg!(windows) { "oat-backend.exe" } else { "oat-backend" };
    if cfg!(debug_assertions) {
        let target = if cfg!(windows) {
            "oat-backend-x86_64-pc-windows-msvc.exe"
        } else {
            "oat-backend"
        };
        let candidate = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("binaries")
            .join(target);
        if candidate.is_file() {
            return Ok(candidate);
        }
    }
    let current = std::env::current_exe().map_err(|e| e.to_string())?;
    Ok(current
        .parent()
        .ok_or("无法定位桌面程序目录")?
        .join(executable))
}

fn spawn_backend(app: &AppHandle) -> Result<(), String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|e| e.to_string())?;
    let port = listener.local_addr().map_err(|e| e.to_string())?.port();
    drop(listener);
    let token: String = rand::thread_rng()
        .sample_iter(&Alphanumeric)
        .take(48)
        .map(char::from)
        .collect();
    let executable = sidecar_path()?;
    if !executable.is_file() {
        return Err(format!("找不到 FastAPI sidecar：{}", executable.display()));
    }

    let mut command = Command::new(executable);
    command
        .args([
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
            "--token",
            &token,
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
    // Command::new + args 直接调用 CreateProcess/execve，不经过 cmd、PowerShell 或 sh。
    let mut child = command.spawn().map_err(|e| format!("启动后端失败：{e}"))?;
    let address: SocketAddr = ([127, 0, 0, 1], port).into();
    let deadline = Instant::now() + Duration::from_secs(30);
    loop {
        if TcpStream::connect_timeout(&address, Duration::from_millis(300)).is_ok() {
            break;
        }
        if let Some(status) = child.try_wait().map_err(|e| e.to_string())? {
            return Err(format!("后端提前退出：{status}"));
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            return Err("等待 FastAPI 后端启动超时".into());
        }
        thread::sleep(Duration::from_millis(150));
    }

    app.manage(BackendState {
        url: format!("http://127.0.0.1:{port}"),
        ws_url: format!("ws://127.0.0.1:{port}"),
        token,
        child: Mutex::new(Some(child)),
    });
    Ok(())
}

fn stop_backend(app: &AppHandle) {
    if let Some(state) = app.try_state::<BackendState>() {
        if let Ok(mut guard) = state.child.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![backend_config, pick_executable])
        .setup(|app| {
            spawn_backend(app.handle())?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("构建 Tauri 应用失败");
    app.run(|handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. }) {
            stop_backend(handle);
        }
    });
}

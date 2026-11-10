// Bellows desktop shell (Tauri 2).
//
// Boot order is deliberately "window first":
//   1. pick a free localhost port and show the local splash screen immediately;
//   2. spawn the bundled `bellows-core` (PyInstaller onedir, no temp extraction);
//   3. stream boot stages to the splash screen;
//   4. navigate the same window to the workbench once `/api/health` answers.
//
// On exit the core process is terminated so no orphan Python process remains.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{Emitter, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

struct CoreProcess(Mutex<Option<Child>>);

#[derive(Clone, Serialize)]
struct BootProgress {
    stage: &'static str,
    label: &'static str,
    progress: f32,
}

fn pick_port() -> u16 {
    TcpListener::bind(("127.0.0.1", 0))
        .and_then(|listener| listener.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(7801)
}

/// Poll `/api/health` with a short interval so the workbench opens as soon as
/// uvicorn is listening instead of waiting on a coarse tick.
fn wait_for_core(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    let mut attempt = 0u32;
    while Instant::now() < deadline {
        if let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) {
            let _ = stream.set_read_timeout(Some(Duration::from_millis(600)));
            let _ = stream.set_write_timeout(Some(Duration::from_millis(600)));
            let request = "GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
            if stream.write_all(request.as_bytes()).is_ok() {
                let mut buffer = [0u8; 512];
                if let Ok(n) = stream.read(&mut buffer) {
                    let text = String::from_utf8_lossy(&buffer[..n]);
                    if text.contains("200 OK") && text.contains("\"status\":\"ok\"") {
                        return true;
                    }
                }
            }
        }
        attempt += 1;
        // 80ms for the first second, then back off to 250ms.
        let delay = if attempt < 12 { 80 } else { 250 };
        thread::sleep(Duration::from_millis(delay));
    }
    false
}

/// Locate the bundled core. In a packaged app it lives under the bundle
/// resource directory; during `tauri dev` it sits next to the Rust project.
fn core_path() -> PathBuf {
    let exe = if cfg!(windows) {
        "bellows-core.exe"
    } else {
        "bellows-core"
    };
    if let Ok(dir) = std::env::current_exe() {
        let mut candidates = Vec::new();
        if let Some(parent) = dir.parent() {
            candidates.push(parent.join("sidecar").join(exe));
            candidates.push(parent.join(exe));
        }
        for candidate in candidates {
            if candidate.exists() {
                return candidate;
            }
        }
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("sidecar")
        .join(exe)
}

fn spawn_core(port: u16, data_dir: &PathBuf) -> std::io::Result<Child> {
    let mut command = Command::new(core_path());
    command
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg(port.to_string())
        .arg("--data-dir")
        .arg(data_dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        // Do not flash a console window for the child process.
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    command.spawn()
}

fn emit_progress(app: &tauri::AppHandle, stage: &'static str, label: &'static str, progress: f32) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.emit(
            "boot-progress",
            BootProgress {
                stage,
                label,
                progress,
            },
        );
    }
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let port = pick_port();
            let data_dir = app
                .path()
                .app_data_dir()
                .unwrap_or_else(|_| PathBuf::from("."));
            std::fs::create_dir_all(&data_dir).ok();

            // Show the splash instantly; everything slow happens after this.
            let window = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("Bellows · 风箱")
                .inner_size(900.0, 560.0)
                .min_inner_size(720.0, 480.0)
                .resizable(false)
                .center()
                .build()?;

            let handle = app.handle().clone();
            match spawn_core(port, &data_dir) {
                Ok(child) => {
                    app.manage(CoreProcess(Mutex::new(Some(child))));
                    emit_progress(&handle, "spawning", "正在唤醒内核", 0.35);
                }
                Err(error) => {
                    eprintln!("failed to start bellows-core: {error}");
                    emit_progress(&handle, "failed", "内核启动失败，请重新安装", 1.0);
                    return Ok(());
                }
            }

            let boot_handle = handle.clone();
            thread::spawn(move || {
                emit_progress(&boot_handle, "booting", "内核正在点火", 0.6);
                let ready = wait_for_core(port, Duration::from_secs(45));
                if !ready {
                    emit_progress(&boot_handle, "failed", "点火超时，可重新启动应用", 1.0);
                    return;
                }
                emit_progress(&boot_handle, "ready", "炉火已旺", 1.0);
                // Let the progress bar land before swapping views.
                thread::sleep(Duration::from_millis(280));
                let navigate_handle = boot_handle.clone();
                let _ = boot_handle.run_on_main_thread(move || {
                    if let Some(window) = navigate_handle.get_webview_window("main") {
                        let _ = window.set_resizable(true);
                        let _ = window.set_size(tauri::LogicalSize::new(1280.0, 800.0));
                        let _ = window.center();
                        if let Ok(url) = url::Url::parse(&format!("http://127.0.0.1:{port}")) {
                            let _ = window.navigate(url);
                        }
                    }
                });
            });
            let _ = window;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build Bellows desktop");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = app_handle.try_state::<CoreProcess>() {
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(mut child) = guard.take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        }
    });
}

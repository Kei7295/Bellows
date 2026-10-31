// Bellows desktop shell (Tauri 2).
//
// Starts the bundled `bellows-core` sidecar on a free localhost port, waits for
// `/api/health`, then opens the workbench in a webview window. On exit the
// sidecar is terminated so no orphan Python process is left behind.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

struct SidecarState(Mutex<Option<CommandChild>>);

fn pick_port() -> u16 {
    TcpListener::bind(("127.0.0.1", 0))
        .and_then(|listener| listener.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(7801)
}

fn wait_for_core(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) {
            let _ = stream.set_read_timeout(Some(Duration::from_millis(800)));
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
        thread::sleep(Duration::from_millis(300));
    }
    false
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let port = pick_port();
            let data_dir = app
                .path()
                .app_data_dir()
                .unwrap_or_else(|_| PathBuf::from("."));
            std::fs::create_dir_all(&data_dir).ok();

            let command = app.shell().sidecar("bellows-core")?.args([
                "--host".to_string(),
                "127.0.0.1".to_string(),
                "--port".to_string(),
                port.to_string(),
                "--data-dir".to_string(),
                data_dir.to_string_lossy().to_string(),
            ]);
            let (mut rx, child) = command.spawn()?;
            app.manage(SidecarState(Mutex::new(Some(child))));

            // Drain sidecar output so it never blocks on a full pipe.
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let CommandEvent::Stderr(line) = event {
                        eprintln!("[bellows-core] {}", String::from_utf8_lossy(&line));
                    }
                }
            });

            let handle = app.handle().clone();
            thread::spawn(move || {
                let ready = wait_for_core(port, Duration::from_secs(45));
                let _ = handle.run_on_main_thread(move || {
                    let url = format!("http://127.0.0.1:{port}");
                    let target = if ready {
                        match url::Url::parse(&url) {
                            Ok(parsed) => WebviewUrl::External(parsed),
                            Err(_) => WebviewUrl::App("index.html".into()),
                        }
                    } else {
                        WebviewUrl::App("index.html".into())
                    };
                    let builder = WebviewWindowBuilder::new(&handle, "main", target)
                        .title("Bellows · 风箱")
                        .inner_size(1280.0, 800.0)
                        .min_inner_size(960.0, 640.0)
                        .center();
                    if let Err(error) = builder.build() {
                        eprintln!("failed to create main window: {error}");
                    }
                });
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build Bellows desktop");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = app_handle.try_state::<SidecarState>() {
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(child) = guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });
}

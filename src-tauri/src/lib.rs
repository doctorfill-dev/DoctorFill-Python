use std::sync::Mutex;
use tauri::webview::WebviewWindowBuilder;
use tauri::Manager;
use tauri::WebviewUrl;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

const FLASK_PORT: u16 = 8000;

/// Holds the sidecar process so we can kill it when the app exits.
struct Sidecar(Mutex<Option<tauri_plugin_shell::process::CommandChild>>);

impl Sidecar {
    /// Kill the sidecar process and its children.
    fn kill(&self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(child) = guard.take() {
                println!("[tauri] Killing sidecar process...");
                let _ = child.kill();
                println!("[tauri] Sidecar killed.");
            }
        }
        // Belt-and-suspenders: also kill any process listening on our port.
        // This catches child processes spawned by the sidecar (e.g. Flask reloader).
        Self::kill_port_holder();
    }

    /// Kill any process listening on FLASK_PORT.
    /// Works on macOS and Linux via lsof, on Windows via netstat/taskkill.
    fn kill_port_holder() {
        #[cfg(unix)]
        {
            let _ = std::process::Command::new("sh")
                .args([
                    "-c",
                    &format!(
                        "lsof -ti :{} | xargs kill -9 2>/dev/null",
                        FLASK_PORT
                    ),
                ])
                .output();
        }
        #[cfg(windows)]
        {
            // Find PID listening on port and kill it
            let output = std::process::Command::new("cmd")
                .args([
                    "/C",
                    &format!(
                        "for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{} ^| findstr LISTENING') do taskkill /F /PID %a",
                        FLASK_PORT
                    ),
                ])
                .output();
            let _ = output;
        }
    }
}

/// Spawn a background watchdog process that monitors the main Tauri app PID.
/// If the main app dies (SIGTERM, SIGKILL, crash), the watchdog process
/// kills any process holding our Flask port.
/// This is necessary because:
/// - macOS Cocoa/NSApplication overrides SIGTERM handlers
/// - Tauri's RunEvent::Exit may not fire on forced kills
/// - Child processes become orphaned when the parent is killed
fn spawn_sidecar_watchdog() {
    let main_pid = std::process::id();
    #[cfg(unix)]
    {
        // Spawn a detached shell process that polls the parent PID
        let _ = std::process::Command::new("sh")
            .args([
                "-c",
                &format!(
                    // Wait until the main PID disappears, then kill anything on our port
                    "while kill -0 {} 2>/dev/null; do sleep 1; done; \
                     sleep 1; \
                     lsof -ti :{} | xargs kill -9 2>/dev/null",
                    main_pid, FLASK_PORT
                ),
            ])
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn();
    }
    #[cfg(windows)]
    {
        // On Windows, use a PowerShell process to watch for parent death
        let _ = std::process::Command::new("powershell")
            .args([
                "-WindowStyle", "Hidden",
                "-Command",
                &format!(
                    "while (Get-Process -Id {} -ErrorAction SilentlyContinue) {{ Start-Sleep -Seconds 1 }}; \
                     Start-Sleep -Seconds 1; \
                     $p = netstat -aon | Select-String ':{} ' | Select-String 'LISTENING'; \
                     if ($p) {{ $pid = ($p -split '\\s+')[-1]; Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }}",
                    main_pid, FLASK_PORT
                ),
            ])
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn();
    }
}

/// Spawn the Python backend sidecar and read its output in background.
fn start_python_backend(app: &tauri::AppHandle) -> tauri_plugin_shell::process::CommandChild {
    let (mut rx, child) = app
        .shell()
        .sidecar("doctorfill-server")
        .expect("failed to create doctorfill-server sidecar")
        .spawn()
        .expect("failed to spawn doctorfill-server sidecar");

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let s = String::from_utf8_lossy(&line);
                    println!("[python] {}", s);
                }
                CommandEvent::Stderr(line) => {
                    let s = String::from_utf8_lossy(&line);
                    eprintln!("[python] {}", s);
                }
                CommandEvent::Terminated(payload) => {
                    println!("[python] terminated: {:?}", payload);
                    break;
                }
                _ => {}
            }
        }
    });

    child
}

/// Loading page shown while Flask sidecar starts up.
/// Uses base64-encoded data URI for reliable rendering on all platforms
/// (plain data URIs with special chars can show blank on WKWebView).
fn loading_html() -> String {
    let html = r#"<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  }
  .loader {
    text-align:center; color:white;
  }
  .loader h1 { font-size:1.75rem; margin-bottom:1rem; }
  .spinner {
    width:40px; height:40px; margin:0 auto 1rem;
    border:4px solid rgba(255,255,255,0.3); border-top-color:white;
    border-radius:50%; animation:spin 1s linear infinite;
  }
  @keyframes spin { to { transform:rotate(360deg); } }
  .loader p { opacity:0.8; font-size:0.9rem; }
</style>
</head>
<body>
  <div class="loader">
    <h1>DoctorFill</h1>
    <div class="spinner"></div>
    <p>Démarrage du serveur...</p>
  </div>
</body>
</html>"#;

    // Base64-encode the HTML for reliable data URI on all webview engines
    let mut b64 = String::new();
    {
        use std::fmt::Write as FmtWrite;
        let encoded = base64_encode(html.as_bytes());
        let _ = write!(&mut b64, "data:text/html;base64,{}", encoded);
    }
    b64
}

/// Simple base64 encoder (no external crate needed).
fn base64_encode(input: &[u8]) -> String {
    const CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::with_capacity((input.len() + 2) / 3 * 4);
    for chunk in input.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = if chunk.len() > 1 { chunk[1] as u32 } else { 0 };
        let b2 = if chunk.len() > 2 { chunk[2] as u32 } else { 0 };
        let triple = (b0 << 16) | (b1 << 8) | b2;
        result.push(CHARS[((triple >> 18) & 0x3F) as usize] as char);
        result.push(CHARS[((triple >> 12) & 0x3F) as usize] as char);
        if chunk.len() > 1 {
            result.push(CHARS[((triple >> 6) & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }
        if chunk.len() > 2 {
            result.push(CHARS[(triple & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }
    }
    result
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Spawn a watchdog process that will clean up the sidecar if the app
    // is killed via SIGTERM, SIGKILL, or any unexpected termination.
    spawn_sidecar_watchdog();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            // ── Create the window immediately with a loading page ─────
            let loading_url: tauri::Url = loading_html().parse().expect("invalid data URI");

            let _window = WebviewWindowBuilder::new(
                app,
                "main",
                WebviewUrl::External(loading_url),
            )
            .title("DoctorFill")
            .inner_size(700.0, 850.0)
            .resizable(true)
            .center()
            .disable_drag_drop_handler()
            .build()?;

            // ── Start sidecar (production only) ──────────────────────
            #[cfg(not(dev))]
            {
                let child = start_python_backend(app.handle());
                app.manage(Sidecar(Mutex::new(Some(child))));
            }

            // ── Navigate to Flask once ready (async, non-blocking) ───
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let url = format!("http://localhost:{}/health", FLASK_PORT);
                let max_retries = 60;

                for i in 1..=max_retries {
                    match reqwest::get(&url).await {
                        Ok(resp) if resp.status().is_success() => {
                            println!("[tauri] Backend ready after {} attempt(s)", i);
                            if let Some(w) = handle.get_webview_window("main") {
                                let flask_url: tauri::Url =
                                    format!("http://localhost:{}", FLASK_PORT)
                                        .parse()
                                        .expect("invalid Flask URL");
                                let _ = w.navigate(flask_url);
                            }
                            return;
                        }
                        _ => {
                            println!(
                                "[tauri] Waiting for backend... attempt {}/{}",
                                i, max_retries
                            );
                            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                        }
                    }
                }
                eprintln!("[tauri] Backend did not start in time!");
            });

            Ok(())
        })
        // ── Kill sidecar when app exits ──────────────────────────────
        .build(tauri::generate_context!())
        .expect("error while building DoctorFill")
        .run(|app_handle, event| {
            match event {
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                    println!("[tauri] App exiting, cleaning up sidecar...");
                    if let Some(state) = app_handle.try_state::<Sidecar>() {
                        state.kill();
                    } else {
                        // Fallback: kill any process on our port even without state
                        Sidecar::kill_port_holder();
                    }
                }
                _ => {}
            }
        });
}

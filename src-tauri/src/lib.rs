use tauri::webview::WebviewWindowBuilder;
use tauri::Manager;
use tauri::WebviewUrl;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

const FLASK_PORT: u16 = 8000;

/// Spawn the Python backend sidecar and read its output in background.
/// Returns the child process handle so it stays alive.
fn start_python_backend(app: &tauri::AppHandle) -> tauri_plugin_shell::process::CommandChild {
    let (mut rx, child) = app
        .shell()
        .sidecar("doctorfill-server")
        .expect("failed to create doctorfill-server sidecar")
        .spawn()
        .expect("failed to spawn doctorfill-server sidecar");

    // Read sidecar stdout/stderr in background so it doesn't block
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
fn loading_html() -> String {
    format!(
        r#"data:text/html,
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  }}
  .loader {{
    text-align:center; color:white;
  }}
  .loader h1 {{ font-size:1.75rem; margin-bottom:1rem; }}
  .spinner {{
    width:40px; height:40px; margin:0 auto 1rem;
    border:4px solid rgba(255,255,255,0.3); border-top-color:white;
    border-radius:50%; animation:spin 1s linear infinite;
  }}
  @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
  .loader p {{ opacity:0.8; font-size:0.9rem; }}
</style>
</head>
<body>
  <div class="loader">
    <h1>DoctorFill</h1>
    <div class="spinner"></div>
    <p>Demarrage du serveur...</p>
  </div>
</body>
</html>"#
    )
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            // ── Create the window immediately with a loading page ─────
            // This avoids the blank white screen the user sees while
            // the Flask sidecar takes ~12s to start.
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
            // Disable Tauri's native drag-drop interception so the
            // browser's standard HTML5 drag & drop API works
            // (files from Finder → webview drop zone).
            .disable_drag_drop_handler()
            .build()?;

            // ── Start sidecar + navigate when ready (in background) ──
            #[cfg(not(dev))]
            {
                let child = start_python_backend(app.handle());
                app.manage(child);
            }

            // Navigate to Flask once it is ready (runs in async so UI stays responsive)
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let url = format!("http://localhost:{}/health", FLASK_PORT);
                let max_retries = 60; // 30 seconds

                for i in 1..=max_retries {
                    match reqwest::get(&url).await {
                        Ok(resp) if resp.status().is_success() => {
                            println!("[tauri] Backend ready after {} attempt(s)", i);
                            // Navigate the window to Flask
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
        .run(tauri::generate_context!())
        .expect("error while running DoctorFill");
}

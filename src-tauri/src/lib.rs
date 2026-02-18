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

/// Wait for the Flask backend to become ready by polling its health endpoint.
fn wait_for_backend(max_retries: u32) -> bool {
    let url = format!("http://localhost:{}/health", FLASK_PORT);
    for i in 1..=max_retries {
        match reqwest::blocking::get(&url) {
            Ok(resp) if resp.status().is_success() => {
                println!("[tauri] Backend ready after {} attempt(s)", i);
                return true;
            }
            _ => {
                println!(
                    "[tauri] Waiting for backend... attempt {}/{}",
                    i, max_retries
                );
                std::thread::sleep(std::time::Duration::from_millis(500));
            }
        }
    }
    eprintln!("[tauri] Backend did not start in time!");
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            // ── Production build ──────────────────────────────────
            // Launch sidecar, wait for Flask, create window pointing to Flask HTTP.
            #[cfg(not(dev))]
            {
                let child = start_python_backend(app.handle());
                app.manage(child);
                wait_for_backend(30);
            }

            // ── Dev mode ─────────────────────────────────────────
            // Flask must be started externally (e.g. `python -m flask run -p 8000`)
            // before running `tauri dev`. Wait for it to be up.
            #[cfg(dev)]
            {
                wait_for_backend(20);
            }

            // ── Create main window ───────────────────────────────
            // Always point the webview at Flask over plain HTTP.
            // This eliminates the mixed-content issue entirely:
            //   - No https://tauri.localhost → http://localhost cross-origin
            //   - Flask serves both HTML and API on the same origin
            //   - No CORS needed
            let url: tauri::Url = format!("http://localhost:{}", FLASK_PORT)
                .parse()
                .expect("invalid URL");

            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
                .title("DoctorFill")
                .inner_size(700.0, 850.0)
                .resizable(true)
                .center()
                .build()?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running DoctorFill");
}

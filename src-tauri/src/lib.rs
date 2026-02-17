use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

/// Spawn the Python backend sidecar and wait for it to be ready.
fn start_python_backend(app: &tauri::AppHandle) {
    let (mut rx, _child) = app
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
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            start_python_backend(app.handle());
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running DoctorFill");
}

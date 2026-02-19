use std::sync::Mutex;
use tauri::webview::WebviewWindowBuilder;
use tauri::Manager;
use tauri::WebviewUrl;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

const FLASK_PORT: u16 = 8000;

// ── Windows Job Object ────────────────────────────────────────────────────────
//
// On Windows, killing a PyInstaller --onefile process only kills the
// bootstrapper (parent). The real Python child process becomes an orphan and
// keeps running (holding port 8000) even after the Tauri app exits.
//
// A Windows Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE solves this
// at the OS level: when the last handle to the Job is closed (i.e. when the
// Tauri process exits for any reason — normal close, crash, task-kill), Windows
// automatically terminates every process in the Job, including all children.
// No Rust cleanup code, no RunEvent handler, no watchdog process needed.
//
// We assign the sidecar to the Job immediately after spawning it. The Job
// handle is stored in a global so it stays open for the entire lifetime of the
// Tauri process.
//
// References:
//   https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
//   Child processes spawned by the sidecar (e.g. PyInstaller unpacked Python)
//   are also automatically added to the Job unless they explicitly break away.
#[cfg(windows)]
mod job {
    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE, INVALID_HANDLE_VALUE};
    use windows_sys::Win32::Security::SECURITY_ATTRIBUTES;
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };
    use windows_sys::Win32::System::Threading::OpenProcess;
    use windows_sys::Win32::System::Threading::{PROCESS_SET_QUOTA, PROCESS_TERMINATE};

    use std::sync::OnceLock;

    /// Global Job Object handle. Kept open for the Tauri process lifetime.
    /// When this handle is closed (process exit), Windows kills all job members.
    static JOB_HANDLE: OnceLock<JobHandle> = OnceLock::new();

    /// Newtype wrapper so we can implement Send + Sync on a raw HANDLE.
    struct JobHandle(HANDLE);
    // SAFETY: The handle is only written once via OnceLock and never closed
    // manually — Windows closes it on process exit.
    unsafe impl Send for JobHandle {}
    unsafe impl Sync for JobHandle {}

    impl Drop for JobHandle {
        fn drop(&mut self) {
            unsafe {
                if self.0 != INVALID_HANDLE_VALUE && !self.0.is_null() {
                    CloseHandle(self.0);
                }
            }
        }
    }

    /// Create the global Job Object with KILL_ON_JOB_CLOSE.
    /// Must be called once at startup, before spawning the sidecar.
    pub fn create_job() {
        unsafe {
            let job = CreateJobObjectW(std::ptr::null::<SECURITY_ATTRIBUTES>(), std::ptr::null());
            if job.is_null() {
                eprintln!("[tauri] CreateJobObjectW failed");
                return;
            }

            // Set KILL_ON_JOB_CLOSE so all members die when our handle closes.
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

            let ok = SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &raw const info as *const _,
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );

            if ok == 0 {
                eprintln!("[tauri] SetInformationJobObject failed");
                CloseHandle(job);
                return;
            }

            // Store handle globally — never manually closed, Windows does it on exit.
            let _ = JOB_HANDLE.set(JobHandle(job));
            println!("[tauri] Job Object created (KILL_ON_JOB_CLOSE)");
        }
    }

    /// Assign a process (by PID) to the global Job Object.
    pub fn assign_pid_to_job(pid: u32) {
        let Some(job) = JOB_HANDLE.get() else {
            eprintln!("[tauri] Job not initialized, cannot assign PID {}", pid);
            return;
        };

        unsafe {
            let proc = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, 0, pid);
            if proc.is_null() {
                eprintln!("[tauri] OpenProcess failed for PID {}", pid);
                return;
            }

            let ok = AssignProcessToJobObject(job.0, proc);
            CloseHandle(proc);

            if ok == 0 {
                eprintln!("[tauri] AssignProcessToJobObject failed for PID {}", pid);
            } else {
                println!("[tauri] PID {} assigned to Job Object", pid);
            }
        }
    }
}

// ── Sidecar state ─────────────────────────────────────────────────────────────

/// Holds the sidecar process handle and its PID for explicit cleanup on graceful exit.
/// The Job Object is the primary safety net on Windows; this is belt-and-suspenders.
struct Sidecar {
    child: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
    /// PID of the spawned sidecar process, used for scoped tree-kill on Windows.
    #[cfg(windows)]
    pid: u32,
}

impl Sidecar {
    fn new(child: tauri_plugin_shell::process::CommandChild) -> Self {
        Self {
            #[cfg(windows)]
            pid: child.pid(),
            child: Mutex::new(Some(child)),
        }
    }

    /// Explicit kill: send kill signal + platform-specific tree kill.
    fn kill(&self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(child) = guard.take() {
                println!("[tauri] Sending kill to sidecar...");
                let _ = child.kill();
            }
        }
        // Windows: kill the process tree rooted at the sidecar's PID.
        // This handles the PyInstaller parent+child situation explicitly
        // and complements the Job Object for graceful exit paths.
        // Using /PID instead of /IM to avoid killing unrelated instances.
        #[cfg(windows)]
        Self::kill_process_tree_windows(self.pid);

        // Unix: kill by port (lsof).
        #[cfg(unix)]
        Self::kill_port_unix();
    }

    /// Windows: taskkill /F /PID <pid> /T — kills the tree rooted at the given PID only.
    #[cfg(windows)]
    fn kill_process_tree_windows(pid: u32) {
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/PID", &pid.to_string(), "/T"])
            .output();
    }

    /// Unix: kill by port via lsof.
    #[cfg(unix)]
    fn kill_port_unix() {
        let _ = std::process::Command::new("sh")
            .args([
                "-c",
                &format!("lsof -ti :{} | xargs kill -9 2>/dev/null", FLASK_PORT),
            ])
            .output();
    }
}

// ── Python backend launcher ───────────────────────────────────────────────────

/// Spawn the Python backend sidecar, assign it to the Job Object (Windows),
/// and read its output in background.
fn start_python_backend(app: &tauri::AppHandle) -> tauri_plugin_shell::process::CommandChild {
    let (mut rx, child) = app
        .shell()
        .sidecar("doctorfill-server")
        .expect("failed to create doctorfill-server sidecar")
        .spawn()
        .expect("failed to spawn doctorfill-server sidecar");

    // Windows: assign the sidecar PID to the Job Object immediately.
    // Any child processes it spawns (e.g. PyInstaller unpacked Python) will
    // also be part of the Job and killed when the Tauri process exits.
    #[cfg(windows)]
    {
        let pid = child.pid();
        println!("[tauri] Sidecar PID: {}", pid);
        job::assign_pid_to_job(pid);
    }

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

// ── Loading page ──────────────────────────────────────────────────────────────

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

// ── Entry point ───────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Windows: create the Job Object before spawning anything.
    // All subsequently spawned sidecar processes will be assigned to it.
    // When the Tauri process exits (for ANY reason: normal close, crash,
    // task-kill, forced kill), Windows automatically terminates all job members.
    #[cfg(windows)]
    job::create_job();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
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
                app.manage(Sidecar::new(child));
            }

            // ── Check for updates in background (production only) ────
            // Silent check: downloads and installs automatically, then
            // prompts the user to restart via a non-blocking async task.
            #[cfg(not(dev))]
            {
                let update_handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    match tauri_plugin_updater::UpdaterExt::updater(&update_handle) {
                        Ok(updater) => {
                            match updater.check().await {
                                Ok(Some(update)) => {
                                    println!(
                                        "[tauri] Update available: {} -> {}",
                                        update.current_version,
                                        update.version
                                    );
                                    let mut downloaded = 0u64;
                                    match update
                                        .download_and_install(
                                            |chunk, total| {
                                                downloaded += chunk as u64;
                                                if let Some(t) = total {
                                                    println!(
                                                        "[tauri] Downloading update: {}/{}",
                                                        downloaded, t
                                                    );
                                                }
                                            },
                                            || {
                                                println!("[tauri] Update installed, restart required.");
                                            },
                                        )
                                        .await
                                    {
                                        Ok(_) => {
                                            println!("[tauri] Restarting for update...");
                                            tauri_plugin_process::restart(
                                                &update_handle.env(),
                                            );
                                        }
                                        Err(e) => eprintln!("[tauri] Update install failed: {}", e),
                                    }
                                }
                                Ok(None) => println!("[tauri] App is up to date."),
                                Err(e) => eprintln!("[tauri] Update check failed: {}", e),
                            }
                        }
                        Err(e) => eprintln!("[tauri] Updater init failed: {}", e),
                    }
                });
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
        // ── Kill sidecar when app exits (graceful close) ─────────────
        // The Job Object handles forced kills / crashes automatically.
        .build(tauri::generate_context!())
        .expect("error while building DoctorFill")
        .run(|app_handle, event| {
            match event {
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                    println!("[tauri] App exiting, cleaning up sidecar...");
                    if let Some(state) = app_handle.try_state::<Sidecar>() {
                        state.kill();
                    } else {
                        // Fallback if state was never registered (dev mode).
                        // On Windows the Job Object handles cleanup automatically.
                        // On Unix, fall back to port-based kill.
                        #[cfg(unix)]
                        Sidecar::kill_port_unix();
                    }
                }
                _ => {}
            }
        });
}

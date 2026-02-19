# DoctorFill

Application de remplissage intelligent de formulaires PDF medicaux.

## Architecture

- **RAG Pipeline** : Chunking intelligent, embeddings, reranking cross-encoder
- **XFA natif** : Extraction, remplissage et injection XFA robustes
- **Multi-providers** : Support Infomaniak AI (cloud) et LM Studio (local)
- **Desktop** : Application Tauri (Rust) avec sidecar Python (PyInstaller)

## Prerequis

| Outil | Version | Installation |
|-------|---------|-------------|
| Python | 3.12 | [python.org](https://www.python.org/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Rust | stable | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| PyInstaller | latest | `pip install pyinstaller` |

## Installation

```bash
git clone https://github.com/doctorfill-dev/DoctorFill-Python.git
cd DoctorFill-Python

# Environnement Python
python3.12 -m venv .env312
source .env312/bin/activate   # macOS/Linux
# .env312\Scripts\activate    # Windows

pip install -r requirements.txt
pip install pyinstaller

# Dependances Node/Tauri
npm install
```

## Utilisation (developpement)

```bash
source .env312/bin/activate
python -m src.web.app
# Ouvrir http://localhost:8000
```

## Build local (application desktop)

### macOS (Apple Silicon)

```bash
# 1. Activer l'environnement Python
source .env312/bin/activate

# 2. Builder le sidecar Python (serveur Flask empaquete)
pyinstaller --noconfirm pyinstaller.spec

# 3. Copier le binaire sidecar dans le dossier Tauri
TARGET=$(rustc -vV | grep host | awk '{print $2}')
mkdir -p src-tauri/binaries
cp dist/doctorfill-server "src-tauri/binaries/doctorfill-server-$TARGET"
chmod +x "src-tauri/binaries/doctorfill-server-$TARGET"

# 4. Builder l'application Tauri
npx tauri build --target "$TARGET"
```

Les fichiers generes se trouvent dans :
- **App** : `src-tauri/target/<target>/release/bundle/macos/DoctorFill.app`
- **DMG** : `src-tauri/target/<target>/release/bundle/dmg/DoctorFill_0.1.0_aarch64.dmg`

### Windows

```bash
# 1. Activer l'environnement Python
.env312\Scripts\activate

# 2. Builder le sidecar Python
pyinstaller --noconfirm pyinstaller.spec

# 3. Copier le binaire sidecar
mkdir -p src-tauri\binaries
copy dist\doctorfill-server.exe src-tauri\binaries\doctorfill-server-x86_64-pc-windows-msvc.exe

# 4. Builder l'application Tauri
npx tauri build --target x86_64-pc-windows-msvc
```

### Changer l'icone

```bash
npm run tauri icon chemin/vers/icone-1024x1024.png
```

## Tester le build

```bash
# macOS - lancement avec logs console
/path/to/DoctorFill.app/Contents/MacOS/doctorfill

# ou double-clic sur DoctorFill.app (desactiver Gatekeeper si besoin)
xattr -cr /path/to/DoctorFill.app
open /path/to/DoctorFill.app
```

## CI/CD

Les builds sont automatises via GitHub Actions. Un push de tag `v*` declenche :
- Build macOS ARM (Apple Silicon)
- Build Windows x64

```bash
git tag v0.1.0-alpha.3
git push origin v0.1.0-alpha.3
```

Les artefacts sont publies comme GitHub Release.

## Structure du projet

```
DoctorFill-Python/
├── src/
│   ├── config/          # Configuration, user_config, registre formulaires
│   ├── core/            # Template manager, type converter
│   ├── llm/             # Providers LLM (Infomaniak, Local)
│   ├── pdf/xfa/         # Extraction, remplissage, injection XFA
│   ├── rag/             # Pipeline RAG (chunker, processor)
│   ├── templates/       # Generation de questions
│   ├── pipeline/        # Orchestrateur principal
│   └── web/             # API Flask et interface (static/)
├── src-tauri/           # Application Tauri (Rust)
│   ├── src/lib.rs       # Logique principale (sidecar, splash, navigation)
│   ├── Cargo.toml       # Dependances Rust
│   ├── tauri.conf.json  # Configuration Tauri
│   ├── binaries/        # Sidecar PyInstaller (genere au build)
│   ├── icons/           # Icones de l'app
│   └── capabilities/    # Permissions Tauri v2
├── templates/           # Templates manuels (JSON)
├── forms/               # PDFs vierges
├── server.py            # Entrypoint PyInstaller
├── pyinstaller.spec     # Configuration PyInstaller
├── package.json         # Dependances Node/Tauri CLI
└── .github/workflows/   # CI/CD GitHub Actions
```

## Formulaires disponibles

- **Form_AVS** : Formulaire AI/AVS
- **Form_Cardio** : Formulaire cardiologique
- **Form_LAA_ABRG** : Formulaire LAA abrege

## Licence

Proprietaire

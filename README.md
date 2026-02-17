# DoctorFill

Application de remplissage intelligent de formulaires PDF médicaux.

## Architecture

Cette application combine les meilleurs composants de deux projets :
- **DF-POC-02** : Module RAG intelligent (embeddings, reranking, gestion des tokens)
- **DoctorFill-app-web** : Extraction/remplissage XFA robuste

## Fonctionnalités

- **RAG Pipeline** : Chunking intelligent, embeddings Nomic/Qwen, reranking cross-encoder
- **Templates hybrides** : Templates manuels prioritaires, génération auto en fallback
- **XFA natif** : Extraction, remplissage et injection XFA robustes
- **Multi-providers** : Support Infomaniak (cloud) et LM Studio (local)
- **Interface web** : Interface simplifiée pour uploader et remplir des formulaires

## Installation

```bash
# Cloner et installer
cd /Users/cutiips/Code/DF-POC-03
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurer
cp .env.example .env
# Éditer .env avec vos credentials Infomaniak
```

## Utilisation

### Via l'interface web

```bash
python -m src.web.app
# Ouvrir http://localhost:8000
```

### Via Python

```python
from src.pipeline.orchestrator import PipelineOrchestrator
from src.core.template_manager import TemplateManager
from pathlib import Path

# Initialiser
tm = TemplateManager()
orchestrator = PipelineOrchestrator(template_manager=tm)

# Remplir un formulaire
result = orchestrator.process(
    form_id="Form_AVS",
    report_pdfs=[Path("rapport_medical.pdf")],
)

if result.success:
    print(f"PDF généré: {result.output_pdf}")
    print(f"Champs remplis: {result.filled_fields}/{result.total_fields}")
```

## Structure

```
DF-POC-03/
├── src/
│   ├── config/          # Configuration et registre des formulaires
│   ├── core/            # Template manager, type converter
│   ├── llm/             # Providers LLM (Infomaniak, Local)
│   ├── pdf/xfa/         # Extraction, remplissage, injection XFA
│   ├── rag/             # Pipeline RAG (chunker, processor)
│   ├── templates/       # Génération de questions
│   ├── pipeline/        # Orchestrateur principal
│   └── web/             # API Flask et interface
├── templates/           # Templates manuels (JSON)
├── forms/               # PDFs vierges
├── data/                # ChromaDB et cache
└── logs/                # Logs et artifacts
```

## Formulaires disponibles

- **Form_AVS** : Formulaire AI/AVS
- **Form_Cardio** : Formulaire cardiologique
- **Form_LAA_ABRG** : Formulaire LAA abrégé

## Configuration

Variables d'environnement principales :

| Variable | Description | Défaut |
|----------|-------------|--------|
| `LLM_PROVIDER` | Provider LLM (`infomaniak` ou `local`) | `infomaniak` |
| `IFK_PRODUCT_ID` | ID produit Infomaniak | - |
| `IFK_API_TOKEN` | Token API Infomaniak | - |
| `RAG_CHUNK_SIZE` | Taille des chunks | `2000` |
| `RAG_USE_RERANKING` | Activer le reranking | `true` |

## Docker

```bash
docker build -t doctorfill .
docker run -p 8000:8000 --env-file .env doctorfill
```

## Licence

Propriétaire

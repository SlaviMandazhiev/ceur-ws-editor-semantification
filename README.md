# CEUR-WS Editor Semantification Pipeline

> Developed as part of the **Knowledge Graphs Lab** (SoSe 2025) at RWTH Aachen University.
>
> Authors: Pierre Bonert, Mohammed Al-Gafri, Slavi Mandazhiev

## About

[CEUR-WS](https://ceur-ws.org) is a widely used publisher of academic workshop proceedings. Its volume pages present metadata (editor names, affiliations, submission counts) in semi-structured HTML, making it difficult to query or analyse programmatically.

This pipeline extracts that metadata, validates it, and uploads it to **CEUR-DEV**: a structured knowledge graph, making editor contributions and institutional affiliations fully queryable.

## Pipeline Architecture

The pipeline is composed of four sequential modules:

| 1. Editor Information Extraction | `editor_extractor.py` | Fetches CEUR-WS volume HTML and uses an LLM to extract editor names, affiliations, and series ordinals into JSON |
| 2. Editor Signature Creation | `editor_operations.py` | Validates extracted data with Pydantic, checks ORCID IDs against the public ORCID API, and uploads editor statements to CEUR-DEV |
| 3. Affiliation Semantification | `affiliation_handling.py` | Uses an LLM to isolate the main organisation from an affiliation string, looks it up on Wikidata, validates it, imports it into CEUR-DEV, and links it to the editor statement |
| 4. Proceedings Metrics Extraction | `editor_extractor.py` | Extracts submission and acceptance counts from the preface summary and uploads them to CEUR-DEV |

`main.py` runs the full pipeline over a configurable range of volume numbers.

## Prerequisites

- Python 3.11+
- Access to an LLM (see [LLM Configuration](#llm-configuration) below)
- CEUR-DEV API credentials (see [note below](#ceur-dev--wikibase-note))

## Installation

```bash
git clone https://github.com/slavimandazhiev/ceur-ws-editor-semantification.git
cd ceur-ws-editor-semantification
pip install -r requirements.txt
```

## For the LLM of you choice you need to install the relevant packages.

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### LLM Configuration

The pipeline supports three LLM providers, configured via `.env`:

**Ollama (default)**  run a model locally or on any Ollama server:
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
```
Install Ollama from [ollama.com](https://ollama.com) and pull a model with `ollama pull llama3.1:8b`.

**OpenAI:**
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

**Anthropic:**
```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=
```

The original project used `llama3.1:8b` via a university-hosted Ollama instance. Any capable instruction-following model should work.

### CEUR-DEV (This is a Wikibase instance of the RWTH university | However the script would work for a personal Wikibase instance) API Credentials

Set your Wikibase instance username and password in `.env`:

```env
USERNAME=your_username
PASSWORD=your_password
```

Without these, the extraction steps (modules 1 and 4) will still run and produce JSON output, but the upload steps (modules 2 and 3) will fail.

## Running the Pipeline

Edit the volume range in `main.py` and run:

```bash
python main.py
```

The default range is a single volume (`3009, 3009`). Change it to process multiple volumes, e.g.:

```python
main(3000, 3100)
```

Extracted JSON files are saved to `json_files/` and logs are written to `log_info.log`.

## Running Tests

```bash
pytest test_editor_operations.py test_main.py
```

20 unit tests covering data validation and mocked API interactions.

## CEUR-DEV & Wikibase Note

**CEUR-DEV** is a [Wikibase](https://wikiba.se) instance hosted by the Chair of Information Systems and Databases (CS5) at RWTH Aachen University. It mirrors the structure of public [Wikidata](https://www.wikidata.org) and serves as a staging environment for structured CEUR-WS metadata.

Access to the CEUR-DEV REST API requires credentials issued by the CS5 chair. External users without those credentials can still run the extraction modules (1 and 4) to produce the intermediate JSON output, or adapt the upload modules to target their own Wikibase instance by changing `BASE_URL` in `config.py`.

Have fun :)

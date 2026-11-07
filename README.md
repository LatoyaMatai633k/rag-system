# Ask Yaya RAG backend

This project repairs and packages the original notebook RAG prototype as a small FastAPI backend for the Ask Yaya portfolio assistant. The original [Latoya_Matai_RAG_EXERCISE.ipynb](./Latoya_Matai_RAG_EXERCISE.ipynb) is preserved and is not used as the application entry point.

## What it does

```text
Google Drive PDF → validate real PDF → extract text → semantic chunks
→ BGE embeddings → LlamaIndex query rewriting and fusion retrieval
→ OpenRouter Llama 3.3 70B → JSON API answer
```

The backend deliberately refuses to index an invalid PDF. This prevents the earlier Google Drive problem where an HTML page was saved as `source.pdf` and caused `invalid pdf header: b'<!doc'`.

## Technology

- Python and FastAPI
- LlamaIndex (the original RAG framework)
- `BAAI/bge-small-en-v1.5` embeddings
- SemanticSplitterNodeParser
- LlamaIndex QueryRewritingRetrieverPack / query fusion
- OpenRouter with `meta-llama/llama-3.3-70b-instruct:free` by default

## Project structure

```text
app/
  main.py                    FastAPI routes and CORS
  core/config.py             environment configuration
  services/drive_download.py validated Google Drive downloader
  services/rag_service.py    original RAG approach as reusable service
  schemas.py                 API request/response models
tests/                       API, RAG guard, and PDF-validation tests
.env.example                 safe configuration template
ASK_YAYA_INTEGRATION.md      portfolio connection instructions
```

`data/` and `query_rewriting_pack/` are created at runtime and intentionally ignored by Git. The index is held in memory: re-index after restarting the API. Persistent vector storage is intentionally not claimed or added here because the original system uses the fusion pack's in-memory index.

## Install locally

Use Python 3.11 or 3.12. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set your real OpenRouter key:

```text
OPENROUTER_API_KEY=your_key_here
```

Never commit `.env` or send its value to the portfolio frontend. An OpenRouter account/key and access to the selected model are required for live embedding/indexing and answers. The default model remains the notebook's free Llama 3.3 70B identifier; update `OPENROUTER_MODEL` only if that identifier is unavailable to your account.

## Google Drive document access

Share the PDF so that the backend can download it without signing in (for example, “Anyone with the link” with viewer access). Supply its usual sharing link—both `/file/d/FILE_ID/view` and `?id=FILE_ID` forms are accepted.

The downloader checks the response bytes before saving. A real PDF starts with `%PDF-`. An HTML login, permission, virus-check, quota, or error page is rejected with a useful message, and does not overwrite an existing valid PDF.

## Run and index a document

Start the backend:

```powershell
uvicorn app.main:app --reload
```

Index a Drive PDF in another terminal. Replace the URL with your own shared-PDF link:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/documents/from-drive `
  -ContentType 'application/json' `
  -Body '{"drive_url":"https://drive.google.com/file/d/FILE_ID/view"}'
```

Success reports actual `document_count` and `chunk_count`. Do not continue to `/chat` if either value is zero. Re-run this endpoint to replace/update the current in-memory knowledge document.

## API

### `GET /health`

Returns whether the server is running and whether a document is currently indexed.

### `POST /documents/from-drive`

Downloads, validates, extracts, chunks, embeds, and indexes a shared Google Drive PDF.

Request:

```json
{"drive_url":"https://drive.google.com/file/d/FILE_ID/view"}
```

### `POST /chat`

Asks a question against the currently indexed document.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat `
  -ContentType 'application/json' `
  -Body '{"question":"What are the main topics?"}'
```

Successful responses always have this form:

```json
{
  "success": true,
  "answer": "Answer based on retrieved document context.",
  "sources": [],
  "error": null
}
```

Common status codes: `200` success, `409` no indexed document, `422` invalid request or PDF, and `502` provider/LLM failure.

## Test locally

With the virtual environment active:

```powershell
pytest -q
```

The included tests do not call Google Drive, download models, or use a real OpenRouter key. They test URL parsing, HTML/PDF detection, empty-file handling, RAG readiness/empty-response guards, endpoint validation, and local CORS behavior. Live ingestion and live answer tests need a valid public PDF, internet access, model downloads, and a valid OpenRouter key.

## Connect Ask Yaya

Use `POST /chat` from the portfolio. The detailed request, JavaScript example, loading/error behavior, sources display, frontend environment variable, and CORS setup are in [ASK_YAYA_INTEGRATION.md](./ASK_YAYA_INTEGRATION.md).

For deployment, use a production ASGI host, set all environment variables securely in that platform, expose HTTPS, set the exact portfolio domain in `ALLOWED_ORIGINS`, and provide a strategy to re-index the document after application restarts. Deployment itself is outside this repository's local setup.

## Troubleshooting

| Symptom | What it means / what to do |
| --- | --- |
| `returned an HTML page instead of a PDF` | The Drive URL is inaccessible, requires sign-in/confirmation, or is not a PDF. Adjust sharing and retry. |
| `No readable text could be extracted` | The PDF may be image-only/scanned. It needs OCR before this text-based pipeline can use it. |
| `No document is indexed` | Call `/documents/from-drive` successfully before `/chat`; re-index after a restart. |
| `OPENROUTER_API_KEY is not configured` | Add the key to `.env`, then restart Uvicorn. |
| `502` response | OpenRouter, model access, or a dependent provider failed. Check the server log and API key/model availability. |

# Connect Ask Yaya to the RAG API

Ask Yaya does not need to know how PDFs, embeddings, or LlamaIndex work. It only calls the backend API.

## Connection details

| Setting | Value |
| --- | --- |
| Backend base URL (local) | `http://127.0.0.1:8000` |
| Production base URL | Set this after the backend is deployed; do not hard-code it in the portfolio. |
| Endpoint | `POST /chat` |
| Content type | `application/json` |
| Request body | `{ "question": "..." }` |

The complete local URL is `http://127.0.0.1:8000/chat`.

Before chat can answer questions, an administrator must index a document with `POST /documents/from-drive`. That endpoint downloads and validates the PDF, then builds the in-memory retrieval index.

## Expected response

Success (`200`):

```json
{
  "success": true,
  "answer": "Generated answer based on the indexed document.",
  "sources": [
    {"source": "data/source.pdf", "page": "2", "score": 0.9123}
  ],
  "error": null
}
```

An error has the same shape. For example, asking before a document is indexed returns `409`:

```json
{
  "success": false,
  "answer": null,
  "sources": [],
  "error": "No document is indexed. Ingest a valid PDF before asking questions."
}
```

## Portfolio environment variable

Configure the portfolio with its own public backend URL. The exact variable name depends on its framework:

```bash
# Vite
VITE_ASK_YAYA_API_URL=https://your-rag-api.example.com

# Next.js (browser-visible variable)
NEXT_PUBLIC_ASK_YAYA_API_URL=https://your-rag-api.example.com
```

Do not put `OPENROUTER_API_KEY` in the portfolio. It belongs only in the RAG backend's `.env` file.

## JavaScript integration example

```js
const apiBaseUrl = import.meta.env.VITE_ASK_YAYA_API_URL;

export async function askYaya(question) {
  const response = await fetch(`${apiBaseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  const payload = await response.json();
  if (!response.ok || !payload.success) {
    throw new Error(payload.error || "Ask Yaya could not answer right now.");
  }
  return payload;
}
```

In the chat submit handler: set a `loading` state before calling `askYaya`, add `payload.answer` as the assistant message when it succeeds, and clear `loading` in a `finally` block. Render each available source under the message, for example `Source: data/source.pdf, page 2`. Catch the thrown error and show it as a friendly chat error without removing the user's question.

## CORS for the portfolio

The backend permits only origins in `ALLOWED_ORIGINS`. Set its `.env` value after you know the portfolio URL:

```bash
ALLOWED_ORIGINS=https://your-portfolio.example.com,http://localhost:5173
```

Restart the backend after changing `.env`. Do not use `*` for a deployed public site.

## Integration checklist

1. Deploy the backend and define `OPENROUTER_API_KEY` there.
2. Set the deployed portfolio origin in `ALLOWED_ORIGINS`.
3. Index a valid shared Google Drive PDF through `POST /documents/from-drive`.
4. Set the portfolio's backend URL environment variable.
5. Test a question in the portfolio and confirm a `200` response with `success: true`.

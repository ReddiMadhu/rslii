# RSLI — Python ETL Visual Lineage Analyzer
## Product Specification v1.0

---

## 1. Overview

RSLI is a **web application** that accepts a single Python ETL script (paste or upload), performs **static AST analysis** to extract the complete data pipeline, and renders an **Alteryx-style visual lineage diagram** with an accompanying **dashboard summary**.

**Core principle**: **AST-first, LLM-optional.** The tool works fully without any LLM connection using Python's `ast` module + template-based descriptions. LLM is an optional enhancement layer that enriches descriptions for complex operations and classifies unknown patterns. ~85% of ETL scripts need zero LLM involvement.

**Target audience**: Reviewers, auditors, and new team members seeing an ETL script for the first time. The tool should enable understanding of "what does this ETL do?" in under 10 seconds via the summary tab, and full lineage exploration via the diagram tab.

**Deployment**: Local machine (`npm run dev` + `uvicorn`). No Docker/containerization for v1.

**Session model**: Ephemeral — upload → view → gone. No persistence, no user accounts, no export.

---

## 2. Architecture

```
┌─────────────────────────────────┐      ┌──────────────────────────────────┐
│         FRONTEND (React 19)     │      │        BACKEND (FastAPI)         │
│         Vite Dev Server         │      │        Python 3.11+              │
│                                 │      │                                  │
│  ┌───────────┐  ┌────────────┐  │      │  ┌──────────┐                    │
│  │ Upload /  │  │ Dashboard  │  │ POST │  │  AST     │  ┌─────────────┐  │
│  │ Paste     │──│ Summary    │──│─────▶│  │  Parser  │─▷│  LLM        │  │
│  │ Page      │  │ (Tab 1)    │  │      │  │ (CORE)   │  │  (OPTIONAL) │  │
│  └───────────┘  ├────────────┤  │      │  └──────────┘  │  Azure AI   │  │
│                 │ Lineage    │  │◀─────│       │        └─────────────┘  │
│                 │ Diagram    │  │ JSON  │       ▼                         │
│                 │ (Tab 2)    │  │       │  ┌──────────┐                   │
│                 └────────────┘  │       │  │ Template │                   │
│                                 │       │  │ NL Desc  │                   │
│  Theme: Dark (default) / Light  │       │  │ (CORE)   │                   │
│  Toggle persists in localStorage│       │  └──────────┘                   │
└─────────────────────────────────┘       └──────────────────────────────────┘
                                           ─▷ = optional dependency
```

### 2.1 Frontend Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + Vite |
| Styling | Tailwind CSS v4 |
| Components | Shadcn UI + Radix UI |
| Icons | Lucide React |
| Font | Geist Variable (Fontsource) |
| State | Zustand |
| Data fetching | TanStack React Query |
| Routing | React Router DOM |
| Notifications | Sonner |
| File upload | React Dropzone |
| Utilities | clsx + tailwind-merge |
| Animations | tw-animate-css |
| Primary color | `#fb4e0b` |

### 2.2 Backend Stack

| Layer | Technology | Required? |
|-------|-----------|----------|
| Framework | FastAPI | ✅ Core |
| Parser | Python `ast` stdlib module | ✅ Core |
| NL Templates | Hardcoded description templates | ✅ Core |
| LLM | Self-hosted model on Azure AI Foundry | ⚡ Optional |
| Auth to LLM | Endpoint URL (env-configurable) | ⚡ Optional |

---

## 3. User Flow

```
1. User opens RSLI in browser
2. User pastes Python code OR uploads a .py file via drag-and-drop
3. Frontend sends code to POST /api/analyze
4. Backend (AST-first pipeline):
   a. Validates Python syntax (max 2000 lines)
   b. Parses AST to extract nodes & edges (ALWAYS runs)
   c. Generates template-based NL descriptions (ALWAYS runs)
   d. IF LLM configured AND complex nodes exist:
      - Sends batch request to LLM for enriched descriptions
      - Sends unclassified operations for categorization
      - On failure: gracefully falls back to template descriptions
   e. Returns JSON response
5. Frontend renders two tabs:
   - Tab 1: Dashboard summary (sources, targets, operation counts)
   - Tab 2: Lineage diagram (Alteryx-style, left-to-right)
6. User clicks nodes to see inline detail panels
7. User closes tab or uploads new file (ephemeral)
```

---

## 4. Input Handling

### 4.1 Input Methods
- **Paste**: Textarea for pasting raw Python code
- **Upload**: Drag-and-drop zone accepting `.py` files only

### 4.2 Validation Rules

| Check | Behavior |
|-------|----------|
| Not valid Python (syntax errors) | Show parse error with line number and message |
| Valid Python, no ETL operations detected | Show "No ETL operations detected" message |
| Exceeds 2000 lines | Show "File too large — max 2000 lines" error |
| Empty input | Disable the analyze button |

---

## 5. AST Parsing Engine

### 5.1 Entry Point Resolution

1. **Primary**: Look for `if __name__ == "__main__":` block. Parse only code within it + resolve all function calls defined in the file.
2. **Fallback (AST-only)**: If no `__main__` guard exists, parse the **entire file top-to-bottom**, treating all top-level statements as the execution flow. Filter out standalone function/class definitions that are never called at the top level.
3. **LLM enhancement (optional)**: If LLM is configured, send the top-level code to LLM to help identify which statements form the main pipeline vs. utility code. This improves accuracy but is **not required** — the AST fallback produces a usable (if noisier) result.

### 5.2 Function Call Resolution (Call Graph)

When a function is called in the main flow, the parser must:
1. Locate the function definition in the same file
2. Parse the function body for ETL operations
3. Map function parameters to the arguments passed at the call site
4. Chain the resulting nodes into the parent flow at the call point

```python
# Example:
def transform(df):
    df = df.dropna()           # → Node: Clean (dropna)
    return df[df['x'] > 0]    # → Node: Filter (x > 0)

if __name__ == "__main__":
    data = pd.read_csv("a.csv")  # → Node: Source (a.csv)
    result = transform(data)      # → Expands into 2 nodes above
    result.to_csv("out.csv")      # → Node: Target (out.csv)
```

### 5.3 Variable Tracking

The parser must handle **both** variable patterns:

- **Unique names**: `raw → cleaned → filtered → result` — each is a distinct variable
- **Reused names**: `df = ...; df = df.dropna(); df = df[...]` — each reassignment creates a new logical node

Implementation: Maintain a **variable version map** (`df_v1`, `df_v2`, etc.) internally to track data lineage through reassignments.

### 5.4 Chained Method Calls

Unpack method chains into individual nodes:

```python
# Single AST statement, but 4 separate lineage nodes:
result = (pd.read_csv("data.csv")    # Node 1: Source
            .dropna()                 # Node 2: Clean
            .query("amount > 100")    # Node 3: Filter
            .to_csv("out.csv"))       # Node 4: Target
```

### 5.5 Loop Handling

Loops containing ETL operations → Show as a **single source→target flow** with a **"Loop" annotation badge** on the relevant nodes.

```python
for file in glob.glob("data/*.csv"):
    df = pd.read_csv(file)
    df.to_sql('combined', engine, if_exists='append')
# → Source("data/*.csv" 🔁) → Target("combined" 🔁)
```

### 5.6 Conditional Branches

`if/else` blocks → Show **both branches** as separate paths with condition annotations on the edges.

### 5.7 Multiple Independent Pipelines

If the script contains two or more disconnected data flows, render them as **separate disconnected graphs** on the same canvas, visually separated with spacing.

### 5.8 Connection String Resolution

| Pattern | Display |
|---------|---------|
| Hardcoded path: `"data/orders.csv"` | `data/orders.csv` |
| Environment variable: `os.environ["DB_HOST"]` | `env(DB_HOST)` |
| Config lookup: `config.get("source")` | `config(source)` |
| Unresolvable | `Unknown Source — line {n}` |

---

## 6. Operation Detection Catalog

### 6.1 Source (Read) Operations — Node Color: 🔵 Blue

`pd.read_csv()`, `pd.read_excel()`, `pd.read_sql()`, `pd.read_sql_table()`, `pd.read_sql_query()`, `pd.read_parquet()`, `pd.read_json()`, `pd.read_html()`, `pd.read_clipboard()`, `pd.read_fwf()`, `pd.read_orc()`, `pd.read_sas()`, `pd.read_spss()`, `pd.read_feather()`, `pd.read_hdf()`, `pd.read_pickle()`, `pd.read_xml()`, `pd.read_stata()`

### 6.2 Target (Write) Operations — Node Color: 🟢 Green

`df.to_csv()`, `df.to_sql()`, `df.to_parquet()`, `df.to_excel()`, `df.to_json()`, `df.to_html()`, `df.to_pickle()`, `df.to_feather()`, `df.to_hdf()`, `df.to_xml()`, `df.to_stata()`, `df.to_orc()`

### 6.3 Filter / Select — Node Color: 🟡 Yellow

`df[condition]`, `.query()`, `.loc[]`, `.iloc[]`, `.where()`, `.mask()`, `.sample()`

### 6.4 Join / Merge — Node Color: 🟠 Orange

`.merge()`, `.join()`, `pd.concat()`

### 6.5 Aggregation — Node Color: 🟣 Purple

`.groupby()`, `.agg()`, `.sum()`, `.mean()`, `.count()`, `.pivot_table()`, `.value_counts()`

### 6.6 Reshape — Node Color: 🔴 Red

`.melt()`, `.pivot()`, `.stack()`, `.unstack()`, `.transpose()`

### 6.7 Clean / Data Quality — Node Color: Teal

`.dropna()`, `.fillna()`, `.drop_duplicates()`, `.replace()`, `.astype()`, `pd.to_datetime()`, `pd.to_numeric()`, `.isna()`, `.isnull()`, `.str.*` accessor methods

### 6.8 Column Operations — Node Color: Slate

`.rename()`, `.drop(columns=)`, `df['new_col'] = ...`, `.assign()`

### 6.9 Sort & Index — Node Color: Brown

`.sort_values()`, `.sort_index()`, `.reset_index()`, `.set_index()`

### 6.10 Apply / Map / Transform — Node Color: Pink

`.apply()`, `.map()`, `.applymap()`, `.transform()`, `pd.json_normalize()`

### 6.11 Unknown / Unparsed — Node Color: Gray

Any operation the parser could not classify.

---

## 7. Description Generation (AST-First, LLM-Optional)

### 7.1 Architecture: Two-Tier Description System

```
┌─────────────────────────────────────────────────┐
│              Description Pipeline                │
│                                                  │
│  Step 1 (ALWAYS): AST Parse + Template Match     │
│  ┌─────────────┐    ┌──────────────────────┐     │
│  │ AST Extract │───▶│ Template Engine       │     │
│  │ method name │    │ Pattern → Description │     │
│  │ arguments   │    │ (covers ~85% nodes)   │     │
│  │ condition   │    └──────────────────────┘     │
│  └─────────────┘                                 │
│                                                  │
│  Step 2 (OPTIONAL): LLM Enrichment               │
│  ┌──────────────────────────────────────────┐    │
│  │ Only fires for:                          │    │
│  │  • Complex lambdas / apply expressions   │    │
│  │  • Unclassified operations (Gray nodes)  │    │
│  │  • Multi-line custom function summaries  │    │
│  │                                          │    │
│  │ Requires: LLM_ENDPOINT env var set       │    │
│  │ Failure mode: Silent fallback to Step 1  │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### 7.2 Tier 1 — Template Engine (Core, Always Runs)

Covers all recognized pandas operations with parameterized templates:

| Pattern | Template Output |
|---------|----------------|
| `pd.read_csv("orders.csv")` | "Reads CSV file: orders.csv" |
| `df.dropna()` | "Removes rows with missing values" |
| `df.dropna(subset=['x','y'])` | "Removes rows with missing values in columns: x, y" |
| `df[df['amount'] > 100]` | "Filters rows where amount > 100" |
| `df.query("status == 'active'")` | "Filters rows where status == 'active'" |
| `df.merge(df2, on='id')` | "Merges with another DataFrame on column: id" |
| `df.merge(df2, on='id', how='left')` | "Left-merges with another DataFrame on column: id" |
| `df.groupby('region').sum()` | "Groups by region and sums all numeric columns" |
| `df.groupby(['a','b']).agg({'c':'mean'})` | "Groups by a, b and aggregates c with mean" |
| `df.to_sql('table', engine)` | "Writes to SQL table: table" |
| `df.rename(columns={'old': 'new'})` | "Renames column: old → new" |
| `df['tax'] = df['amount'] * 0.1` | "Creates column: tax" |
| `df.sort_values('date')` | "Sorts by column: date" |
| `df.apply(func)` | "Applies function: func" |
| `df.apply(lambda x: ...)` | "Applies lambda transformation" |
| *(unrecognized operation)* | "Operation: {method_name} (line {n})" |

The template engine extracts parameters directly from AST nodes (string literals, keyword arguments, comparison operators) — no LLM needed.

### 7.3 Tier 2 — LLM Enrichment (Optional, Graceful Degradation)

**Activation conditions** (ALL must be true):
1. `LLM_ENDPOINT` environment variable is set
2. At least one node has a complex expression the template engine can't describe well

**What triggers LLM enrichment:**
- Complex lambda bodies: `lambda x: x.split('-')[0] if isinstance(x, str) else x`
- Unclassified operations (Gray nodes)
- Custom function bodies that were inlined from call resolution

**Batch call format:**
```json
{
  "task": "generate_descriptions",
  "nodes": [
    {"id": "node_5", "code": "df = df[df['status'].isin(valid_statuses) & (df['amount'] > threshold)]"},
    {"id": "node_12", "code": "result = df.apply(lambda x: process(x), axis=1)"}
  ]
}
```

**Failure handling (graceful degradation):**
1. Batch response malformed or missing items → retry only failed IDs individually
2. Retry also fails → keep template description (already generated in Tier 1)
3. LLM endpoint unreachable → skip entirely, show subtle info toast: "Using template descriptions (AI enrichment unavailable)"
4. `LLM_ENDPOINT` not configured → Tier 2 never fires, no warning shown (this is a valid operating mode)

### 7.4 What Works Without LLM (Everything Essential)

| Feature | Without LLM | With LLM |
|---------|------------|----------|
| Node detection & classification | ✅ Full | ✅ Full |
| Lineage diagram | ✅ Full | ✅ Full |
| Dashboard summary & metrics | ✅ Full | ✅ Full |
| NL descriptions (simple ops) | ✅ Template | ✅ Template |
| NL descriptions (complex lambdas) | ⚠️ Generic ("Applies lambda") | ✅ Rich ("Extracts prefix before hyphen") |
| Unknown operation classification | ⚠️ Shows as Gray "Unknown" node | ✅ May classify correctly |
| Main flow detection (no `__main__`) | ⚠️ Parses all top-level code | ✅ Smarter flow identification |

---

## 8. UI / UX Design

### 8.1 Theme

- **Default**: Dark theme
- **Toggle**: Light/Dark via header toggle, persisted in `localStorage`
- **Primary color**: `#fb4e0b`

### 8.2 Layout

```
┌──────────────────────────────────────────────────┐
│  RSLI Logo    [Theme Toggle]                     │
├──────────────────────────────────────────────────┤
│  [Upload Zone / Paste Area]                      │
│  Drag & drop .py file or paste code              │
│  [Analyze] button                                │
├──────────────────────────────────────────────────┤
│  [Tab: Summary]  [Tab: Lineage]                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  Tab Content Area                                │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 8.3 Tab 1 — Dashboard Summary

Dashboard-style card layout providing instant comprehension:

**Row 1 — Source & Target Cards**

| Card | Content |
|------|---------|
| Sources | List of all read operations with file/table names, format badges (CSV, SQL, etc.) |
| Targets | List of all write operations with file/table names, format badges |

**Row 2 — Operation Metrics (count cards with icons)**

| Card | Content |
|------|---------|
| Joins/Merges | Count of merge, join, concat operations |
| Filters | Count of filter/select operations |
| Aggregations | Count of groupby, agg, pivot_table operations |
| Cleaning | Count of dropna, fillna, dedup, type cast operations |
| Reshapes | Count of melt, pivot, stack operations |
| Column Ops | Count of rename, drop, assign operations |
| Sort/Index | Count of sort, reset_index operations |
| Apply/Map | Count of apply, map, transform operations |

**Row 3 — Script Metadata**

| Info | Content |
|------|---------|
| Total nodes | Count of all detected operations |
| Lines of code | Total lines in the script |
| Independent pipelines | Count of disconnected flows |
| Warnings | Count of unparsed operations (links to error banner) |

### 8.4 Tab 2 — Lineage Diagram

**Layout**: Left-to-right, Alteryx-style, scrollable canvas.

**Nodes**:
- Rounded rectangle shape
- **Color-coded** by operation category (see Section 6)
- **Category icon** (from Lucide) on the left side of the node
- **Mini-label** showing operation + key detail (e.g., "Filter: amount > 100")
- **Loop badge** on nodes inside loops

**Edges**:
- **Curved/angled** connectors (Bezier curves)
- **Variable name** displayed on the edge (e.g., `df`, `cleaned_data`)
- Arrow direction: left → right

**Node Click — Inline Detail Panel** (expands below the clicked node):

| Section | Content |
|---------|---------|
| Description | NL description (template or LLM-generated) |
| Source Code | Raw Python code for this operation, syntax-highlighted |
| Line Number | `Line 42` linking to the position in the original script |
| Schema Info | Columns explicitly referenced in code (partial, honest) |

- **Multiple panels** can be open simultaneously
- Clicking an already-open node **collapses** its panel

### 8.5 Error & Warning States

| State | UI Treatment |
|-------|-------------|
| Python syntax error | Red banner with line number and error message, no tabs shown |
| No ETL ops detected | Info banner: "No ETL operations detected in this script" |
| File too large | Error banner: "File exceeds 2000-line limit" |
| Partially unparsed ops | Warning banner: "Warning: N operations could not be classified" — if LLM configured, attempts classification; otherwise shows Gray nodes |
| LLM not configured | No warning — valid operating mode. Template descriptions used for all nodes |
| LLM configured but unreachable | Subtle info toast: "Using template descriptions (AI enrichment unavailable)" — tool works normally |

---

## 9. API Contract

### 9.1 `POST /api/analyze`

**Request:**
```json
{
  "code": "import pandas as pd\n...",
  "filename": "etl_pipeline.py",
  "enable_llm": true
}
```

**Response:**
```json
{
  "summary": {
    "sources": [{"name": "orders.csv", "format": "csv", "line": 5}],
    "targets": [{"name": "summary_table", "format": "sql", "line": 45}],
    "metrics": {
      "filters": 3,
      "joins": 1,
      "aggregations": 2,
      "cleaning": 4,
      "reshapes": 0,
      "column_ops": 5,
      "sort_index": 1,
      "apply_map": 2
    },
    "total_nodes": 18,
    "total_lines": 156,
    "pipeline_count": 1,
    "warning_count": 0
  },
  "llm_used": false,
  "nodes": [
    {
      "id": "node_1",
      "type": "read",
      "category": "source",
      "method": "read_csv",
      "label": "Read CSV: orders.csv",
      "description": "Reads CSV file: orders.csv",
      "description_source": "template",
      "code": "df = pd.read_csv('orders.csv')",
      "line_number": 5,
      "schema_refs": ["order_id", "amount", "status"],
      "is_loop": false,
      "pipeline_id": 0,
      "variable_out": "df"
    }
  ],
  "edges": [
    {
      "source": "node_1",
      "target": "node_2",
      "variable": "df"
    }
  ],
  "warnings": [
    {
      "line": 32,
      "code": "custom_transform(df)",
      "message": "Could not classify operation"
    }
  ]
}
```

### 9.2 `GET /api/health`

Returns `{"status": "ok"}` for frontend connectivity check.

---

## 10. Edge Cases & Handling Summary

| Edge Case | Handling |
|-----------|----------|
| No `if __name__` guard | AST: Parse entire file top-to-bottom, filter out uncalled definitions. LLM (optional): smarter flow identification |
| Chained method calls (`df.a().b().c()`) | Unpack into individual nodes via recursive AST Call traversal |
| Variable reuse (`df = ...; df = df.x()`) | Internal version map (`df_v1`, `df_v2`) for lineage tracking |
| Unique variable names (`raw → clean → final`) | Track through assignment targets, chain as edges |
| Functions called from main | Resolve call graph, inline function body as sub-nodes |
| Loops with ETL ops | Single flow with loop annotation badge |
| Conditionals (`if/else`) | Show both branches with condition labels on edges |
| Multiple independent pipelines | Disconnected graphs on same canvas with visual separation |
| Dynamic connection strings (`os.environ[...]`) | Show as `env(VAR_NAME)` |
| Config-based connections | Show as `config(key)` |
| Dead code (unreachable functions) | Not parsed (only follow call graph from entry point) |
| `df.apply(lambda x: ...)` | AST: Classified as Apply/Map, generic template. LLM (optional): rich description of lambda body |
| `.str` accessor chains | Classified as Clean with method name |
| `pd.concat([df1, df2])` | Classified as Join/Merge with fan-in edges from both inputs |
| LLM not configured | Tool works fully — template descriptions for all nodes, Gray nodes for unknowns |
| LLM batch partial failure | Retry failed IDs individually, keep template descriptions as fallback |
| LLM total failure | Silent fallback to template-only mode, subtle info toast |

---

## 11. v1 Scope Boundaries

### In Scope (v1)
- Single `.py` file analysis (paste or upload)
- Full AST parsing with function resolution
- All pandas IO + transformation operations
- Alteryx-style left-to-right lineage diagram
- Dashboard summary with operation counts
- Node detail panels (code, NL description, line number, partial schema)
- Dark/light theme
- AST-first template NL descriptions (works without LLM)
- Optional LLM enrichment for complex operations (graceful degradation)
- Variable tracking (aliasing + reuse)
- Chained method unpacking
- Loop & conditional handling
- Multiple disconnected pipeline support

### Out of Scope (v1)
- Multi-file analysis (imports from other `.py` files)
- SQL parsing inside Python strings
- Runtime/instrumented tracing
- Persistence / saved analyses
- User accounts / auth
- Export to PNG/SVG/PDF
- Column-level lineage
- Framework-specific parsing (Airflow DAG objects, dbt models)
- Deployment / containerization
- Collaboration features

---

## 12. File Structure (Planned)

```
rsli/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/              # Shadcn components
│   │   │   ├── UploadZone.jsx   # Drag-drop + paste area
│   │   │   ├── SummaryTab.jsx   # Dashboard cards
│   │   │   ├── LineageTab.jsx   # Diagram canvas
│   │   │   ├── LineageNode.jsx  # Individual node component
│   │   │   ├── LineageEdge.jsx  # Curved connector
│   │   │   ├── NodeDetail.jsx   # Inline expansion panel
│   │   │   └── ThemeToggle.jsx  # Dark/Light switch
│   │   ├── lib/
│   │   │   ├── api.js           # API client (TanStack Query)
│   │   │   └── utils.js         # clsx/twMerge helpers
│   │   ├── store/
│   │   │   └── useAnalysisStore.js  # Zustand store
│   │   ├── App.jsx
│   │   ├── index.css            # Tailwind + design tokens
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── backend/
│   ├── main.py                  # FastAPI app + routes
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── ast_parser.py        # Core AST parsing engine
│   │   ├── operations.py        # Operation detection registry
│   │   ├── variable_tracker.py  # Variable aliasing/versioning
│   │   ├── call_resolver.py     # Function call graph resolution
│   │   └── chain_unpacker.py    # Chained method call unpacking
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py            # Azure AI Foundry client
│   │   ├── templates.py         # NL description templates
│   │   └── batch_describer.py   # Batch description generator
│   ├── models.py                # Pydantic response models
│   └── requirements.txt
└── README.md
```

# COBOL Tracer Architecture Doc

## Summary
- Describe the CLI tracer’s mission: interpret COBOL programs symbolically to enumerate possible execution paths, surface decisions/calls, and flag data uncertainties before exporting either human-readable or JSON output.
- Clarify the primary inputs/outputs so the project implementation doc states what must be delivered: COBOL source + optional copybook dirs/vars → preprocessed AST + `PathState` results → CLI path summary or NDJSON file.
- Reinforce that this plan focuses on architecture and data flow so implementers understand how each subsystem contributes to the overall tracer.

## Component Breakdown
- `main.py` wires the CLI flags to `trace_file`, handling argument parsing (`--entry`, `--vars`, `--copy-dirs`, `--copy-exts`, `--max-steps`, `--max-paths`, `--json`) and printing either detailed summaries or NDJSON records.
- `src/cobol_ast_trace.py` loads the COBOL text, preprocesses copybooks via `src/ibm_preprocess.py`, invokes the parser (`src/cobol_parser.py`), and drives symbolic execution through `perform_paragraph`/`exec_nodes`, eventually deduplicating paths before returning control to the CLI.
- `src/ibm_preprocess.py` normalizes legacy fixed-format layouts, strips comments, expands `COPY` statements (with configurable directories/extensions), and isolates the `PROCEDURE DIVISION` before the parser sees the tokens.
- `src/cobol_parser.py` consumes the line stream, recognizes paragraph labels, structured blocks (`IF`, `EVALUATE`, `EXEC SQL`), and statement-level nodes, exposing a `Program`/`Paragraph` AST (`src/cobol_ast_nodes.py`) that the executor walks.
- `src/cobol_execution.py` performs symbolic evaluation, branching on conditions, handling loops/`PERFORM`, capturing decisions/calls/flags, and enforcing limits (max steps, paths, recursion) to keep runtime bounded for complex COBOL sources.

## Data Flow & Runtime State
- Parser output: `Program` keeps paragraph order and bodies as lists of `Node` subclasses (`Stmt`, `IfStmt`, `EvaluateStmt`, `CallStmt`, `ZCallPgmStmt`, `MoveStmt`, `ComputeStmt`, `PerformStmt`, `ReadStmt`, `GotoStmt`, etc.), allowing structured traversal.
- Execution state: `PathState` tracks `env` (known vars), `callstack`, `calls` history, `decisions` (control flow taken), `flags` (external reads, unknown conditions, recursion limits), and `steps`. Document how environment updates (via `MOVE`, `SET`, `COMPUTE`, `READ`, `PERFORM`, structured statements) propagate through nested control flow.
- Symbolic branching: `exec_nodes` splits on `IF`/`EVALUATE`-driven `Unknown` conditions by cloning the state, labeling branches, and recursing on both paths. `PERFORM ... UNTIL` also duplicates states when the condition is indeterminate before continuing. Explain how this yields multiple `PathState`s before `dedup_paths` collapses equivalent sets.
- Highlight limit handling: `max_steps` appends flags when exceeded; `max_paths` stops further expansion; recursion counts per paragraph guard infinite loops. Mention special `flags` like `EXTERNAL_DATA_DEPENDENCY`, `UNKNOWN_CONDITION`, `EXTERNAL_CALL`, `UNKNOWN_PARAGRAPH`, and how they signal implementation needs (copybook lookups → unresolved copies, etc.).

## CLI Flags & Configuration Influence
- `--entry`: determines the starting paragraph. Document fallback priority (`0000-MAIN`, `MAIN`, `000-MAIN`, `1000-MAIN`, first real paragraph) and `EntryNotFound` logic, so plan explains how implementation docs should describe that behavior.
- `--vars`: seeds `PathState.env` using `parse_value` heuristics (ints, booleans, quoted strings) and uppercases keys. Mention its downstream effect on `eval_condition`/`eval_atom` to produce deterministic path decisions.
- `--copy-dirs` & `--copy-exts`: supply search paths/extensions used by `ibm_preprocess.expand_copybooks`; mention unresolved references log as `*UNRESOLVED_COPY*`.
- `--max-steps` & `--max-paths`: throttle symbolic execution; explain how exceeding them annotates `flags` (`MAX_STEPS_REACHED`, truncated paths) so docs can describe expected behavior.
- `--json`: toggles output format. When enabled, CLI emits NDJSON objects with `calls`, `decisions`, `flags`, known vs unknown env, etc., helping implementers know what fields to document vs when to describe the pretty-print path summary.

## Sample Usage & Inputs
- Reference `datas/chatgpt/PGMB002.cbl` as a canonical input that includes file handling, validation, `IF`/`EVALUATE`, `PERFORM`, and `CALL` logic; explain how the tracer will preprocess it, parse paragraphs (`0000-MAIN`, `1000-INIT`, etc.), branch on priorities/amounts, and record external context (copybook fields: `CPYB-*`).
- Mention other COBOL samples under `datas/` to show variation (batch processing, copybook-heavy cases) and note that tests/docs should refer to these as fixtures to ensure parsing/execution is exercised.
- Describe expected outputs: human-readable path listing (calls summary, decisions, known/unknown vars), plus NDJSON structures capturing `path_id`, `calls`, `decisions`, `flags`, `known_env`, `unknown_env_keys`, and `steps`. Highlight that `flags` (like `EXTERNAL_DATA_DEPENDENCY` from `READ` or `UNKNOWN_CONDITION` from unresolved `IF` conditions) should be documented so implementers know what to expect.

## Test Plan
- Document a regression suite under `tests/` that exercises `trace_file` with:
  - Simple paragraph flows to verify paragraph discovery/dedup (`Program.order`, `Paragraph` contents).
  - Branching/`PERFORM` structures to ensure `PathState.decisions` reflect taken branches and `flags` like `UNKNOWN_CONDITION`.
  - Copybook expansion via `datas/` fixtures to validate `ibm_preprocess.expand_copybooks`, `COPY` resolution, and unresolved-copy markers.
  - `--vars` seeding and numeric comparisons to confirm deterministic path selection when env has known values.
- Add smoke checks that instantiate `PathState` and exercise `exec_nodes` for `MOVE`, `SET`, `READ`, `CALL`, `GO TO`, and `PERFORM`, verifying env updates, `calls` entries, and that `max_steps`/`max_paths` guard rails append expected flags.
- Include assertions that `trace_file` returns deduplicated paths (unique signatures) and that CLI logic increments `WS-PROCESSED-NBR` vs errors when `flags` indicate failures (conceptual expectation for doc; actual CLI tests can mock `print` output or inspect NDJSON).

## Assumptions
- No code edits beyond writing `project_implementation.md`; the plan only documents what will be implemented later.
- Future work will expand the symbolic executor and tests, so this doc explicitly calls out missing/unknown behaviors (unknown condition splits, recursion/call stack limits, copybook lookup order) to guide later engineers.

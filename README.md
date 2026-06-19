# COBOL Documentor

COBOL Documentor is now a .NET 8 / C# toolchain for analysing COBOL sources, resolving copybooks, extracting DATA DIVISION structures, loading PROCEDURE DIVISION statements, and exporting dependency graphs.

The previous Python prototype has been removed from the main project tree. The C# solution is the canonical implementation.

## Projects

- `src/CobolDocumentor/CobolDocumentor.csproj`: core library.
- `src/CobolDocumentor.Cli/CobolDocumentor.Cli.csproj`: command-line entry point.
- `tests/CobolDocumentor.Tests/CobolDocumentor.Tests.csproj`: xUnit tests.

## Pipeline

```text
COBOL source or source folder
  -> recursive program discovery
  -> recursive COPY index
  -> recursive COPY expansion
  -> fixed-format condenser
  -> DATA DIVISION variable parser
  -> PROCEDURE DIVISION paragraph/statement loader
  -> Graphify JSON export
  -> optional standalone HTML/SVG graph export
```

## Supported features

- Recursive program discovery in folders and subfolders.
- Program file detection for `.cbl`, `.cob`, `.cobol`, `.pgm`, `.pco`, `.sqb`.
- Copybook exclusion for `.cpy`, `.cpm`, `.cpx`, `.copy`.
- `PROGRAM-ID` extraction, with file-name fallback.
- Fixed-format sequence area stripping.
- Fixed-format comments/debug lines.
- Logical statement condensation.
- Multi-target `MOVE A TO B C` expansion.
- Multi-target `SET A B TO TRUE` expansion.
- Recursive copybook index over `.cpy`, `.cpm`, `.cpx`, `.copy`.
- Recursive `COPY` expansion with max-depth guard.
- Basic `COPY ... REPLACING ...` support, including fixed-format COPY lines.
- DATA DIVISION groups.
- Level-88 conditions.
- `REDEFINES`.
- `OCCURS`, including `OCCURS n TO m TIMES DEPENDING ON var`.
- Statement classification for `CALL`, `PERFORM`, `READ`, `WRITE`, `REWRITE`, `MOVE`, `SET`, `IF`, `EVALUATE`, etc.
- Graphify-compatible JSON export with nodes/edges.
- Simple standalone HTML graph export using static SVG only.

## CLI usage

Single program:

```bash
dotnet run --project src/CobolDocumentor.Cli -- path/to/program.cbl --graphify-out out/graphify.json
```

Single program with copybooks:

```bash
dotnet run --project src/CobolDocumentor.Cli -- path/to/program.cbl --copy-root path/to/copybooks --graphify-out out/graphify.json
```

Folder mode, with recursive program discovery and recursive copybook lookup:

```bash
dotnet run --project src/CobolDocumentor.Cli -- path/to/source-root --out-dir out/json --html-out out/html
```

With a standalone HTML graph for one program:

```bash
dotnet run --project src/CobolDocumentor.Cli -- path/to/program.cbl --graphify-out out/graphify.json --html-out out/graph.html
```

## Build and test

```bash
dotnet restore CobolDocumentor.CSharp.sln
dotnet build CobolDocumentor.CSharp.sln --configuration Release
dotnet test CobolDocumentor.CSharp.sln --configuration Release
```

## CI and deliverables

The workflow `.github/workflows/dotnet-deliverables.yml` runs on pull requests, matching tags, and manual dispatch.

For pull requests, it:

- restores, builds, and tests the C# solution;
- uploads xUnit/TRX test results;
- publishes self-contained CLI deliverables for `linux-x64` and `win-x64`;
- uploads the ZIP deliverables as workflow artifacts.

For tags matching `v*` or `release-*`, it also creates or updates a GitHub Release and attaches the generated ZIP files.

Generated deliverables are named like:

```text
CobolDocumentor-v1.0.0-linux-x64.zip
CobolDocumentor-v1.0.0-win-x64.zip
```

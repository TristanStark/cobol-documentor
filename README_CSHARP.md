# COBOL Documentor - C# rewrite

This branch contains an autonomous .NET 8 rewrite of the COBOL documentor pipeline.

## Projects

- `src/CobolDocumentor/CobolDocumentor.csproj`: core library.
- `src/CobolDocumentor.Cli/CobolDocumentor.Cli.csproj`: command-line entry point.
- `tests/CobolDocumentor.Tests/CobolDocumentor.Tests.csproj`: xUnit tests.

## Implemented pipeline

```text
COBOL source or source folder
  -> recursive program discovery
  -> recursive COPY index
  -> COPY expansion
  -> fixed-format condenser
  -> DATA DIVISION variable parser
  -> PROCEDURE DIVISION paragraph/statement loader
  -> Graphify JSON export
  -> optional standalone HTML/SVG graph export
```

## Supported COBOL features in this rewrite

- Recursive program discovery in folders and subfolders.
- Program file detection for `.cbl`, `.cob`, `.cobol`, `.pgm`, `.pco`.
- Copybook exclusion for `.cpy`, `.cpm`, `.cpx`.
- Fixed-format sequence area stripping.
- Fixed-format comments/debug lines.
- Logical statement condensation.
- Multi-target `MOVE A TO B C` expansion.
- Multi-target `SET A B TO TRUE` expansion.
- Recursive copybook index over `.cpy`, `.cpm`, `.cpx`.
- Basic `COPY ... REPLACING ...` support.
- DATA DIVISION groups.
- Level-88 conditions.
- `REDEFINES`.
- `OCCURS`, including `OCCURS n TO m TIMES DEPENDING ON var`.
- Statement classification for `CALL`, `PERFORM`, `READ`, `WRITE`, `REWRITE`, `MOVE`, `SET`, `IF`, `EVALUATE`, etc.
- Graphify export with nodes/edges.
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

## Tests

```bash
dotnet test CobolDocumentor.CSharp.sln
```

## Notes

The Python implementation is still present on this branch so the rewrite can be compared safely. The C# projects are autonomous and can become the main implementation once validated against real COBOL samples.

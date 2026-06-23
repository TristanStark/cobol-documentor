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
- Exploration-only mode for collecting missing copybooks without aborting the run.
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

Exploration-only mode, used to find all missing copybooks in one pass:

```bash
dotnet run --project src/CobolDocumentor.Cli -- path/to/source-root --copy-root path/to/partial-copy-root --exploration-only
```

Alias:

```bash
dotnet run --project src/CobolDocumentor.Cli -- path/to/source-root --copy-root path/to/partial-copy-root --explore-only
```

In exploration-only mode, the CLI does not fail when a `COPY` cannot be resolved. It preserves the unresolved `COPY` line, continues scanning available sources and copybooks, disables graph exports, and prints a final `Missing COPY report` to stdout.

The final report contains:

- the unique COPY names to retrieve;
- the total number of missing COPY occurrences;
- the source file where each missing COPY was encountered;
- the nested COPY depth when the missing reference came from another copybook;
- the normalized COPY statement.

## Build and test from source

```bash
dotnet restore CobolDocumentor.CSharp.sln
dotnet build CobolDocumentor.CSharp.sln --configuration Release
dotnet test CobolDocumentor.CSharp.sln --configuration Release
```

## Local binary builds

Windows self-contained build:

```bash
dotnet publish src/CobolDocumentor.Cli/CobolDocumentor.Cli.csproj \
  --configuration Release \
  --runtime win-x64 \
  --self-contained true \
  -p:PublishSingleFile=true \
  -p:IncludeNativeLibrariesForSelfExtract=true \
  --output publish/win-x64
```

Linux self-contained build:

```bash
dotnet publish src/CobolDocumentor.Cli/CobolDocumentor.Cli.csproj \
  --configuration Release \
  --runtime linux-x64 \
  --self-contained true \
  -p:PublishSingleFile=true \
  -p:IncludeNativeLibrariesForSelfExtract=true \
  --output publish/linux-x64
```

## CI, compiled artifacts, and releases

The workflow `.github/workflows/dotnet-deliverables.yml` runs on:

- pull requests targeting `master`, `main`, or `feature/**`;
- pushes to `master` or `main`;
- pushed tags matching `v*` or `release-*`;
- published GitHub Releases;
- manual dispatch.

For pull requests and main-branch pushes, it:

- restores, builds, and tests the C# solution;
- uploads the build log and xUnit/TRX test results;
- publishes self-contained CLI builds for `linux-x64` and `win-x64`;
- uploads the compiled ZIP builds as workflow artifacts.

For tags matching `v*` or `release-*`, or when a GitHub Release is published, it also attaches the compiled builds to the GitHub Release. The release is therefore not limited to GitHub's automatic source-code archives.

Release assets include:

```text
CobolDocumentor-v1.0.0-linux-x64.zip
CobolDocumentor-v1.0.0-win-x64.zip
SHA256SUMS.txt
```

The ZIP files contain the published self-contained CLI executable and the README. `SHA256SUMS.txt` contains checksums for the binary assets.

## Creating a binary release

Create and push a tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The CI will build the Windows and Linux binaries, create or update the GitHub Release for that tag, and upload the compiled ZIP files plus `SHA256SUMS.txt`.

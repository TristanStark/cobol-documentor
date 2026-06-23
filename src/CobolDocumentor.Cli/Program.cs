using CobolDocumentor.Copybooks;
using CobolDocumentor.Discovery;
using CobolDocumentor.Export;
using CobolDocumentor.Parsing;

if (args.Length == 0 || HasFlag(args, "--help"))
{
    Console.WriteLine("Usage: cobol-documentor <program.cbl|source-folder> [--copy-root <folder>] [--graphify-out <graph.json>] [--html-out <graph.html>] [--out-dir <folder>] [--exploration-only]");
    Console.WriteLine();
    Console.WriteLine("Options:");
    Console.WriteLine("  --copy-root <folder>      Root folder used to recursively index copybooks.");
    Console.WriteLine("  --graphify-out <file>     Graphify JSON output for single-file mode.");
    Console.WriteLine("  --html-out <file|folder>  Standalone HTML graph output.");
    Console.WriteLine("  --out-dir <folder>        Graphify JSON output folder for folder mode. Default: out.");
    Console.WriteLine("  --exploration-only        Continue on missing COPY and print all missing COPY names at the end.");
    Console.WriteLine("  --explore-only            Alias for --exploration-only.");
    return args.Length == 0 ? 1 : 0;
}

var sourcePath = args[0];
var copyRoot = ReadOption(args, "--copy-root");
var graphifyOut = ReadOption(args, "--graphify-out");
var htmlOut = ReadOption(args, "--html-out");
var outDir = ReadOption(args, "--out-dir") ?? "out";
var explorationOnly = HasFlag(args, "--exploration-only") || HasFlag(args, "--explore-only");

if (Directory.Exists(sourcePath))
{
    var effectiveCopyRoot = copyRoot ?? sourcePath;
    var resolver = new CopyResolver(
        new CopyLookup(effectiveCopyRoot),
        new CopyResolverOptions { ContinueOnMissingCopy = explorationOnly });
    var loader = new CobolProgramLoader(resolver);
    var programs = CobolProgramDiscovery.DiscoverProgramFiles(sourcePath);
    var explorationErrors = new List<(string SourceFile, string Message)>();

    if (!explorationOnly)
    {
        Directory.CreateDirectory(outDir);
    }

    foreach (var descriptor in programs)
    {
        try
        {
            var program = loader.Load(descriptor.SourceFile);
            if (!explorationOnly)
            {
                var jsonPath = Path.Combine(outDir, program.Name + ".graphify.json");
                GraphifyExporter.Write(program, jsonPath);

                if (!string.IsNullOrWhiteSpace(htmlOut))
                {
                    Directory.CreateDirectory(htmlOut);
                    SimpleHtmlGraphExporter.Write(program, Path.Combine(htmlOut, program.Name + ".html"));
                }

                Console.WriteLine($"Parsed {program.Name}: {descriptor.SourceFile}");
            }
            else
            {
                Console.WriteLine($"Explored {program.Name}: {descriptor.SourceFile}");
            }
        }
        catch (Exception exception) when (explorationOnly)
        {
            explorationErrors.Add((descriptor.SourceFile, exception.Message));
            Console.WriteLine($"Exploration warning: {descriptor.SourceFile}: {exception.Message}");
        }
    }

    Console.WriteLine($"Programs discovered: {programs.Count}");
    Console.WriteLine(explorationOnly ? "Exploration-only mode: graph exports disabled." : $"Output folder: {outDir}");
    PrintExplorationErrors(explorationErrors);
    PrintMissingCopies(resolver.MissingCopies);
    return 0;
}

var effectiveSingleCopyRoot = copyRoot;
if (explorationOnly && string.IsNullOrWhiteSpace(effectiveSingleCopyRoot))
{
    effectiveSingleCopyRoot = Path.GetDirectoryName(Path.GetFullPath(sourcePath));
}

CopyLookup? lookup = null;
if (!string.IsNullOrWhiteSpace(effectiveSingleCopyRoot))
{
    lookup = new CopyLookup(effectiveSingleCopyRoot);
}

var singleResolver = new CopyResolver(
    lookup,
    new CopyResolverOptions { ContinueOnMissingCopy = explorationOnly });
var singleLoader = new CobolProgramLoader(singleResolver);
var singleProgram = singleLoader.Load(sourcePath);

if (!explorationOnly)
{
    var singleGraphifyOut = graphifyOut ?? Path.ChangeExtension(sourcePath, ".graphify.json");
    GraphifyExporter.Write(singleProgram, singleGraphifyOut);

    if (!string.IsNullOrWhiteSpace(htmlOut))
    {
        SimpleHtmlGraphExporter.Write(singleProgram, htmlOut);
    }

    Console.WriteLine($"Parsed {singleProgram.Name}");
    Console.WriteLine($"Variables: {singleProgram.MemoryStack.KnownVariables.Count}");
    Console.WriteLine($"Paragraphs: {singleProgram.Paragraphs.Count}");
    Console.WriteLine($"Graphify export: {singleGraphifyOut}");
    Console.WriteLine(!string.IsNullOrWhiteSpace(htmlOut) ? $"HTML graph export: {htmlOut}" : "HTML graph export: disabled");
}
else
{
    Console.WriteLine($"Explored {singleProgram.Name}");
    Console.WriteLine($"Variables discovered from available copies: {singleProgram.MemoryStack.KnownVariables.Count}");
    Console.WriteLine($"Paragraphs: {singleProgram.Paragraphs.Count}");
    Console.WriteLine("Exploration-only mode: graph exports disabled.");
}

PrintMissingCopies(singleResolver.MissingCopies);
return 0;

static string? ReadOption(string[] values, string optionName)
{
    for (var i = 0; i < values.Length - 1; i++)
    {
        if (values[i].Equals(optionName, StringComparison.OrdinalIgnoreCase))
        {
            return values[i + 1];
        }
    }

    return null;
}

static bool HasFlag(string[] values, string flagName)
{
    return values.Any(value => value.Equals(flagName, StringComparison.OrdinalIgnoreCase));
}

static void PrintExplorationErrors(IReadOnlyCollection<(string SourceFile, string Message)> errors)
{
    if (errors.Count == 0)
    {
        return;
    }

    Console.WriteLine();
    Console.WriteLine("=== Exploration warnings ===");
    foreach (var error in errors)
    {
        Console.WriteLine($"- {error.SourceFile}");
        Console.WriteLine($"  {error.Message}");
    }
}

static void PrintMissingCopies(IReadOnlyCollection<MissingCopyReference> missingCopies)
{
    Console.WriteLine();
    Console.WriteLine("=== Missing COPY report ===");
    if (missingCopies.Count == 0)
    {
        Console.WriteLine("No missing COPY found.");
        return;
    }

    var groups = missingCopies
        .GroupBy(copy => copy.CopyName, StringComparer.OrdinalIgnoreCase)
        .OrderBy(group => group.Key, StringComparer.OrdinalIgnoreCase)
        .ToArray();

    Console.WriteLine($"Missing COPY names: {groups.Length}");
    Console.WriteLine($"Missing COPY occurrences: {missingCopies.Count}");
    Console.WriteLine();
    Console.WriteLine("Copy names to retrieve:");
    foreach (var group in groups)
    {
        Console.WriteLine(group.Key);
    }

    Console.WriteLine();
    Console.WriteLine("Details:");
    foreach (var group in groups)
    {
        Console.WriteLine($"- {group.Key} ({group.Count()} occurrence(s))");
        foreach (var occurrence in group.OrderBy(item => item.SourceFile, StringComparer.OrdinalIgnoreCase))
        {
            Console.WriteLine($"  source: {occurrence.SourceFile}");
            if (occurrence.Depth > 0)
            {
                Console.WriteLine($"  nested depth: {occurrence.Depth}");
            }

            Console.WriteLine($"  statement: {occurrence.Statement}");
        }
    }
}

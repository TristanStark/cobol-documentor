using CobolDocumentor.Copybooks;
using CobolDocumentor.Discovery;
using CobolDocumentor.Export;
using CobolDocumentor.Parsing;

if (args.Length == 0 || args.Contains("--help"))
{
    Console.WriteLine("Usage: cobol-documentor <program.cbl|source-folder> [--copy-root <folder>] [--graphify-out <graph.json>] [--html-out <graph.html>] [--out-dir <folder>]");
    return args.Length == 0 ? 1 : 0;
}

var sourcePath = args[0];
var copyRoot = ReadOption(args, "--copy-root");
var graphifyOut = ReadOption(args, "--graphify-out");
var htmlOut = ReadOption(args, "--html-out");
var outDir = ReadOption(args, "--out-dir") ?? "out";

if (Directory.Exists(sourcePath))
{
    var effectiveCopyRoot = copyRoot ?? sourcePath;
    var loader = new CobolProgramLoader(new CopyResolver(new CopyLookup(effectiveCopyRoot)));
    var programs = CobolProgramDiscovery.DiscoverProgramFiles(sourcePath);
    Directory.CreateDirectory(outDir);

    foreach (var descriptor in programs)
    {
        var program = loader.Load(descriptor.SourceFile);
        var jsonPath = Path.Combine(outDir, program.Name + ".graphify.json");
        GraphifyExporter.Write(program, jsonPath);

        if (!string.IsNullOrWhiteSpace(htmlOut))
        {
            Directory.CreateDirectory(htmlOut);
            SimpleHtmlGraphExporter.Write(program, Path.Combine(htmlOut, program.Name + ".html"));
        }

        Console.WriteLine($"Parsed {program.Name}: {descriptor.SourceFile}");
    }

    Console.WriteLine($"Programs discovered: {programs.Count}");
    Console.WriteLine($"Output folder: {outDir}");
    return 0;
}

CopyLookup? lookup = null;
if (!string.IsNullOrWhiteSpace(copyRoot))
{
    lookup = new CopyLookup(copyRoot);
}

var singleLoader = new CobolProgramLoader(new CopyResolver(lookup));
var singleProgram = singleLoader.Load(sourcePath);
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

using CobolDocumentor.Copybooks;
using CobolDocumentor.Export;
using CobolDocumentor.Parsing;

if (args.Length == 0 || args.Contains("--help"))
{
    Console.WriteLine("Usage: cobol-documentor <program.cbl> [--copy-root <folder>] [--graphify-out <graph.json>] [--html-out <graph.html>]");
    return args.Length == 0 ? 1 : 0;
}

var sourceFile = args[0];
var copyRoot = ReadOption(args, "--copy-root");
var graphifyOut = ReadOption(args, "--graphify-out") ?? Path.ChangeExtension(sourceFile, ".graphify.json");
var htmlOut = ReadOption(args, "--html-out");

CopyLookup? lookup = null;
if (!string.IsNullOrWhiteSpace(copyRoot))
{
    lookup = new CopyLookup(copyRoot);
}

var loader = new CobolProgramLoader(new CopyResolver(lookup));
var program = loader.Load(sourceFile);
GraphifyExporter.Write(program, graphifyOut);

if (!string.IsNullOrWhiteSpace(htmlOut))
{
    SimpleHtmlGraphExporter.Write(program, htmlOut);
}

Console.WriteLine($"Parsed {program.Name}");
Console.WriteLine($"Variables: {program.MemoryStack.KnownVariables.Count}");
Console.WriteLine($"Paragraphs: {program.Paragraphs.Count}");
Console.WriteLine($"Graphify export: {graphifyOut}");
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

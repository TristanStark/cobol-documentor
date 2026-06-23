using CobolDocumentor.Copybooks;
using CobolDocumentor.Discovery;
using CobolDocumentor.Export;
using CobolDocumentor.Parsing;
using Xunit;

namespace CobolDocumentor.Tests;

public sealed class RecursiveDiscoveryAndCopiesTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "cobol-documentor-" + Guid.NewGuid().ToString("N"));

    public RecursiveDiscoveryAndCopiesTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public void DiscoveryFindsProgramsRecursivelyAndSkipsCopybooks()
    {
        Write("src/level1/alpha.cbl", "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. ALPHA.\n       PROCEDURE DIVISION.\n       MAIN.\n           GOBACK.\n");
        Write("src/level1/level2/beta.cob", "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. BETA.\n       PROCEDURE DIVISION.\n       MAIN.\n           GOBACK.\n");
        Write("copy/SHARED.cpy", "       01 SHARED-AREA.\n");

        var programs = CobolProgramDiscovery.DiscoverProgramFiles(_root);
        var ids = programs.Select(program => program.ProgramId).ToHashSet(StringComparer.OrdinalIgnoreCase);

        Assert.Equal(2, programs.Count);
        Assert.Contains("ALPHA", ids);
        Assert.Contains("BETA", ids);
        Assert.DoesNotContain("SHARED", ids);
    }

    [Fact]
    public void LoaderExpandsNestedCopiesAndPreservesRedefines()
    {
        Write("copies/BASECPY.cpy", "       01 WS-AREA.\n       COPY NESTEDCPY.\n");
        Write("copies/NESTEDCPY.cpy", "          05 WS-COUNT PIC 9(02).\n          05 WS-BASE PIC X(02).\n          05 WS-ALT REDEFINES WS-BASE PIC X(02).\n");
        var programFile = Write("programs/sub/realpgm.cbl", "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. REALPGM.\n       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n000100 COPY BASECPY.\n       PROCEDURE DIVISION.\n       0000-MAIN.\n           MOVE WS-ALT TO WS-COUNT.\n           GOBACK.\n");

        var loader = new CobolProgramLoader(new CopyResolver(new CopyLookup(_root)));
        var program = loader.Load(programFile);
        var graph = GraphifyExporter.Export(program);

        Assert.Equal("REALPGM", program.Name);
        Assert.True(program.MemoryStack.Contains("WS-ALT"));
        Assert.True(program.MemoryStack.Contains("WS-COUNT"));
        Assert.True(graph.Edges.Any(edge => edge["source"]?.ToString() == "variable:ws-alt" && edge["target"]?.ToString() == "variable:ws-base" && edge["relation"]?.ToString() == "redefines"));
        Assert.True(graph.Edges.Any(edge => edge["target"]?.ToString() == "variable:ws-alt" && edge["relation"]?.ToString() == "references"));
    }

    [Fact]
    public void ExplorationModeCollectsMissingCopiesWithoutThrowing()
    {
        Write("copies/FOUNDCPY.cpy", "       01 FOUND-AREA.\n          05 FOUND-FIELD PIC X(01).\n       COPY NESTED-MISSING.\n");
        var programFile = Write("programs/sub/explore.cbl", "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. EXPLORE.\n       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n       COPY FOUNDCPY.\n       COPY TOP-MISSING.\n       PROCEDURE DIVISION.\n       0000-MAIN.\n           GOBACK.\n");
        var resolver = new CopyResolver(
            new CopyLookup(_root),
            new CopyResolverOptions { ContinueOnMissingCopy = true });
        var loader = new CobolProgramLoader(resolver);

        var program = loader.Load(programFile);
        var missingNames = resolver.MissingCopies.Select(copy => copy.CopyName).OrderBy(name => name, StringComparer.OrdinalIgnoreCase).ToArray();

        Assert.Equal("EXPLORE", program.Name);
        Assert.True(program.MemoryStack.Contains("FOUND-FIELD"));
        Assert.Equal(new[] { "NESTED-MISSING", "TOP-MISSING" }, missingNames);
        Assert.True(resolver.MissingCopies.Any(copy => copy.SourceFile.EndsWith("FOUNDCPY.cpy", StringComparison.OrdinalIgnoreCase)));
        Assert.True(resolver.MissingCopies.Any(copy => copy.SourceFile.EndsWith("explore.cbl", StringComparison.OrdinalIgnoreCase)));
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }

    private string Write(string relativePath, string content)
    {
        var path = Path.Combine(_root, relativePath.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, content);
        return path;
    }
}

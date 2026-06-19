using CobolDocumentor.Copybooks;
using CobolDocumentor.Discovery;
using CobolDocumentor.Parsing;
using Xunit;

namespace CobolDocumentor.Tests;

public sealed class RecursiveDiscoveryTests
{
    [Fact]
    public void DiscoveryFindsProgramsInSubfoldersAndIgnoresCopybooks()
    {
        var root = CreateTempRoot();
        try
        {
            Directory.CreateDirectory(Path.Combine(root, "programs", "nested"));
            Directory.CreateDirectory(Path.Combine(root, "copies", "shared"));

            var mainProgram = Path.Combine(root, "programs", "nested", "MAIN.cbl");
            var otherProgram = Path.Combine(root, "programs", "OTHER.pgm");
            var copyBook = Path.Combine(root, "copies", "shared", "COMMON.cpy");

            File.WriteAllText(mainProgram, ProgramText("MAINPGM", "COPY COMMON."));
            File.WriteAllText(otherProgram, ProgramText("OTHERPGM", "05 WS-OTHER PIC X(01)."));
            File.WriteAllText(copyBook, string.Join(Environment.NewLine,
            [
                "       05 WS-COUNT PIC 9(02).",
                "       05 WS-ALT REDEFINES WS-COUNT PIC X(02)."
            ]));

            var discovered = CobolProgramDiscovery.DiscoverProgramFiles(root);

            Assert.Equal(2, discovered.Count);
            Assert.True(discovered.Any(program => program.ProgramId == "MAINPGM"));
            Assert.True(discovered.Any(program => program.ProgramId == "OTHERPGM"));
            Assert.False(discovered.Any(program => program.SourceFile.EndsWith("COMMON.cpy", StringComparison.OrdinalIgnoreCase)));
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public void LoaderResolvesRecursiveCopiesAndKeepsRedefines()
    {
        var root = CreateTempRoot();
        try
        {
            Directory.CreateDirectory(Path.Combine(root, "programs", "nested"));
            Directory.CreateDirectory(Path.Combine(root, "copies", "shared"));

            var mainProgram = Path.Combine(root, "programs", "nested", "MAIN.cbl");
            var copyBook = Path.Combine(root, "copies", "shared", "COMMON.cpy");

            File.WriteAllText(mainProgram, ProgramText("MAINPGM", "COPY COMMON."));
            File.WriteAllText(copyBook, string.Join(Environment.NewLine,
            [
                "       05 WS-COUNT PIC 9(02).",
                "       05 WS-ALT REDEFINES WS-COUNT PIC X(02)."
            ]));

            var loader = new CobolProgramLoader(new CopyResolver(new CopyLookup(root)));
            var program = loader.Load(mainProgram);
            var rootVariable = program.MemoryStack.Variables.Single();
            var variables = rootVariable.Children.ToDictionary(variable => variable.Name);

            Assert.Equal("MAINPGM", program.Name);
            Assert.True(program.MemoryStack.Contains("WS-ALT"));
            Assert.Equal("WS-COUNT", variables["WS-ALT"].Redefines);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    private static string ProgramText(string programId, string workingStorageLine)
    {
        return string.Join(Environment.NewLine,
        [
            "       IDENTIFICATION DIVISION.",
            $"       PROGRAM-ID. {programId}.",
            "       DATA DIVISION.",
            "       WORKING-STORAGE SECTION.",
            "       01 CUSTOMER-AREA.",
            $"       {workingStorageLine}",
            "       PROCEDURE DIVISION.",
            "       0000-MAIN.",
            "           GOBACK."
        ]);
    }

    private static string CreateTempRoot()
    {
        var root = Path.Combine(Path.GetTempPath(), "CobolDocumentorTests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        return root;
    }
}

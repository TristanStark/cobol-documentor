using System.Text.RegularExpressions;

namespace CobolDocumentor.Discovery;

/// <summary>Finds COBOL programs in a directory tree.</summary>
public static class CobolProgramDiscovery
{
    private static readonly HashSet<string> ProgramExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".cbl", ".cob", ".cobol", ".pgm", ".pco"
    };

    private static readonly HashSet<string> CopyExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".cpy", ".cpm", ".cpx"
    };

    /// <summary>Recursively discovers COBOL program files below <paramref name="rootFolder" />.</summary>
    public static IReadOnlyList<DiscoveredCobolProgram> DiscoverProgramFiles(string rootFolder)
    {
        if (!Directory.Exists(rootFolder))
        {
            throw new DirectoryNotFoundException(rootFolder);
        }

        return Directory.EnumerateFiles(rootFolder, "*.*", SearchOption.AllDirectories)
            .Where(IsProgramCandidate)
            .Select(CreateDescriptor)
            .Where(program => program is not null)
            .Cast<DiscoveredCobolProgram>()
            .OrderBy(program => program.SourceFile, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    /// <summary>Returns true when a file looks like a COBOL program and not a copybook.</summary>
    public static bool IsProgramFile(string filePath)
    {
        return IsProgramCandidate(filePath) && CreateDescriptor(filePath) is not null;
    }

    /// <summary>Extracts PROGRAM-ID from a COBOL source text.</summary>
    public static string? ExtractProgramId(string sourceText)
    {
        var match = Regex.Match(sourceText, @"\bPROGRAM-ID\s*\.\s*([A-Z0-9_-]+)", RegexOptions.IgnoreCase);
        return match.Success ? match.Groups[1].Value.Trim().TrimEnd('.').ToUpperInvariant() : null;
    }

    private static bool IsProgramCandidate(string filePath)
    {
        var extension = Path.GetExtension(filePath);
        return ProgramExtensions.Contains(extension) && !CopyExtensions.Contains(extension);
    }

    private static DiscoveredCobolProgram? CreateDescriptor(string filePath)
    {
        var text = File.ReadAllText(filePath);
        var hasProgramMarker = text.Contains("PROGRAM-ID", StringComparison.OrdinalIgnoreCase)
            || text.Contains("PROCEDURE DIVISION", StringComparison.OrdinalIgnoreCase);
        if (!hasProgramMarker)
        {
            return null;
        }

        var programId = ExtractProgramId(text) ?? Path.GetFileNameWithoutExtension(filePath).ToUpperInvariant();
        return new DiscoveredCobolProgram(programId, Path.GetFullPath(filePath));
    }
}

/// <summary>Describes one discovered COBOL program file.</summary>
public sealed record DiscoveredCobolProgram(string ProgramId, string SourceFile);

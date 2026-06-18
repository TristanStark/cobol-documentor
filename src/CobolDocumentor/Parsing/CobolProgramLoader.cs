using CobolDocumentor.Copybooks;
using CobolDocumentor.Model;
using CobolDocumentor.Preprocessing;

namespace CobolDocumentor.Parsing;

/// <summary>Loads COBOL source files into the C# domain model.</summary>
public sealed class CobolProgramLoader
{
    private readonly CopyResolver _copyResolver;

    /// <summary>Creates a loader.</summary>
    public CobolProgramLoader(CopyResolver? copyResolver = null) => _copyResolver = copyResolver ?? new CopyResolver();

    /// <summary>Loads and parses one COBOL source file.</summary>
    public CobolProgramModel Load(string sourceFile)
    {
        if (!File.Exists(sourceFile))
        {
            throw new FileNotFoundException(sourceFile);
        }

        var expandedLines = _copyResolver.ExpandFile(sourceFile);
        var statements = CobolCondenser.CondenseLines(expandedLines);
        var program = new CobolProgramModel(Path.GetFileNameWithoutExtension(sourceFile).ToUpperInvariant(), sourceFile);

        var dataDeclarations = new List<string>();
        CobolParagraph? currentParagraph = null;
        var currentSection = CobolSection.None;

        foreach (var statement in statements)
        {
            var upper = statement.Trim().ToUpperInvariant();
            if (upper.StartsWith("IDENTIFICATION DIVISION", StringComparison.Ordinal))
            {
                currentSection = CobolSection.Identification;
                continue;
            }

            if (upper.StartsWith("ENVIRONMENT DIVISION", StringComparison.Ordinal))
            {
                currentSection = CobolSection.Environment;
                continue;
            }

            if (upper.StartsWith("DATA DIVISION", StringComparison.Ordinal))
            {
                currentSection = CobolSection.Data;
                continue;
            }

            if (upper.StartsWith("PROCEDURE DIVISION", StringComparison.Ordinal))
            {
                program.MemoryStack = CobolMemoryStack.FromDeclarations(dataDeclarations);
                currentSection = CobolSection.Procedure;
                continue;
            }

            if (currentSection == CobolSection.Data && LooksLikeDataDeclaration(statement))
            {
                dataDeclarations.Add(statement);
                continue;
            }

            if (currentSection != CobolSection.Procedure)
            {
                continue;
            }

            if (LooksLikeParagraphLabel(statement))
            {
                currentParagraph = new CobolParagraph(statement);
                program.Paragraphs.Add(currentParagraph);
                continue;
            }

            if (currentParagraph is null)
            {
                continue;
            }

            currentParagraph.Statements.Add(ParseStatement(statement));
        }

        if (program.MemoryStack.Variables.Count == 0 && dataDeclarations.Count > 0)
        {
            program.MemoryStack = CobolMemoryStack.FromDeclarations(dataDeclarations);
        }

        return program;
    }

    /// <summary>Parses one normalized COBOL logical statement.</summary>
    public static CobolStatement ParseStatement(string rawStatement)
    {
        var trimmed = rawStatement.Trim();
        var upper = trimmed.ToUpperInvariant();
        var kind = upper switch
        {
            var text when text.StartsWith("IF ", StringComparison.Ordinal) => CobolStatementKind.If,
            var text when text.StartsWith("EVALUATE ", StringComparison.Ordinal) => CobolStatementKind.Evaluate,
            var text when text.StartsWith("PERFORM ", StringComparison.Ordinal) => CobolStatementKind.Perform,
            var text when text.StartsWith("CALL ", StringComparison.Ordinal) => CobolStatementKind.Call,
            var text when text.StartsWith("READ ", StringComparison.Ordinal) => CobolStatementKind.Read,
            var text when text.StartsWith("WRITE ", StringComparison.Ordinal) => CobolStatementKind.Write,
            var text when text.StartsWith("REWRITE ", StringComparison.Ordinal) => CobolStatementKind.Rewrite,
            var text when text.StartsWith("OPEN ", StringComparison.Ordinal) => CobolStatementKind.Open,
            var text when text.StartsWith("CLOSE ", StringComparison.Ordinal) => CobolStatementKind.Close,
            var text when text.StartsWith("MOVE ", StringComparison.Ordinal) => CobolStatementKind.Move,
            var text when text.StartsWith("SET ", StringComparison.Ordinal) => CobolStatementKind.Set,
            var text when text.StartsWith("COMPUTE ", StringComparison.Ordinal) => CobolStatementKind.Compute,
            var text when text.StartsWith("DISPLAY ", StringComparison.Ordinal) => CobolStatementKind.Display,
            "GOBACK" or "GO BACK" => CobolStatementKind.Goback,
            _ => CobolStatementKind.Line
        };

        return new CobolStatement(kind, trimmed);
    }

    private static bool LooksLikeDataDeclaration(string statement)
    {
        var trimmed = statement.TrimStart();
        return trimmed.Length >= 2 && char.IsDigit(trimmed[0]) && char.IsDigit(trimmed[1]);
    }

    private static bool LooksLikeParagraphLabel(string statement)
    {
        var trimmed = statement.Trim();
        if (!trimmed.EndsWith('.', StringComparison.Ordinal) || trimmed[..^1].Contains(' '))
        {
            return false;
        }

        var label = trimmed.TrimEnd('.');
        return !label.EndsWith("DIVISION", StringComparison.OrdinalIgnoreCase)
            && !label.EndsWith("SECTION", StringComparison.OrdinalIgnoreCase)
            && !IsCobolVerb(label);
    }

    private static bool IsCobolVerb(string value)
    {
        return new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "MOVE", "SET", "CALL", "PERFORM", "IF", "EVALUATE", "READ", "WRITE", "REWRITE", "OPEN", "CLOSE", "DISPLAY", "COMPUTE", "GOBACK", "GO"
        }.Contains(value);
    }

    private enum CobolSection
    {
        None,
        Identification,
        Environment,
        Data,
        Procedure
    }
}

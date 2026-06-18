using System.Text.RegularExpressions;

namespace CobolDocumentor.Model;

/// <summary>Represents a parsed COBOL program.</summary>
public sealed class CobolProgramModel
{
    /// <summary>Initializes a new parsed program.</summary>
    public CobolProgramModel(string name, string sourceFile)
    {
        Name = name;
        SourceFile = sourceFile;
    }

    /// <summary>Program name or source-derived fallback.</summary>
    public string Name { get; }

    /// <summary>Path of the source COBOL file.</summary>
    public string SourceFile { get; }

    /// <summary>Parsed DATA DIVISION declarations.</summary>
    public CobolMemoryStack MemoryStack { get; set; } = new();

    /// <summary>Parsed PROCEDURE DIVISION paragraphs.</summary>
    public List<CobolParagraph> Paragraphs { get; } = [];
}

/// <summary>Represents one PROCEDURE DIVISION paragraph.</summary>
public sealed class CobolParagraph
{
    /// <summary>Creates a paragraph.</summary>
    public CobolParagraph(string name) => Name = CleanLabel(name);

    /// <summary>Paragraph name.</summary>
    public string Name { get; }

    /// <summary>Statements contained in the paragraph.</summary>
    public List<CobolStatement> Statements { get; } = [];

    private static string CleanLabel(string value) => value.Trim().TrimEnd('.');
}

/// <summary>Supported statement categories for documentation and graph export.</summary>
public enum CobolStatementKind
{
    /// <summary>Unclassified COBOL statement.</summary>
    Line,
    /// <summary>IF block.</summary>
    If,
    /// <summary>EVALUATE block.</summary>
    Evaluate,
    /// <summary>PERFORM statement.</summary>
    Perform,
    /// <summary>CALL statement.</summary>
    Call,
    /// <summary>READ statement.</summary>
    Read,
    /// <summary>WRITE statement.</summary>
    Write,
    /// <summary>REWRITE statement.</summary>
    Rewrite,
    /// <summary>OPEN statement.</summary>
    Open,
    /// <summary>CLOSE statement.</summary>
    Close,
    /// <summary>MOVE statement.</summary>
    Move,
    /// <summary>SET statement.</summary>
    Set,
    /// <summary>COMPUTE statement.</summary>
    Compute,
    /// <summary>DISPLAY statement.</summary>
    Display,
    /// <summary>GOBACK or GO BACK statement.</summary>
    Goback
}

/// <summary>Represents a parsed COBOL statement.</summary>
public sealed class CobolStatement
{
    /// <summary>Creates a statement.</summary>
    public CobolStatement(CobolStatementKind kind, string rawText)
    {
        Kind = kind;
        RawText = rawText.Trim();
    }

    /// <summary>Statement kind.</summary>
    public CobolStatementKind Kind { get; }

    /// <summary>Original normalized statement text.</summary>
    public string RawText { get; }

    /// <summary>Nested child statements.</summary>
    public List<CobolStatement> Children { get; } = [];

    /// <summary>ELSE branch statements for IF blocks.</summary>
    public List<CobolStatement> ElseChildren { get; } = [];

    /// <summary>True when the statement is a CALL 'ZCALLPGM'.</summary>
    public bool IsZCallPgm => Regex.IsMatch(RawText, "^CALL\\s+['\"]?ZCALLPGM['\"]?", RegexOptions.IgnoreCase);
}

/// <summary>Represents DATA DIVISION declarations and lookup tables.</summary>
public sealed class CobolMemoryStack
{
    /// <summary>Root-level variables.</summary>
    public List<CobolVariable> Variables { get; } = [];

    /// <summary>All known variable and level-88 condition names.</summary>
    public HashSet<string> KnownVariables { get; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Builds a memory stack from normalized COBOL declaration lines.</summary>
    public static CobolMemoryStack FromDeclarations(IEnumerable<string> declarations)
    {
        var memory = new CobolMemoryStack();
        var groupStack = new Stack<(int Level, CobolVariable Variable)>();
        CobolVariable? lastVariable = null;

        foreach (var declaration in declarations)
        {
            var variable = CobolVariable.Parse(declaration);
            if (variable is null)
            {
                continue;
            }

            if (variable.Level == 88)
            {
                if (lastVariable is null)
                {
                    throw new InvalidOperationException($"Level 88 without parent variable: {declaration}");
                }

                lastVariable.Conditions.Add(variable);
                continue;
            }

            while (groupStack.Count > 0 && groupStack.Peek().Level >= variable.Level)
            {
                groupStack.Pop();
            }

            if (groupStack.Count > 0)
            {
                groupStack.Peek().Variable.Children.Add(variable);
            }
            else
            {
                memory.Variables.Add(variable);
            }

            lastVariable = variable;

            if (variable.IsGroup)
            {
                groupStack.Push((variable.Level, variable));
            }
        }

        foreach (var variable in memory.Variables)
        {
            foreach (var knownName in variable.GetKnownNames())
            {
                memory.KnownVariables.Add(knownName);
            }
        }

        return memory;
    }

    /// <summary>Returns true when a variable or condition exists.</summary>
    public bool Contains(string name) => KnownVariables.Contains(name);
}

/// <summary>Represents one COBOL variable, group, array item, redefine, or level-88 condition.</summary>
public sealed class CobolVariable
{
    private static readonly HashSet<string> ClauseKeywords = new(StringComparer.OrdinalIgnoreCase)
    {
        "PIC", "PICTURE", "VALUE", "VALUES", "REDEFINES", "OCCURS", "USAGE", "DEPENDING", "INDEXED", "SIGN",
        "SYNC", "SYNCHRONIZED", "BLANK", "JUST", "JUSTIFIED", "COMP", "COMP-1", "COMP-2", "COMP-3", "COMP-4", "COMP-5",
        "COMPUTATIONAL", "COMPUTATIONAL-1", "COMPUTATIONAL-2", "COMPUTATIONAL-3", "COMPUTATIONAL-4", "COMPUTATIONAL-5",
        "PACKED-DECIMAL", "DISPLAY", "BINARY"
    };

    private static readonly HashSet<string> UsageKeywords = new(StringComparer.OrdinalIgnoreCase)
    {
        "BINARY", "COMP", "COMP-1", "COMP-2", "COMP-3", "COMP-4", "COMP-5", "COMPUTATIONAL", "COMPUTATIONAL-1",
        "COMPUTATIONAL-2", "COMPUTATIONAL-3", "COMPUTATIONAL-4", "COMPUTATIONAL-5", "DISPLAY", "INDEX", "PACKED-DECIMAL"
    };

    /// <summary>Original declaration.</summary>
    public string RawText { get; init; } = string.Empty;

    /// <summary>COBOL level number.</summary>
    public int Level { get; init; }

    /// <summary>Variable name.</summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>PIC/PICTURE clause.</summary>
    public string? Picture { get; init; }

    /// <summary>USAGE clause or implicit usage keyword.</summary>
    public string? Usage { get; init; }

    /// <summary>VALUE clause.</summary>
    public string? Value { get; init; }

    /// <summary>Name of the redefined variable.</summary>
    public string? Redefines { get; init; }

    /// <summary>Raw OCCURS clause.</summary>
    public string? Occurs { get; init; }

    /// <summary>Minimum occurrence count.</summary>
    public int? OccursMin { get; init; }

    /// <summary>Maximum occurrence count.</summary>
    public int? OccursMax { get; init; }

    /// <summary>DEPENDING ON variable for variable-length arrays.</summary>
    public string? DependsOn { get; init; }

    /// <summary>INDEXED BY names.</summary>
    public List<string> IndexedBy { get; init; } = [];

    /// <summary>Child variables for group items.</summary>
    public List<CobolVariable> Children { get; } = [];

    /// <summary>Level-88 condition names attached to this variable.</summary>
    public List<CobolVariable> Conditions { get; } = [];

    /// <summary>True when the item is a group item.</summary>
    public bool IsGroup => Picture is null && Level != 88;

    /// <summary>Parses a COBOL data declaration.</summary>
    public static CobolVariable? Parse(string declaration)
    {
        var tokens = Tokenize(declaration).ToArray();
        if (tokens.Length < 2 || !int.TryParse(tokens[0], out var level))
        {
            return null;
        }

        var variable = new CobolVariable
        {
            RawText = declaration.Trim(),
            Level = level,
            Name = tokens[1],
            Redefines = TokenAfter(tokens, "REDEFINES"),
            Picture = ExtractClause(tokens, "PIC", "PICTURE"),
            Usage = ExtractUsage(tokens),
            Value = ExtractClause(tokens, "VALUE", "VALUES"),
            IndexedBy = ExtractIndexedBy(tokens)
        };

        var occurs = ExtractOccurs(tokens);
        return variable with { Occurs = occurs.Raw, OccursMin = occurs.Min, OccursMax = occurs.Max, DependsOn = occurs.DependsOn };
    }

    /// <summary>Returns every known name below this declaration.</summary>
    public IEnumerable<string> GetKnownNames()
    {
        yield return Name;
        foreach (var condition in Conditions)
        {
            yield return condition.Name;
        }

        foreach (var child in Children)
        {
            foreach (var name in child.GetKnownNames())
            {
                yield return name;
            }
        }
    }

    private static IEnumerable<string> Tokenize(string text)
    {
        var cleaned = text.Trim().TrimEnd('.');
        foreach (Match match in Regex.Matches(cleaned, "'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|\\S+"))
        {
            yield return match.Value;
        }
    }

    private static string? TokenAfter(IReadOnlyList<string> tokens, string keyword)
    {
        for (var i = 0; i < tokens.Count - 1; i++)
        {
            if (tokens[i].Equals(keyword, StringComparison.OrdinalIgnoreCase))
            {
                return tokens[i + 1];
            }
        }

        return null;
    }

    private static string? ExtractClause(IReadOnlyList<string> tokens, params string[] keywords)
    {
        var start = -1;
        for (var i = 0; i < tokens.Count; i++)
        {
            if (keywords.Any(k => tokens[i].Equals(k, StringComparison.OrdinalIgnoreCase)))
            {
                start = i + 1;
                break;
            }
        }

        if (start < 0 || start >= tokens.Count)
        {
            return null;
        }

        var values = new List<string>();
        for (var i = start; i < tokens.Count; i++)
        {
            if (values.Count > 0 && ClauseKeywords.Contains(tokens[i]))
            {
                break;
            }

            if ((tokens[i].Equals("IS", StringComparison.OrdinalIgnoreCase) || tokens[i].Equals("ARE", StringComparison.OrdinalIgnoreCase)) && values.Count == 0)
            {
                continue;
            }

            values.Add(tokens[i]);
        }

        return values.Count == 0 ? null : string.Join(' ', values);
    }

    private static string? ExtractUsage(IReadOnlyList<string> tokens)
    {
        var explicitUsage = ExtractClause(tokens, "USAGE");
        if (!string.IsNullOrWhiteSpace(explicitUsage))
        {
            return explicitUsage;
        }

        return tokens.Skip(2).FirstOrDefault(UsageKeywords.Contains);
    }

    private static List<string> ExtractIndexedBy(IReadOnlyList<string> tokens)
    {
        var result = new List<string>();
        var indexed = Array.FindIndex(tokens.ToArray(), t => t.Equals("INDEXED", StringComparison.OrdinalIgnoreCase));
        if (indexed < 0)
        {
            return result;
        }

        var start = indexed + 1;
        if (start < tokens.Count && tokens[start].Equals("BY", StringComparison.OrdinalIgnoreCase))
        {
            start++;
        }

        for (var i = start; i < tokens.Count && !ClauseKeywords.Contains(tokens[i]); i++)
        {
            result.Add(tokens[i]);
        }

        return result;
    }

    private static (string? Raw, int? Min, int? Max, string? DependsOn) ExtractOccurs(IReadOnlyList<string> tokens)
    {
        var index = Array.FindIndex(tokens.ToArray(), t => t.Equals("OCCURS", StringComparison.OrdinalIgnoreCase));
        if (index < 0 || index + 1 >= tokens.Count)
        {
            return (null, null, null, null);
        }

        var raw = new List<string>();
        for (var i = index + 1; i < tokens.Count; i++)
        {
            if (raw.Count > 0 && new[] { "PIC", "PICTURE", "VALUE", "VALUES", "REDEFINES", "USAGE" }.Contains(tokens[i], StringComparer.OrdinalIgnoreCase))
            {
                break;
            }

            raw.Add(tokens[i]);
        }

        int.TryParse(tokens[index + 1], out var min);
        int? max = min == 0 ? null : min;
        if (index + 3 < tokens.Count && tokens[index + 2].Equals("TO", StringComparison.OrdinalIgnoreCase) && int.TryParse(tokens[index + 3], out var parsedMax))
        {
            max = parsedMax;
        }

        string? dependsOn = null;
        for (var i = index + 1; i < tokens.Count - 2; i++)
        {
            if (tokens[i].Equals("DEPENDING", StringComparison.OrdinalIgnoreCase) && tokens[i + 1].Equals("ON", StringComparison.OrdinalIgnoreCase))
            {
                dependsOn = tokens[i + 2];
                break;
            }
        }

        return (string.Join(' ', raw), min == 0 ? null : min, max, dependsOn);
    }
}

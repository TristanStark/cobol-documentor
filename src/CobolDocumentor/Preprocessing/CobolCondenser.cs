using System.Text.RegularExpressions;

namespace CobolDocumentor.Preprocessing;

/// <summary>Converts fixed-format COBOL lines into normalized logical statements.</summary>
public static class CobolCondenser
{
    private static readonly HashSet<string> CobolVerbs = new(StringComparer.OrdinalIgnoreCase)
    {
        "ACCEPT", "ADD", "CALL", "CANCEL", "CLOSE", "COMPUTE", "CONTINUE", "DELETE", "DISPLAY", "DIVIDE", "EVALUATE", "EXIT",
        "GO", "GOBACK", "IF", "INITIALIZE", "INSPECT", "MOVE", "MULTIPLY", "OPEN", "PERFORM", "READ", "REWRITE", "SEARCH",
        "SET", "SORT", "START", "STOP", "STRING", "SUBTRACT", "UNSTRING", "WRITE", "EXEC"
    };

    private static readonly HashSet<string> BlockEnders = new(StringComparer.OrdinalIgnoreCase)
    {
        "END-IF", "END-PERFORM", "END-EVALUATE", "END-READ", "END-WRITE", "END-REWRITE", "END-SEARCH", "END-START", "END-STRING", "END-UNSTRING", "END-CALL", "END-COMPUTE"
    };

    /// <summary>Condenses a COBOL file already loaded as physical lines.</summary>
    public static IReadOnlyList<string> CondenseLines(IEnumerable<string> lines)
    {
        var statements = JoinMultilineStatements(lines);
        var output = new List<string>();
        foreach (var statement in statements)
        {
            output.AddRange(ExpandSimpleMultiTargetStatements(statement));
        }

        return output;
    }

    /// <summary>Condenses a COBOL source text.</summary>
    public static IReadOnlyList<string> CondenseText(string text) => CondenseLines(text.Split(Environment.NewLine));

    /// <summary>Returns true for fixed-format comment/debug lines.</summary>
    public static bool IsCommentLine(string line) => line.Length >= 7 && (line[6] == '*' || line[6] == '/' || line[6] == 'D');

    /// <summary>Removes COBOL fixed-format sequence area.</summary>
    public static string StripSequenceArea(string line)
    {
        var trimmed = line.TrimEnd('\r', '\n');
        return trimmed.Length >= 7 ? trimmed[6..] : trimmed;
    }

    private static List<string> JoinMultilineStatements(IEnumerable<string> lines)
    {
        var statements = new List<string>();
        var current = string.Empty;

        foreach (var raw in lines)
        {
            if (IsCommentLine(raw))
            {
                continue;
            }

            var line = StripSequenceArea(raw);
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            var normalized = CollapseInternalSpaces(line);
            if (IsLabelOrHeader(normalized) || IsBlockEnder(normalized) || IsMidBlockLine(normalized))
            {
                FlushCurrent(statements, ref current);
                statements.Add(normalized);
                continue;
            }

            if (IsNewStatement(normalized))
            {
                FlushCurrent(statements, ref current);
                current = normalized.TrimEnd();
            }
            else
            {
                current = string.IsNullOrWhiteSpace(current)
                    ? normalized.TrimEnd()
                    : current.TrimEnd() + " " + normalized.TrimStart();
            }

            if (current.TrimEnd().EndsWith('.', StringComparison.Ordinal))
            {
                FlushCurrent(statements, ref current);
            }
        }

        FlushCurrent(statements, ref current);
        return statements;
    }

    private static void FlushCurrent(ICollection<string> statements, ref string current)
    {
        if (!string.IsNullOrWhiteSpace(current))
        {
            statements.Add(CollapseInternalSpaces(current));
            current = string.Empty;
        }
    }

    private static string CollapseInternalSpaces(string text)
    {
        var leading = Regex.Match(text, "^\\s*").Value;
        var body = text[leading.Length..];
        return leading + Regex.Replace(body, "\\s+", " ").TrimEnd();
    }

    private static bool IsNewStatement(string line)
    {
        var token = FirstToken(line);
        return CobolVerbs.Contains(token) || BlockEnders.Contains(token) || line.TrimStart().StartsWith("EXEC ", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsBlockEnder(string line) => BlockEnders.Contains(FirstToken(line));

    private static bool IsMidBlockLine(string line)
    {
        var upper = line.Trim().ToUpperInvariant();
        return upper is "ELSE" or "AT END" or "NOT AT END" || upper.StartsWith("WHEN ", StringComparison.Ordinal);
    }

    private static bool IsLabelOrHeader(string line)
    {
        var stripped = line.Trim();
        var upper = stripped.ToUpperInvariant();
        if (upper.EndsWith(" DIVISION.", StringComparison.Ordinal) || upper.EndsWith(" SECTION.", StringComparison.Ordinal))
        {
            return true;
        }

        return stripped.EndsWith('.', StringComparison.Ordinal) && !stripped[..^1].Contains(' ') && !CobolVerbs.Contains(stripped.TrimEnd('.'));
    }

    private static string FirstToken(string line)
    {
        var stripped = line.TrimStart();
        return stripped.Length == 0 ? string.Empty : stripped.Split(' ', StringSplitOptions.RemoveEmptyEntries)[0].TrimEnd('.');
    }

    private static IEnumerable<string> ExpandSimpleMultiTargetStatements(string statement)
    {
        foreach (var expanded in ExpandMove(statement))
        {
            foreach (var setExpanded in ExpandSet(expanded))
            {
                yield return setExpanded;
            }
        }
    }

    private static IEnumerable<string> ExpandMove(string statement)
    {
        var match = Regex.Match(statement.TrimStart(), "^MOVE\\s+(.+?)\\s+TO\\s+(.+?)\\.?$", RegexOptions.IgnoreCase);
        if (!match.Success)
        {
            yield return statement;
            yield break;
        }

        var targets = match.Groups[2].Value.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (targets.Length <= 1)
        {
            yield return statement;
            yield break;
        }

        var indent = Regex.Match(statement, "^\\s*").Value;
        for (var i = 0; i < targets.Length; i++)
        {
            var suffix = i == targets.Length - 1 && statement.TrimEnd().EndsWith('.') ? "." : string.Empty;
            yield return $"{indent}MOVE {match.Groups[1].Value.Trim()} TO {targets[i]}{suffix}";
        }
    }

    private static IEnumerable<string> ExpandSet(string statement)
    {
        var match = Regex.Match(statement.TrimStart(), "^SET\\s+(.+?)\\s+TO\\s+(.+?)\\.?$", RegexOptions.IgnoreCase);
        if (!match.Success)
        {
            yield return statement;
            yield break;
        }

        var names = match.Groups[1].Value.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (names.Length <= 1)
        {
            yield return statement;
            yield break;
        }

        var indent = Regex.Match(statement, "^\\s*").Value;
        for (var i = 0; i < names.Length; i++)
        {
            var suffix = i == names.Length - 1 && statement.TrimEnd().EndsWith('.') ? "." : string.Empty;
            yield return $"{indent}SET {names[i]} TO {match.Groups[2].Value.Trim()}{suffix}";
        }
    }
}

using System.Text.RegularExpressions;
using CobolDocumentor.Preprocessing;

namespace CobolDocumentor.Copybooks;

/// <summary>Indexes COBOL copybooks and resolves COPY names to files.</summary>
public sealed class CopyLookup
{
    private static readonly HashSet<string> ValidExtensions = new(StringComparer.OrdinalIgnoreCase) { ".cpy", ".cpm", ".cpx", ".copy" };
    private readonly Dictionary<string, string> _index = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Creates an empty lookup.</summary>
    public CopyLookup()
    {
    }

    /// <summary>Creates and warms a lookup from a root folder.</summary>
    public CopyLookup(string rootFolder) => BuildIndex(rootFolder);

    /// <summary>Current immutable index snapshot.</summary>
    public IReadOnlyDictionary<string, string> Index => _index;

    /// <summary>Builds the lookup index from all supported copybook files below a folder recursively.</summary>
    public void BuildIndex(string rootFolder)
    {
        if (!Directory.Exists(rootFolder))
        {
            throw new DirectoryNotFoundException(rootFolder);
        }

        _index.Clear();
        foreach (var file in Directory.EnumerateFiles(rootFolder, "*.*", SearchOption.AllDirectories))
        {
            if (!ValidExtensions.Contains(Path.GetExtension(file)))
            {
                continue;
            }

            var name = Path.GetFileNameWithoutExtension(file).ToUpperInvariant();
            if (_index.ContainsKey(name))
            {
                throw new InvalidOperationException($"COPY collision for {name}: {_index[name]} and {file}");
            }

            _index[name] = Path.GetFullPath(file);
        }
    }

    /// <summary>Resolves a COPY name to a file path.</summary>
    public string Resolve(string copyName)
    {
        var normalized = copyName.Trim().Trim('"', '\'', '.').ToUpperInvariant();
        if (_index.TryGetValue(normalized, out var path))
        {
            return path;
        }

        throw new FileNotFoundException($"COPY not found: {normalized}");
    }
}

/// <summary>Expands COPY statements using a <see cref="CopyLookup" />.</summary>
public sealed class CopyResolver
{
    private const int MaxCopyDepth = 32;
    private readonly CopyLookup? _lookup;

    /// <summary>Creates a resolver. Without lookup, COPY statements are preserved.</summary>
    public CopyResolver(CopyLookup? lookup = null) => _lookup = lookup;

    /// <summary>Expands COPY statements in a source file while preserving non-COPY lines.</summary>
    public IReadOnlyList<string> ExpandFile(string sourceFile)
    {
        var lines = File.ReadAllLines(sourceFile).Select(line => line + Environment.NewLine).ToArray();
        return ExpandLines(lines);
    }

    /// <summary>Expands COPY statements in physical source lines.</summary>
    public IReadOnlyList<string> ExpandLines(IReadOnlyList<string> lines) => ExpandLines(lines, 0);

    private IReadOnlyList<string> ExpandLines(IReadOnlyList<string> lines, int depth)
    {
        if (depth > MaxCopyDepth)
        {
            throw new InvalidOperationException("Maximum nested COPY expansion depth reached.");
        }

        var output = new List<string>();
        var buffer = new List<string>();
        var inCopy = false;

        foreach (var line in lines)
        {
            var normalized = CobolCondenser.StripSequenceArea(line).TrimStart();
            if (!inCopy && normalized.StartsWith("COPY ", StringComparison.OrdinalIgnoreCase))
            {
                inCopy = true;
                buffer.Add(line);
                if (line.Contains('.'))
                {
                    FlushCopy(output, buffer, depth);
                    inCopy = false;
                }

                continue;
            }

            if (inCopy)
            {
                buffer.Add(line);
                if (line.Contains('.'))
                {
                    FlushCopy(output, buffer, depth);
                    inCopy = false;
                }

                continue;
            }

            output.Add(line);
        }

        if (buffer.Count > 0)
        {
            output.AddRange(buffer);
        }

        return output;
    }

    private void FlushCopy(List<string> output, List<string> buffer, int depth)
    {
        if (_lookup is null)
        {
            output.AddRange(buffer);
            buffer.Clear();
            return;
        }

        var statement = string.Concat(buffer.Where(line => !IsCommentLine(line)).Select(CobolCondenser.StripSequenceArea));
        var parsed = ParseCopyStatement(statement);
        var copyPath = _lookup.Resolve(parsed.CopyName);
        var content = File.ReadAllText(copyPath);
        foreach (var replacement in parsed.Replacements)
        {
            content = replacement.IsPseudoText
                ? content.Replace(replacement.OldValue, replacement.NewValue, StringComparison.Ordinal)
                : Regex.Replace(content, $"(?<![A-Za-z0-9-]){Regex.Escape(replacement.OldValue)}(?![A-Za-z0-9-])", replacement.NewValue);
        }

        var expanded = ExpandLines(content.SplitLines(keepEnds: true).ToArray(), depth + 1);
        output.AddRange(expanded);
        buffer.Clear();
    }

    private static bool IsCommentLine(string line) => line.Length >= 7 && (line[6] == '*' || line[6] == '/' || line[6] == 'D');

    private static ParsedCopy ParseCopyStatement(string statement)
    {
        var tokens = TokenizeCopy(statement).ToArray();
        if (tokens.Length < 2 || !tokens[0].Equals("COPY", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"Invalid COPY statement: {statement}");
        }

        var parsed = new ParsedCopy(tokens[1].Trim('"', '\'', '.'));
        var i = 2;
        if (i < tokens.Length && tokens[i].Equals("REPLACING", StringComparison.OrdinalIgnoreCase))
        {
            i++;
            while (i + 2 < tokens.Length && tokens[i] != ".")
            {
                var oldValue = Decode(tokens[i++], out var oldPseudo);
                if (!tokens[i].Equals("BY", StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidOperationException($"Invalid COPY REPLACING clause: {statement}");
                }

                i++;
                var newValue = Decode(tokens[i++], out _);
                parsed.Replacements.Add(new CopyReplacement(oldValue, newValue, oldPseudo));
            }
        }

        return parsed;
    }

    private static IEnumerable<string> TokenizeCopy(string statement)
    {
        foreach (Match match in Regex.Matches(statement.Trim(), "==.*?==|'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|\\.|\\S+"))
        {
            yield return match.Value;
        }
    }

    private static string Decode(string token, out bool isPseudoText)
    {
        token = token.Trim();
        isPseudoText = token.StartsWith("==", StringComparison.Ordinal) && token.EndsWith("==", StringComparison.Ordinal);
        if (isPseudoText)
        {
            return token[2..^2];
        }

        return token.Trim('"', '\'', '.');
    }

    private sealed record ParsedCopy(string CopyName)
    {
        public List<CopyReplacement> Replacements { get; } = [];
    }

    private sealed record CopyReplacement(string OldValue, string NewValue, bool IsPseudoText);
}

internal static class StringSplitExtensions
{
    public static IEnumerable<string> SplitLines(this string text, bool keepEnds)
    {
        using var reader = new StringReader(text);
        string? line;
        while ((line = reader.ReadLine()) is not null)
        {
            yield return keepEnds ? line + Environment.NewLine : line;
        }
    }
}

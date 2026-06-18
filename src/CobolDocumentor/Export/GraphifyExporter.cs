using System.Text.Json;
using System.Text.RegularExpressions;
using CobolDocumentor.Model;

namespace CobolDocumentor.Export;

/// <summary>Exports parsed COBOL programs to Graphify's simple nodes/edges shape.</summary>
public static class GraphifyExporter
{
    /// <summary>Builds a graph from a parsed COBOL program.</summary>
    public static GraphifyGraph Export(CobolProgramModel program)
    {
        var graph = new GraphifyGraph();
        var seenNodes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var seenEdges = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var programId = Id("program", program.Name);

        AddNode(graph, seenNodes, programId, program.Name, "program", new Dictionary<string, object?> { ["source_file"] = program.SourceFile });

        foreach (var variable in program.MemoryStack.Variables)
        {
            var variableId = ExportVariable(graph, seenNodes, seenEdges, variable);
            AddEdge(graph, seenEdges, programId, variableId, "declares");
        }

        for (var i = 0; i < program.Paragraphs.Count; i++)
        {
            var paragraph = program.Paragraphs[i];
            var paragraphId = Id("paragraph", $"{program.Name}:{paragraph.Name}:{i}");
            AddNode(graph, seenNodes, paragraphId, paragraph.Name, "paragraph", new Dictionary<string, object?> { ["source_file"] = program.SourceFile });
            AddEdge(graph, seenEdges, programId, paragraphId, "contains");

            for (var j = 0; j < paragraph.Statements.Count; j++)
            {
                ExportStatement(graph, seenNodes, seenEdges, paragraphId, paragraph.Statements[j], j, program.MemoryStack.KnownVariables);
            }
        }

        return graph;
    }

    /// <summary>Writes a graph export to a JSON file.</summary>
    public static void Write(CobolProgramModel program, string outputPath)
    {
        var graph = Export(program);
        var directory = Path.GetDirectoryName(outputPath);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        File.WriteAllText(outputPath, JsonSerializer.Serialize(graph, new JsonSerializerOptions { WriteIndented = true }));
    }

    private static string ExportVariable(GraphifyGraph graph, HashSet<string> seenNodes, HashSet<string> seenEdges, CobolVariable variable)
    {
        var variableId = Id("variable", variable.Name);
        AddNode(graph, seenNodes, variableId, variable.Name, "variable", new Dictionary<string, object?>
        {
            ["level"] = variable.Level,
            ["pic"] = variable.Picture,
            ["usage"] = variable.Usage,
            ["value"] = variable.Value,
            ["redefines"] = variable.Redefines,
            ["occurs"] = variable.Occurs,
            ["occurs_min"] = variable.OccursMin,
            ["occurs_max"] = variable.OccursMax,
            ["depends_on"] = variable.DependsOn,
            ["is_group"] = variable.IsGroup
        });

        if (!string.IsNullOrWhiteSpace(variable.Redefines))
        {
            var targetId = Id("variable", variable.Redefines);
            AddNode(graph, seenNodes, targetId, variable.Redefines, "variable", new Dictionary<string, object?> { ["inferred"] = true });
            AddEdge(graph, seenEdges, variableId, targetId, "redefines");
        }

        if (!string.IsNullOrWhiteSpace(variable.DependsOn))
        {
            var targetId = Id("variable", variable.DependsOn);
            AddNode(graph, seenNodes, targetId, variable.DependsOn, "variable", new Dictionary<string, object?> { ["inferred"] = true });
            AddEdge(graph, seenEdges, variableId, targetId, "occurs_depends_on");
        }

        foreach (var condition in variable.Conditions)
        {
            var conditionId = ExportVariable(graph, seenNodes, seenEdges, condition);
            AddEdge(graph, seenEdges, variableId, conditionId, "defines_condition");
        }

        foreach (var child in variable.Children)
        {
            var childId = ExportVariable(graph, seenNodes, seenEdges, child);
            AddEdge(graph, seenEdges, variableId, childId, "contains");
        }

        return variableId;
    }

    private static void ExportStatement(GraphifyGraph graph, HashSet<string> seenNodes, HashSet<string> seenEdges, string parentId, CobolStatement statement, int index, IReadOnlySet<string> knownVariables)
    {
        var statementId = Id("statement", $"{parentId}:{index}:{statement.RawText}");
        AddNode(graph, seenNodes, statementId, Short(statement.RawText), "statement", new Dictionary<string, object?> { ["statement_type"] = statement.Kind.ToString().ToLowerInvariant() });
        AddEdge(graph, seenEdges, parentId, statementId, "contains");
        AddSemanticEdges(graph, seenNodes, seenEdges, statementId, statement);

        foreach (var variableName in ReferencedVariables(statement.RawText, knownVariables))
        {
            var variableId = Id("variable", variableName);
            AddNode(graph, seenNodes, variableId, variableName, "variable", new Dictionary<string, object?> { ["inferred"] = true });
            AddEdge(graph, seenEdges, statementId, variableId, "references");
        }

        for (var i = 0; i < statement.Children.Count; i++)
        {
            ExportStatement(graph, seenNodes, seenEdges, statementId, statement.Children[i], i, knownVariables);
        }

        for (var i = 0; i < statement.ElseChildren.Count; i++)
        {
            ExportStatement(graph, seenNodes, seenEdges, statementId, statement.ElseChildren[i], i, knownVariables);
        }
    }

    private static void AddSemanticEdges(GraphifyGraph graph, HashSet<string> seenNodes, HashSet<string> seenEdges, string statementId, CobolStatement statement)
    {
        var raw = statement.RawText.Trim();
        var upper = raw.ToUpperInvariant();
        if (upper.StartsWith("CALL ", StringComparison.Ordinal))
        {
            var tokens = SplitTokens(raw);
            var target = statement.IsZCallPgm && tokens.Count >= 4 ? tokens[3] : tokens.ElementAtOrDefault(1);
            if (!string.IsNullOrWhiteSpace(target))
            {
                var programId = Id("program", CleanToken(target));
                AddNode(graph, seenNodes, programId, CleanToken(target), "program", new Dictionary<string, object?> { ["inferred"] = true });
                AddEdge(graph, seenEdges, statementId, programId, "calls");
            }

            if (statement.IsZCallPgm)
            {
                foreach (var copyArgument in tokens.Skip(4))
                {
                    var copyId = Id("copy", CleanToken(copyArgument));
                    AddNode(graph, seenNodes, copyId, CleanToken(copyArgument), "copy", new Dictionary<string, object?> { ["inferred"] = true });
                    AddEdge(graph, seenEdges, statementId, copyId, "uses_copy_argument");
                }
            }
        }
        else if (upper.StartsWith("PERFORM ", StringComparison.Ordinal))
        {
            foreach (var target in PerformTargets(raw))
            {
                var paragraphId = Id("paragraph", target);
                AddNode(graph, seenNodes, paragraphId, target, "paragraph", new Dictionary<string, object?> { ["inferred"] = true });
                AddEdge(graph, seenEdges, statementId, paragraphId, "performs");
            }
        }
        else if (upper.StartsWith("READ ", StringComparison.Ordinal))
        {
            AddFileEdge(graph, seenNodes, seenEdges, statementId, raw, "reads_from");
        }
        else if (upper.StartsWith("WRITE ", StringComparison.Ordinal) || upper.StartsWith("REWRITE ", StringComparison.Ordinal))
        {
            AddFileEdge(graph, seenNodes, seenEdges, statementId, raw, "writes_to");
        }
    }

    private static void AddFileEdge(GraphifyGraph graph, HashSet<string> seenNodes, HashSet<string> seenEdges, string statementId, string raw, string relation)
    {
        var target = SplitTokens(raw).ElementAtOrDefault(1);
        if (string.IsNullOrWhiteSpace(target))
        {
            return;
        }

        var fileId = Id("file", target);
        AddNode(graph, seenNodes, fileId, target, "file", new Dictionary<string, object?> { ["inferred"] = true });
        AddEdge(graph, seenEdges, statementId, fileId, relation);
    }

    private static IEnumerable<string> PerformTargets(string raw)
    {
        var tokens = SplitTokens(raw).ToArray();
        if (tokens.Length < 2 || new[] { "UNTIL", "VARYING", "TIMES" }.Contains(tokens[1], StringComparer.OrdinalIgnoreCase))
        {
            yield break;
        }

        yield return CleanToken(tokens[1]);
        for (var i = 2; i < tokens.Length - 1; i++)
        {
            if (tokens[i].Equals("THRU", StringComparison.OrdinalIgnoreCase) || tokens[i].Equals("THROUGH", StringComparison.OrdinalIgnoreCase))
            {
                yield return CleanToken(tokens[i + 1]);
            }
        }
    }

    private static IEnumerable<string> ReferencedVariables(string raw, IReadOnlySet<string> knownVariables)
    {
        foreach (var variableName in knownVariables.OrderByDescending(v => v.Length))
        {
            if (Regex.IsMatch(raw, $"(?<![A-Z0-9-]){Regex.Escape(variableName)}(?![A-Z0-9-])", RegexOptions.IgnoreCase))
            {
                yield return variableName;
            }
        }
    }

    private static void AddNode(GraphifyGraph graph, HashSet<string> seenNodes, string id, string label, string type, Dictionary<string, object?> attributes)
    {
        if (!seenNodes.Add(id))
        {
            return;
        }

        var node = new Dictionary<string, object?> { ["id"] = id, ["label"] = label, ["type"] = type };
        foreach (var pair in attributes.Where(pair => pair.Value is not null))
        {
            node[pair.Key] = pair.Value;
        }

        graph.Nodes.Add(node);
    }

    private static void AddEdge(GraphifyGraph graph, HashSet<string> seenEdges, string source, string target, string relation)
    {
        var key = $"{source}|{target}|{relation}";
        if (seenEdges.Add(key))
        {
            graph.Edges.Add(new Dictionary<string, object?> { ["source"] = source, ["target"] = target, ["relation"] = relation });
        }
    }

    private static string Id(string kind, string label)
    {
        var value = Regex.Replace(CleanToken(label).ToLowerInvariant(), "[^a-z0-9_-]+", "-").Trim('-');
        return $"{kind}:{(string.IsNullOrWhiteSpace(value) ? "unknown" : value)}";
    }

    private static string CleanToken(string value) => value.Trim().TrimEnd('.').Trim('"', '\'');

    private static string Short(string value) => value.Length <= 120 ? value : value[..119] + "…";

    private static IReadOnlyList<string> SplitTokens(string raw) => raw.Trim().TrimEnd('.').Split(' ', StringSplitOptions.RemoveEmptyEntries);
}

/// <summary>Graphify-compatible graph data transfer object.</summary>
public sealed class GraphifyGraph
{
    /// <summary>Graph nodes.</summary>
    public List<Dictionary<string, object?>> Nodes { get; } = [];

    /// <summary>Graph edges.</summary>
    public List<Dictionary<string, object?>> Edges { get; } = [];
}

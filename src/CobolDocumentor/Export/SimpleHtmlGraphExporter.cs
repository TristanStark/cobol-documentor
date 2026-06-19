using System.Globalization;
using System.Net;
using System.Text;
using CobolDocumentor.Model;

namespace CobolDocumentor.Export;

/// <summary>Writes a lightweight standalone HTML graph without depending on Graphify.</summary>
public static class SimpleHtmlGraphExporter
{
    /// <summary>Exports a parsed COBOL program as a static HTML/SVG graph.</summary>
    public static void Write(CobolProgramModel program, string outputPath)
    {
        Write(GraphifyExporter.Export(program), outputPath, program.Name);
    }

    /// <summary>Exports an existing graph as a static HTML/SVG graph.</summary>
    public static void Write(GraphifyGraph graph, string outputPath, string title = "COBOL graph")
    {
        var directory = Path.GetDirectoryName(outputPath);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        File.WriteAllText(outputPath, Render(graph, title));
    }

    /// <summary>Renders a complete standalone HTML document containing an SVG graph.</summary>
    public static string Render(GraphifyGraph graph, string title = "COBOL graph")
    {
        var nodes = graph.Nodes.Select((node, index) => new PositionedNode(node, index)).ToList();
        var byId = nodes.ToDictionary(node => node.Id, StringComparer.OrdinalIgnoreCase);
        PositionNodes(nodes);

        var html = new StringBuilder();
        html.AppendLine("<!doctype html>");
        html.AppendLine("<html lang=\"en\"><head><meta charset=\"utf-8\">");
        html.AppendLine($"<title>{Escape(title)}</title>");
        html.AppendLine("<style>body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#111827;color:#e5e7eb}header{padding:14px 18px;background:#020617;border-bottom:1px solid #334155}svg{display:block;width:100vw;height:calc(100vh - 54px);background:#0f172a}.edge{stroke:#64748b;stroke-width:1.2}.edge-label{fill:#94a3b8;font-size:10px}.node-label{fill:#e5e7eb;font-size:12px}.node{stroke:#bfdbfe;stroke-width:1.5}.program{fill:#7c3aed}.paragraph{fill:#0891b2}.variable{fill:#16a34a}.statement{fill:#ea580c}.copy{fill:#be123c}.file{fill:#ca8a04}.unknown{fill:#2563eb}</style>");
        html.AppendLine("</head><body>");
        html.AppendLine($"<header><strong>{Escape(title)}</strong> — {nodes.Count} nodes, {graph.Edges.Count} edges</header>");
        html.AppendLine("<svg viewBox=\"0 0 1200 800\" role=\"img\" aria-label=\"COBOL dependency graph\">");

        foreach (var edge in graph.Edges)
        {
            var source = Value(edge, "source");
            var target = Value(edge, "target");
            if (!byId.TryGetValue(source, out var sourceNode) || !byId.TryGetValue(target, out var targetNode))
            {
                continue;
            }

            var relation = Value(edge, "relation");
            html.AppendLine($"<line class=\"edge\" x1=\"{N(sourceNode.X)}\" y1=\"{N(sourceNode.Y)}\" x2=\"{N(targetNode.X)}\" y2=\"{N(targetNode.Y)}\"><title>{Escape(relation)}</title></line>");
            html.AppendLine($"<text class=\"edge-label\" x=\"{N((sourceNode.X + targetNode.X) / 2)}\" y=\"{N((sourceNode.Y + targetNode.Y) / 2)}\">{Escape(relation)}</text>");
        }

        foreach (var node in nodes)
        {
            html.AppendLine($"<circle class=\"node {EscapeCss(node.Type)}\" cx=\"{N(node.X)}\" cy=\"{N(node.Y)}\" r=\"18\"><title>{Escape(node.Id)}</title></circle>");
            html.AppendLine($"<text class=\"node-label\" x=\"{N(node.X + 24)}\" y=\"{N(node.Y + 4)}\">{Escape(node.Label)}</text>");
        }

        html.AppendLine("</svg></body></html>");
        return html.ToString();
    }

    private static void PositionNodes(IReadOnlyList<PositionedNode> nodes)
    {
        const double centerX = 600;
        const double centerY = 390;
        const double radius = 310;
        var count = Math.Max(1, nodes.Count);
        for (var i = 0; i < nodes.Count; i++)
        {
            var angle = Math.PI * 2 * i / count;
            nodes[i].X = centerX + Math.Cos(angle) * radius;
            nodes[i].Y = centerY + Math.Sin(angle) * radius;
        }
    }

    private static string Value(IReadOnlyDictionary<string, object?> map, string key)
    {
        return map.TryGetValue(key, out var value) ? Convert.ToString(value, CultureInfo.InvariantCulture) ?? string.Empty : string.Empty;
    }

    private static string Escape(string value) => WebUtility.HtmlEncode(value);

    private static string EscapeCss(string value) => string.IsNullOrWhiteSpace(value) ? "unknown" : Escape(value.ToLowerInvariant());

    private static string N(double value) => value.ToString("0.###", CultureInfo.InvariantCulture);

    private sealed class PositionedNode
    {
        public PositionedNode(IReadOnlyDictionary<string, object?> source, int index)
        {
            Id = Value(source, "id");
            Label = Value(source, "label");
            Type = Value(source, "type");
            Index = index;
        }

        public string Id { get; }

        public string Label { get; }

        public string Type { get; }

        public int Index { get; }

        public double X { get; set; }

        public double Y { get; set; }
    }
}

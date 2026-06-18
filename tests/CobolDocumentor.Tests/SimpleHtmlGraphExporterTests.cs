using CobolDocumentor.Export;
using CobolDocumentor.Model;
using CobolDocumentor.Parsing;
using Xunit;

namespace CobolDocumentor.Tests;

public sealed class SimpleHtmlGraphExporterTests
{
    [Fact]
    public void RenderProducesStandaloneSvgHtml()
    {
        var program = new CobolProgramModel("SAMPLE", "sample.cbl")
        {
            MemoryStack = CobolMemoryStack.FromDeclarations(
            [
                "01 CUSTOMER-AREA.",
                " 05 WS-COUNT PIC 9(02).",
                " 05 WS-ALT REDEFINES WS-COUNT PIC X(02)."
            ])
        };

        var paragraph = new CobolParagraph("0000-MAIN.");
        paragraph.Statements.Add(CobolProgramLoader.ParseStatement("MOVE WS-ALT TO WS-COUNT."));
        program.Paragraphs.Add(paragraph);

        var html = SimpleHtmlGraphExporter.Render(GraphifyExporter.Export(program), "SAMPLE");

        Assert.Contains("<svg", html);
        Assert.Contains("variable:ws-alt", html);
        Assert.Contains("redefines", html);
        Assert.Contains("references", html);
    }
}

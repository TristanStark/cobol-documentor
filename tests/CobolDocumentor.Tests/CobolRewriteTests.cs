using CobolDocumentor.Export;
using CobolDocumentor.Model;
using CobolDocumentor.Parsing;
using CobolDocumentor.Preprocessing;
using Xunit;

namespace CobolDocumentor.Tests;

public sealed class CobolRewriteTests
{
    [Fact]
    public void VariableParserHandlesRedefinesAndOccurs()
    {
        var redefined = CobolVariable.Parse("05 WS-ALT REDEFINES WS-BASE PIC X(10).")!;
        Assert.Equal("WS-ALT", redefined.Name);
        Assert.Equal("WS-BASE", redefined.Redefines);
        Assert.Equal("X(10)", redefined.Picture);
        Assert.False(redefined.IsGroup);

        var occurs = CobolVariable.Parse("05 WS-ITEM OCCURS 1 TO 10 TIMES DEPENDING ON WS-COUNT PIC X(05).")!;
        Assert.Equal("WS-ITEM", occurs.Name);
        Assert.Equal("X(05)", occurs.Picture);
        Assert.Equal("1 TO 10 TIMES DEPENDING ON WS-COUNT", occurs.Occurs);
        Assert.Equal(1, occurs.OccursMin);
        Assert.Equal(10, occurs.OccursMax);
        Assert.Equal("WS-COUNT", occurs.DependsOn);
    }

    [Fact]
    public void MemoryStackKeepsNestedOccursAndRedefines()
    {
        var memory = CobolMemoryStack.FromDeclarations(
        [
            "01 CUSTOMER-AREA.",
            " 05 WS-COUNT PIC 9(02).",
            " 05 WS-BASE PIC X(10).",
            " 05 WS-ALT REDEFINES WS-BASE PIC X(10).",
            " 05 WS-ITEMS OCCURS 1 TO 10 TIMES DEPENDING ON WS-COUNT.",
            "  10 WS-ITEM-CODE PIC X(03).",
            "  10 WS-ITEM-AMOUNT PIC S9(7)V99 COMP-3."
        ]);

        Assert.True(memory.Contains("CUSTOMER-AREA"));
        Assert.True(memory.Contains("WS-ALT"));
        Assert.True(memory.Contains("WS-ITEM-CODE"));

        var root = memory.Variables.Single();
        var children = root.Children.ToDictionary(v => v.Name);
        Assert.Equal("WS-BASE", children["WS-ALT"].Redefines);
        Assert.True(children["WS-ITEMS"].IsGroup);
        Assert.Equal(1, children["WS-ITEMS"].OccursMin);
        Assert.Equal(10, children["WS-ITEMS"].OccursMax);
        Assert.Equal("WS-COUNT", children["WS-ITEMS"].DependsOn);
        Assert.Equal("COMP-3", children["WS-ITEMS"].Children[1].Usage);
    }

    [Fact]
    public void CondenserExpandsMultiTargetMoveAndSet()
    {
        var result = CobolCondenser.CondenseText(string.Join(Environment.NewLine,
        [
            "       PROCEDURE DIVISION.",
            "       MAIN.",
            "           MOVE A TO B C.",
            "           SET FLAG1 FLAG2 TO TRUE."
        ]));

        Assert.Contains("     MOVE A TO B", result);
        Assert.Contains("     MOVE A TO C.", result);
        Assert.Contains("     SET FLAG1 TO TRUE", result);
        Assert.Contains("     SET FLAG2 TO TRUE.", result);
    }

    [Fact]
    public void GraphifyExportContainsCobolEdges()
    {
        var program = new CobolProgramModel("SAMPLE", "sample.cbl")
        {
            MemoryStack = CobolMemoryStack.FromDeclarations(
            [
                "01 CUSTOMER-AREA.",
                " 05 WS-COUNT PIC 9(02).",
                " 05 WS-BASE PIC X(10).",
                " 05 WS-ALT REDEFINES WS-BASE PIC X(10).",
                " 05 WS-ITEMS OCCURS 1 TO 10 TIMES DEPENDING ON WS-COUNT.",
                "  10 WS-ITEM-CODE PIC X(03)."
            ])
        };

        var paragraph = new CobolParagraph("0000-MAIN.");
        paragraph.Statements.Add(CobolProgramLoader.ParseStatement("PERFORM 1000-INIT THRU 1999-END."));
        paragraph.Statements.Add(CobolProgramLoader.ParseStatement("CALL 'ZCALLPGM' USING TARGET-PGM CPY-REQUEST."));
        paragraph.Statements.Add(CobolProgramLoader.ParseStatement("MOVE WS-ALT TO WS-COUNT."));
        program.Paragraphs.Add(paragraph);

        var graph = GraphifyExporter.Export(program);
        var edges = graph.Edges.Select(e => (Source: e["source"]?.ToString(), Target: e["target"]?.ToString(), Relation: e["relation"]?.ToString())).ToHashSet();

        Assert.Contains(edges, e => e.Source == "variable:ws-alt" && e.Target == "variable:ws-base" && e.Relation == "redefines");
        Assert.Contains(edges, e => e.Source == "variable:ws-items" && e.Target == "variable:ws-count" && e.Relation == "occurs_depends_on");
        Assert.Contains(edges, e => e.Target == "program:target-pgm" && e.Relation == "calls");
        Assert.Contains(edges, e => e.Target == "paragraph:1000-init" && e.Relation == "performs");
        Assert.Contains(edges, e => e.Target == "paragraph:1999-end" && e.Relation == "performs");
        Assert.Contains(edges, e => e.Target == "variable:ws-alt" && e.Relation == "references");
    }
}

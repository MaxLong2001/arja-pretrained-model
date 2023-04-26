package clm.incoder;

import clm.jasper.ContextParser;
import clm.jasper.Parser;
import com.github.javaparser.Range;
import com.github.javaparser.ast.Node;
import org.eclipse.jdt.core.ToolFactory;
import org.eclipse.jdt.core.formatter.CodeFormatter;
import org.eclipse.jface.text.Document;
import org.eclipse.jface.text.IDocument;
import org.eclipse.text.edits.TextEdit;

public class InCoderInputParser {
    public static InCoderInput getInCoderInput(String filename, int startLine, int endLine, InCoderConfig config) {
        try {
            Node buggyFunctionNode = ContextParser.getSurroundingFunctionNode(filename, startLine, endLine, true);
            Range range = buggyFunctionNode.getRange().get();
            String functionRange = range.begin.line + "," + range.begin.column + "-" + range.end.line + "," + range.end.column;
            String input;

            String buggyFunctionBefore = ContextParser.getSurroundingFunctionBefore(filename, startLine, endLine, true);
            String buggyFunctionAfter = ContextParser.getSurroundingFunctionAfter(filename, startLine, endLine, true);
            String buggyLine = ContextParser.getDedentedCode(filename, startLine, endLine, true);
            int buggyLineIndent = Parser.getIndent(filename, startLine);
            int buggyFunctionIndent = Parser.getIndent(buggyFunctionNode);

            String completeFunction = buggyFunctionBefore + buggyLine + buggyFunctionAfter;
            CodeFormatter codeFormatter = ToolFactory.createCodeFormatter(null);
            TextEdit textEdit = codeFormatter.format(
                    CodeFormatter.K_CLASS_BODY_DECLARATIONS,
                    completeFunction,
                    0,
                    completeFunction.length(),
                    buggyFunctionIndent,
                    null);
            IDocument doc = new Document(completeFunction);
            try {
                textEdit.apply(doc);
            } catch (Exception e) {
                e.printStackTrace();
            }
            String formattedFunction = doc.get();
            String[] lines = formattedFunction.split("\n");
            buggyFunctionBefore = "";
            buggyFunctionAfter = "";
            int buggyLineIndex = -1;
            for (int i = 0; i < lines.length; i += 1) {
                if (lines[i].contains(buggyLine.trim())) {
                    buggyLineIndex = i;
                    buggyLine = lines[i];
                    break;
                }
            }
            for (int i = 0; i < buggyLineIndex; i += 1)
                buggyFunctionBefore += lines[i] + "\n";
            for (int i = buggyLineIndex + 1; i < lines.length; i += 1)
                buggyFunctionAfter += lines[i] + "\n";

            input = buggyFunctionBefore + "\n";
            if (config == InCoderConfig.MASK_ON) {
                for (int i = 0; i < buggyLineIndent - buggyFunctionIndent; i += 1)
                    input += " ";
                input += "<|mask:0|>\n";
            } else if (config == InCoderConfig.MASK_BEFORE) {
                for (int i = 0; i < buggyLineIndent - buggyFunctionIndent; i += 1)
                    input += " ";
                input += "<|mask:0|>\n";
                input += buggyLine;
            } else if (config == InCoderConfig.MASK_AFTER) {
                input += buggyLine;
                for (int i = 0; i < buggyLineIndent - buggyFunctionIndent; i += 1)
                    input += " ";
                input += "<|mask:0|>\n";
            }
            input += buggyFunctionAfter;

            input = Parser.removeEmptyLines(input) + "\n<|mask:0|>";
            return new InCoderInput(input, functionRange);
        } catch (Exception e) {
            e.printStackTrace();
            return new InCoderInput("", "");
        }
    }

    public static void dumpInCoderInput(String filename, int startLine, int endLine, InCoderConfig config, String outputFileName) throws Exception {
        InCoderInput incoderInput = getInCoderInput(filename, startLine, endLine, config);
        incoderInput.dumpAsJson(outputFileName);
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 5) {
            String filename = args[0];
            int startLine = Integer.parseInt(args[1]);
            int endLine = Integer.parseInt(args[2]);
            InCoderConfig config;
            switch (args[3]) {
                case "MASK_ON":
                    config = InCoderConfig.MASK_ON;
                    break;
                case "MASK_BEFORE":
                    config = InCoderConfig.MASK_BEFORE;
                    break;
                case "MASK_AFTER":
                    config = InCoderConfig.MASK_AFTER;
                    break;
                default:
                    throw new Exception("Unrecognized InCoderConfig: " + args[3]);
            }
            String outputFileName = args[4];
            dumpInCoderInput(filename, startLine, endLine, config, outputFileName);
        } else {
            throw new Exception("Arguments number mismatched, expected 5, but got " + args.length);
        }
    }
}

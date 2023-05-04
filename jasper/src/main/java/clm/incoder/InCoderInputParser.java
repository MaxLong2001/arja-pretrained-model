package clm.incoder;

import clm.jasper.ContextParser;
import clm.jasper.Parser;
import com.github.javaparser.Range;
import com.github.javaparser.ast.Node;

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

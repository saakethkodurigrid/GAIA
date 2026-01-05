import { useRef, useEffect, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { java } from '@codemirror/lang-java';
import { EditorView } from '@codemirror/view';
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { tags as t } from '@lezer/highlight';
import { useCoding } from '../../context/CodingContext';

const CodeEditor = () => {
  const { currentProblem, selectedLanguage, code, updateCode } = useCoding();
  const editorRef = useRef<HTMLDivElement>(null);
  const [editorHeight, setEditorHeight] = useState('600px');

  useEffect(() => {
    const updateHeight = () => {
      if (editorRef.current) {
        const height = editorRef.current.clientHeight;
        if (height > 0) {
          setEditorHeight(`${height}px`);
        }
      }
    };

    updateHeight();
    const resizeObserver = new ResizeObserver(updateHeight);
    if (editorRef.current) {
      resizeObserver.observe(editorRef.current);
    }

    window.addEventListener('resize', updateHeight);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateHeight);
    };
  }, []);

  if (!currentProblem) return null;

  const codeKey = `${currentProblem.question_uuid}-${selectedLanguage}`;
  const currentCode = code[codeKey] || currentProblem.boilerplate[selectedLanguage];

  const getLanguageExtension = () => {
    switch (selectedLanguage) {
      case 'python':
        return python();
      case 'javascript':
        return javascript();
      case 'java':
        return java();
      default:
        return python();
    }
  };

  // Syntax highlighting colors for different token types
  const highlightStyle = HighlightStyle.define([
    { tag: t.keyword, color: '#0066cc', fontWeight: 'bold' },
    { tag: t.string, color: '#008800' },
    { tag: [t.number, t.literal], color: '#0066cc' },
    { tag: [t.comment, t.lineComment, t.blockComment], color: '#888888', fontStyle: 'italic' },
    { tag: [t.className, t.typeName], color: '#0066cc' },
    { tag: [t.variableName, t.propertyName], color: '#333333' },
    { tag: [t.operator, t.punctuation], color: '#333333' },
    { tag: t.tagName, color: '#0066cc' },
    { tag: t.attributeName, color: '#0066cc' },
    { tag: t.bracket, color: '#333333' },
    { tag: t.meta, color: '#666666' },
  ]);

  // Create syntax highlighting extension
  const syntaxHighlightingExtension = syntaxHighlighting(highlightStyle);

  // Custom light theme with editor styling
  const lightTheme = EditorView.theme({
    '&': {
      color: '#333',
      backgroundColor: '#fff',
    },
    '.cm-content': {
      caretColor: '#333',
    },
    '.cm-editor': {
      fontSize: '14px',
    },
    '.cm-editor.cm-focused': {
      outline: 'none',
    },
    '&.cm-focused .cm-cursor': {
      borderLeftColor: '#333',
    },
    '&.cm-focused .cm-selectionBackground': {
      backgroundColor: '#b3d4fc',
    },
    '.cm-gutters': {
      backgroundColor: '#f5f5f5',
      color: '#999',
      border: 'none',
    },
    '.cm-lineNumbers .cm-gutterElement': {
      minWidth: '3ch',
      padding: '0 8px',
    },
    '.cm-line': {
      padding: '0 4px',
    },
  }, { dark: false });

  return (
    <div ref={editorRef} className="h-full w-full">
      <CodeMirror
        value={currentCode}
        height={editorHeight}
        extensions={[getLanguageExtension(), lightTheme, syntaxHighlightingExtension]}
        onChange={(value) => updateCode(value)}
        placeholder="Write your code here..."
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          dropCursor: false,
          allowMultipleSelections: false,
        }}
      />
    </div>
  );
};

export default CodeEditor;


declare module 'react-simplemde-editor' {
  import * as React from 'react';
  
  interface SimpleMDEEditorProps {
    value: string;
    onChange: (value: string) => void;
    options?: any;
    events?: any;
    className?: string;
    id?: string;
  }
  
  const SimpleMDEEditor: React.ComponentType<SimpleMDEEditorProps>;
  export default SimpleMDEEditor;
} 
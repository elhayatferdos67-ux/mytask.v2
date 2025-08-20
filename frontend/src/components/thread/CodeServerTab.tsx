'use client';

import React from 'react';
import { CodeEditorPanel } from '@/components/code-editor';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Code } from 'lucide-react';

interface CodeServerTabProps {
  sandboxId: string;
  className?: string;
}

export function CodeServerTab({ sandboxId, className = '' }: CodeServerTabProps) {
  return (
    <div className={`h-full ${className}`}>
      <CodeEditorPanel 
        sandboxId={sandboxId}
        defaultTab="editor"
        className="h-full"
      />
    </div>
  );
}

// Alternative simpler version for direct integration
export function CodeServerSimple({ sandboxId, className = '' }: CodeServerTabProps) {
  return (
    <Card className={`h-full ${className}`}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Code className="h-5 w-5" />
          VS Code IDE
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0">
        <CodeEditorPanel 
          sandboxId={sandboxId}
          defaultTab="editor"
          className="h-full"
        />
      </CardContent>
    </Card>
  );
}
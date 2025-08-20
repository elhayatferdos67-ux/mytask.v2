'use client';

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CodeEditorPanel } from '@/components/code-editor';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CodeServerModalProps {
  isOpen: boolean;
  onClose: () => void;
  sandboxId: string;
  projectName?: string;
}

export function CodeServerModal({
  isOpen,
  onClose,
  sandboxId,
  projectName = 'Project'
}: CodeServerModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[95vw] max-h-[95vh] w-full h-full p-0">
        <DialogHeader className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-lg font-semibold">
              VS Code IDE - {projectName}
            </DialogTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-8 w-8"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden">
          <CodeEditorPanel 
            sandboxId={sandboxId}
            defaultTab="editor"
            className="h-full"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
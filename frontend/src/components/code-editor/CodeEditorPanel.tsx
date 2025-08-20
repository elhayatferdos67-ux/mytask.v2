'use client';

import React, { useState, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CodeServerIframe } from './CodeServerIframe';
import { FileBrowser } from '../thread/file-browser';
import { 
  Code, 
  Files, 
  Terminal, 
  Plus, 
  FolderPlus,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface CodeEditorPanelProps {
  sandboxId: string;
  className?: string;
  defaultTab?: 'editor' | 'files' | 'terminal';
}

interface Project {
  name: string;
  path: string;
  type: string;
}

const PROJECT_TYPES = [
  { value: 'react', label: 'React App', description: 'Create a new React application' },
  { value: 'nextjs', label: 'Next.js App', description: 'Create a Next.js application with TypeScript' },
  { value: 'python', label: 'Python Project', description: 'Basic Python project structure' },
  { value: 'fastapi', label: 'FastAPI Project', description: 'FastAPI web application' },
  { value: 'basic', label: 'Basic Project', description: 'Simple project with basic structure' }
];

export function CodeEditorPanel({ 
  sandboxId, 
  className = '',
  defaultTab = 'editor'
}: CodeEditorPanelProps) {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    type: 'react'
  });

  // API call helper
  const apiCall = useCallback(async (endpoint: string, method: 'GET' | 'POST' | 'DELETE' = 'GET', body?: any) => {
    const response = await fetch(`/api/code-server/${endpoint}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }, []);

  // Load projects list
  const loadProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    try {
      const result = await apiCall(`list-projects/${sandboxId}`);
      if (result.status === 'success') {
        setProjects(result.projects || []);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
      toast.error('Failed to load projects');
    } finally {
      setIsLoadingProjects(false);
    }
  }, [sandboxId, apiCall]);

  // Create new project
  const createProject = useCallback(async () => {
    if (!newProject.name.trim()) {
      toast.error('Please enter a project name');
      return;
    }

    setIsCreatingProject(true);
    try {
      const result = await apiCall(`create-project/${sandboxId}`, 'POST', {
        project_name: newProject.name,
        project_type: newProject.type,
        auto_install_deps: true
      });

      if (result.status === 'success') {
        toast.success(`Project "${newProject.name}" created successfully`);
        setShowCreateDialog(false);
        setNewProject({ name: '', type: 'react' });
        await loadProjects();
      } else {
        throw new Error(result.message || 'Failed to create project');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      toast.error(`Failed to create project: ${errorMsg}`);
    } finally {
      setIsCreatingProject(false);
    }
  }, [sandboxId, newProject, apiCall, loadProjects]);

  // Delete project
  const deleteProject = useCallback(async (projectName: string) => {
    try {
      const result = await apiCall(`delete-project/${sandboxId}/${projectName}`, 'DELETE');
      
      if (result.status === 'success') {
        toast.success(`Project "${projectName}" deleted successfully`);
        await loadProjects();
      } else {
        throw new Error(result.message || 'Failed to delete project');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      toast.error(`Failed to delete project: ${errorMsg}`);
    }
  }, [sandboxId, apiCall, loadProjects]);

  // Load projects on mount
  React.useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Projects list component
  const ProjectsList = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Projects</h3>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="project-name">Project Name</Label>
                <Input
                  id="project-name"
                  value={newProject.name}
                  onChange={(e) => setNewProject(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="my-awesome-project"
                />
              </div>
              <div>
                <Label htmlFor="project-type">Project Type</Label>
                <Select 
                  value={newProject.type} 
                  onValueChange={(value) => setNewProject(prev => ({ ...prev, type: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROJECT_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        <div>
                          <div className="font-medium">{type.label}</div>
                          <div className="text-sm text-muted-foreground">{type.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={createProject} disabled={isCreatingProject}>
                  {isCreatingProject ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <FolderPlus className="h-4 w-4 mr-2" />
                  )}
                  Create Project
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoadingProjects ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : projects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <FolderPlus className="h-12 w-12 text-muted-foreground mb-4" />
            <h4 className="font-medium mb-2">No Projects Yet</h4>
            <p className="text-sm text-muted-foreground text-center mb-4">
              Create your first project to start coding
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {projects.map((project) => (
            <Card key={project.name} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                      <Code className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h4 className="font-medium">{project.name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="secondary" className="text-xs">
                          {project.type}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {project.path}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => deleteProject(project.name)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className={cn("h-full flex flex-col", className)}>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        <TabsList className="grid w-full grid-cols-3 mb-4">
          <TabsTrigger value="editor" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            Code Editor
          </TabsTrigger>
          <TabsTrigger value="files" className="flex items-center gap-2">
            <Files className="h-4 w-4" />
            File Browser
          </TabsTrigger>
          <TabsTrigger value="projects" className="flex items-center gap-2">
            <FolderPlus className="h-4 w-4" />
            Projects
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="editor" className="flex-1 mt-0">
          <CodeServerIframe 
            sandboxId={sandboxId}
            className="h-full"
            onReady={() => console.log('Code Server ready')}
            onError={(error) => console.error('Code Server error:', error)}
            autoStart={true}
          />
        </TabsContent>
        
        <TabsContent value="files" className="flex-1 mt-0">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Files className="h-5 w-5" />
                File Browser
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
              <FileBrowser 
                sandboxId={sandboxId}
                onSelectFile={(path, content) => {
                  console.log('Selected file:', path);
                  // Could switch to editor tab and open file
                  setActiveTab('editor');
                }}
              />
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="projects" className="flex-1 mt-0">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FolderPlus className="h-5 w-5" />
                Project Management
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              <ProjectsList />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
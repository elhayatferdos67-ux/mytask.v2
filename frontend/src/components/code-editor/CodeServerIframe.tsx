'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Loader2, 
  Code, 
  RefreshCw, 
  Play, 
  Square, 
  Monitor,
  AlertCircle,
  CheckCircle,
  Settings
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface CodeServerIframeProps {
  sandboxId: string;
  className?: string;
  onReady?: () => void;
  onError?: (error: string) => void;
  autoStart?: boolean;
}

interface CodeServerStatus {
  status: 'not_initialized' | 'stopped' | 'running' | 'error';
  ready?: boolean;
  port?: number;
  url?: string;
  workspace?: string;
  pid?: number;
  message?: string;
}

export function CodeServerIframe({ 
  sandboxId, 
  className = '',
  onReady,
  onError,
  autoStart = true
}: CodeServerIframeProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<CodeServerStatus>({ status: 'not_initialized' });
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const statusCheckInterval = useRef<NodeJS.Timeout | null>(null);

  // API call helper
  const apiCall = useCallback(async (endpoint: string, method: 'GET' | 'POST' | 'DELETE' = 'GET') => {
    const response = await fetch(`/api/code-server/${endpoint}`, {
      method,
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }, []);

  // Check Code Server status
  const checkStatus = useCallback(async () => {
    try {
      const result = await apiCall(`status/${sandboxId}`);
      setStatus(result);
      
      if (result.status === 'error') {
        setError(result.message || 'Unknown error');
        onError?.(result.message || 'Unknown error');
      } else {
        setError(null);
      }
      
      return result;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to check status';
      setError(errorMsg);
      onError?.(errorMsg);
      return null;
    }
  }, [sandboxId, apiCall, onError]);

  // Start Code Server
  const startCodeServer = useCallback(async () => {
    setIsStarting(true);
    setError(null);
    
    try {
      const result = await apiCall(`start/${sandboxId}`, 'POST');
      
      if (result.status === 'running' || result.status === 'already_running') {
        setStatus(result);
        toast.success('Code Server started successfully');
        
        // Wait a bit for the server to be fully ready
        setTimeout(() => {
          setIsLoading(false);
          onReady?.();
        }, 2000);
      } else {
        throw new Error(result.message || 'Failed to start Code Server');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      toast.error(`Failed to start Code Server: ${errorMsg}`);
      onError?.(errorMsg);
    } finally {
      setIsStarting(false);
    }
  }, [sandboxId, apiCall, onReady, onError]);

  // Stop Code Server
  const stopCodeServer = useCallback(async () => {
    setIsStopping(true);
    
    try {
      const result = await apiCall(`stop/${sandboxId}`, 'POST');
      
      if (result.status === 'stopped' || result.status === 'not_running') {
        setStatus(result);
        toast.success('Code Server stopped');
      } else {
        throw new Error(result.message || 'Failed to stop Code Server');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      toast.error(`Failed to stop Code Server: ${errorMsg}`);
    } finally {
      setIsStopping(false);
    }
  }, [sandboxId, apiCall]);

  // Restart Code Server
  const restartCodeServer = useCallback(async () => {
    setIsStarting(true);
    setError(null);
    
    try {
      const result = await apiCall(`restart/${sandboxId}`, 'POST');
      
      if (result.status === 'running') {
        setStatus(result);
        toast.success('Code Server restarted successfully');
        setIsLoading(false);
        onReady?.();
      } else {
        throw new Error(result.message || 'Failed to restart Code Server');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      toast.error(`Failed to restart Code Server: ${errorMsg}`);
    } finally {
      setIsStarting(false);
    }
  }, [sandboxId, apiCall, onReady]);

  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    if (status.status === 'running') {
      setIsLoading(false);
      onReady?.();
    }
  }, [status.status, onReady]);

  // Handle iframe error
  const handleIframeError = useCallback(() => {
    setIsLoading(false);
    setError('Failed to load Code Server interface');
  }, []);

  // Initialize and start periodic status checks
  useEffect(() => {
    const initializeCodeServer = async () => {
      const currentStatus = await checkStatus();
      
      if (autoStart && currentStatus?.status === 'not_initialized') {
        await startCodeServer();
      } else if (currentStatus?.status === 'running') {
        setIsLoading(false);
      }
    };

    initializeCodeServer();

    // Set up periodic status checks
    statusCheckInterval.current = setInterval(checkStatus, 10000); // Check every 10 seconds

    return () => {
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current);
      }
    };
  }, [sandboxId, autoStart, checkStatus, startCodeServer]);

  // Status indicator component
  const StatusIndicator = () => {
    const getStatusColor = () => {
      switch (status.status) {
        case 'running': return 'bg-green-500';
        case 'stopped': return 'bg-gray-500';
        case 'error': return 'bg-red-500';
        default: return 'bg-yellow-500';
      }
    };

    const getStatusIcon = () => {
      switch (status.status) {
        case 'running': return <CheckCircle className="h-4 w-4" />;
        case 'error': return <AlertCircle className="h-4 w-4" />;
        default: return <Monitor className="h-4 w-4" />;
      }
    };

    return (
      <div className="flex items-center gap-2">
        <div className={cn("w-2 h-2 rounded-full", getStatusColor())} />
        {getStatusIcon()}
        <span className="text-sm font-medium capitalize">
          {status.status.replace('_', ' ')}
        </span>
        {status.port && (
          <Badge variant="outline" className="text-xs">
            Port {status.port}
          </Badge>
        )}
      </div>
    );
  };

  // Control buttons
  const ControlButtons = () => (
    <div className="flex items-center gap-2">
      {status.status === 'running' ? (
        <>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={restartCodeServer}
            disabled={isStarting}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isStarting && "animate-spin")} />
            Restart
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={stopCodeServer}
            disabled={isStopping}
          >
            <Square className="h-4 w-4 mr-2" />
            Stop
          </Button>
        </>
      ) : (
        <Button 
          onClick={startCodeServer} 
          disabled={isStarting}
          size="sm"
        >
          {isStarting ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-2" />
          )}
          Start
        </Button>
      )}
    </div>
  );

  // If Code Server is not running, show control panel
  if (status.status !== 'running') {
    return (
      <div className={cn("flex flex-col h-full", className)}>
        <Card className="h-full">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Code Server
              </CardTitle>
              <StatusIndicator />
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 flex flex-col items-center justify-center space-y-6">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 mx-auto bg-muted rounded-full flex items-center justify-center">
                <Code className="h-8 w-8 text-muted-foreground" />
              </div>
              
              <div>
                <h3 className="text-lg font-semibold">VS Code in Browser</h3>
                <p className="text-muted-foreground text-sm max-w-md">
                  {status.status === 'not_initialized' 
                    ? "Initialize Code Server to start coding in your browser with full VS Code features"
                    : status.status === 'stopped'
                    ? "Code Server is stopped. Start it to continue coding"
                    : "Setting up your development environment..."
                  }
                </p>
              </div>

              <ControlButtons />

              {status.workspace && (
                <div className="text-xs text-muted-foreground">
                  Workspace: {status.workspace}
                </div>
              )}
            </div>

            {error && (
              <Alert variant="destructive" className="max-w-md">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {isStarting && (
              <div className="text-center space-y-2">
                <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                <p className="text-sm text-muted-foreground">
                  Starting Code Server... This may take a moment
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  // Code Server is running, show iframe
  return (
    <div className={cn("relative h-full flex flex-col", className)}>
      {/* Header with status and controls */}
      <div className="flex items-center justify-between p-2 border-b bg-muted/50">
        <StatusIndicator />
        <ControlButtons />
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10">
          <div className="text-center space-y-3">
            <Loader2 className="h-8 w-8 animate-spin mx-auto" />
            <div>
              <p className="font-medium">Loading VS Code...</p>
              <p className="text-sm text-muted-foreground">
                Setting up your development environment
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Code Server iframe */}
      <div className="flex-1 relative">
        <iframe
          ref={iframeRef}
          src={status.url}
          className="w-full h-full border-0"
          onLoad={handleIframeLoad}
          onError={handleIframeError}
          sandbox="allow-same-origin allow-scripts allow-forms allow-downloads allow-modals allow-popups"
          title="VS Code - Code Server"
          allow="clipboard-read; clipboard-write"
        />
      </div>
      
      {/* Error overlay */}
      {error && (
        <Alert variant="destructive" className="absolute top-16 left-4 right-4 z-20">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            {error}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={restartCodeServer}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
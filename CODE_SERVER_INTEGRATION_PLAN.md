# خطة دمج Code Server في مشروع Suna AI

## 🎯 الهدف
دمج **Code Server** (VS Code في المتصفح) مباشرة في واجهة Suna AI بحيث يكون مدمجاً تماماً مثل بيئة OpenHands، مع إمكانية إنشاء وتعديل الأكواد في الوقت الفعلي.

---

## 🔍 التحليل الحالي

### ✅ ما هو متاح حالياً:
- **CodeMirror**: محرر كود أساسي للعرض فقط
- **File Browser**: متصفح ملفات مع إمكانية العرض
- **Sandbox Integration**: تكامل مع Daytona SDK
- **Real-time Updates**: تحديثات فورية عبر WebSocket

### ❌ ما هو مفقود:
- **IDE متكامل**: لا يوجد محرر كود متقدم
- **IntelliSense**: لا يوجد إكمال تلقائي للكود
- **Git Integration**: لا يوجد تكامل مع Git
- **Extensions Support**: لا يوجد دعم للإضافات
- **Multi-file Editing**: لا يمكن تحرير عدة ملفات

---

## 🏗️ خطة التنفيذ

### المرحلة 1: إعداد Code Server في Backend

#### 1.1 إضافة Code Server إلى Sandbox
```python
# backend/sandbox/code_server_manager.py
import asyncio
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

class CodeServerManager:
    """مدير Code Server للتكامل مع Sandbox"""
    
    def __init__(self, sandbox_id: str, workspace_path: str = "/workspace"):
        self.sandbox_id = sandbox_id
        self.workspace_path = workspace_path
        self.code_server_port = 8080
        self.process: Optional[subprocess.Popen] = None
        
    async def start_code_server(self) -> Dict[str, Any]:
        """بدء تشغيل Code Server"""
        try:
            # تثبيت Code Server إذا لم يكن موجوداً
            await self._ensure_code_server_installed()
            
            # إعداد التكوين
            config = await self._setup_config()
            
            # بدء التشغيل
            cmd = [
                "code-server",
                "--bind-addr", f"0.0.0.0:{self.code_server_port}",
                "--auth", "none",  # بدون مصادقة (آمن داخل Sandbox)
                "--disable-telemetry",
                "--disable-update-check",
                self.workspace_path
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.workspace_path
            )
            
            # انتظار بدء التشغيل
            await self._wait_for_startup()
            
            return {
                "status": "running",
                "port": self.code_server_port,
                "url": f"http://localhost:{self.code_server_port}",
                "workspace": self.workspace_path
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _ensure_code_server_installed(self):
        """التأكد من تثبيت Code Server"""
        try:
            # فحص إذا كان مثبتاً
            result = subprocess.run(["code-server", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return
        except FileNotFoundError:
            pass
        
        # تثبيت Code Server
        install_cmd = [
            "curl", "-fsSL", 
            "https://code-server.dev/install.sh", 
            "|", "sh"
        ]
        subprocess.run(" ".join(install_cmd), shell=True, check=True)
    
    async def _setup_config(self) -> Dict[str, Any]:
        """إعداد تكوين Code Server"""
        config_dir = Path.home() / ".config" / "code-server"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config = {
            "bind-addr": f"0.0.0.0:{self.code_server_port}",
            "auth": "none",
            "cert": False,
            "disable-telemetry": True,
            "disable-update-check": True
        }
        
        # كتابة ملف التكوين
        config_file = config_dir / "config.yaml"
        with open(config_file, "w") as f:
            import yaml
            yaml.dump(config, f)
        
        return config
    
    async def _wait_for_startup(self, timeout: int = 30):
        """انتظار بدء تشغيل Code Server"""
        import aiohttp
        import asyncio
        
        for _ in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{self.code_server_port}") as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(1)
        
        raise TimeoutError("Code Server failed to start within timeout")
    
    async def stop_code_server(self):
        """إيقاف Code Server"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
    
    def is_running(self) -> bool:
        """فحص إذا كان Code Server يعمل"""
        return self.process is not None and self.process.poll() is None
```

#### 1.2 إضافة APIs للتحكم في Code Server
```python
# backend/sandbox/code_server_api.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from .code_server_manager import CodeServerManager
from utils.auth_utils import get_user_id

router = APIRouter(prefix="/code-server", tags=["code-server"])

# تخزين مؤقت لمديري Code Server
code_servers: Dict[str, CodeServerManager] = {}

@router.post("/start/{sandbox_id}")
async def start_code_server(
    sandbox_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """بدء تشغيل Code Server لـ Sandbox محدد"""
    try:
        # إنشاء مدير جديد إذا لم يكن موجوداً
        if sandbox_id not in code_servers:
            code_servers[sandbox_id] = CodeServerManager(sandbox_id)
        
        manager = code_servers[sandbox_id]
        
        # بدء التشغيل إذا لم يكن يعمل
        if not manager.is_running():
            result = await manager.start_code_server()
            return result
        else:
            return {
                "status": "already_running",
                "port": manager.code_server_port,
                "url": f"http://localhost:{manager.code_server_port}"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop/{sandbox_id}")
async def stop_code_server(
    sandbox_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """إيقاف Code Server"""
    try:
        if sandbox_id in code_servers:
            manager = code_servers[sandbox_id]
            await manager.stop_code_server()
            del code_servers[sandbox_id]
            return {"status": "stopped"}
        else:
            return {"status": "not_running"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{sandbox_id}")
async def get_code_server_status(
    sandbox_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """الحصول على حالة Code Server"""
    if sandbox_id in code_servers:
        manager = code_servers[sandbox_id]
        return {
            "status": "running" if manager.is_running() else "stopped",
            "port": manager.code_server_port,
            "url": f"http://localhost:{manager.code_server_port}"
        }
    else:
        return {"status": "not_initialized"}
```

### المرحلة 2: دمج Code Server في Frontend

#### 2.1 إنشاء مكون Code Server
```typescript
// frontend/src/components/code-editor/CodeServerIframe.tsx
'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Code, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

interface CodeServerIframeProps {
  sandboxId: string;
  className?: string;
  onReady?: () => void;
}

export function CodeServerIframe({ 
  sandboxId, 
  className = '',
  onReady 
}: CodeServerIframeProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeServerUrl, setCodeServerUrl] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // بدء تشغيل Code Server
  const startCodeServer = async () => {
    setIsStarting(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/code-server/start/${sandboxId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const result = await response.json();
      
      if (result.status === 'running' || result.status === 'already_running') {
        setCodeServerUrl(result.url);
        toast.success('Code Server started successfully');
      } else {
        throw new Error(result.message || 'Failed to start Code Server');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      toast.error(`Failed to start Code Server: ${errorMsg}`);
    } finally {
      setIsStarting(false);
    }
  };

  // فحص حالة Code Server
  const checkStatus = async () => {
    try {
      const response = await fetch(`/api/code-server/status/${sandboxId}`);
      const result = await response.json();
      
      if (result.status === 'running') {
        setCodeServerUrl(result.url);
      } else {
        setCodeServerUrl(null);
      }
    } catch (err) {
      console.error('Failed to check Code Server status:', err);
    }
  };

  // التحقق من الحالة عند التحميل
  useEffect(() => {
    checkStatus();
  }, [sandboxId]);

  // معالج تحميل الـ iframe
  const handleIframeLoad = () => {
    setIsLoading(false);
    onReady?.();
  };

  // معالج خطأ الـ iframe
  const handleIframeError = () => {
    setIsLoading(false);
    setError('Failed to load Code Server');
  };

  if (!codeServerUrl) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <div className="text-center space-y-4">
          <Code className="h-16 w-16 text-muted-foreground mx-auto" />
          <div>
            <h3 className="text-lg font-semibold">Code Server Not Running</h3>
            <p className="text-muted-foreground">
              Start Code Server to begin coding in your browser
            </p>
          </div>
          <Button 
            onClick={startCodeServer} 
            disabled={isStarting}
            className="min-w-32"
          >
            {isStarting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Code className="h-4 w-4 mr-2" />
                Start Code Server
              </>
            )}
          </Button>
          {error && (
            <Alert variant="destructive" className="max-w-md">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`relative h-full ${className}`}>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10">
          <div className="text-center space-y-2">
            <Loader2 className="h-8 w-8 animate-spin mx-auto" />
            <p className="text-sm text-muted-foreground">Loading Code Server...</p>
          </div>
        </div>
      )}
      
      <iframe
        ref={iframeRef}
        src={codeServerUrl}
        className="w-full h-full border-0"
        onLoad={handleIframeLoad}
        onError={handleIframeError}
        sandbox="allow-same-origin allow-scripts allow-forms allow-downloads allow-modals"
        title="Code Server IDE"
      />
      
      {error && (
        <Alert variant="destructive" className="absolute top-4 left-4 right-4 z-20">
          <AlertDescription className="flex items-center justify-between">
            {error}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
```

#### 2.2 دمج Code Server في واجهة Thread
```typescript
// frontend/src/components/thread/CodeEditorPanel.tsx
'use client';

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { CodeServerIframe } from '@/components/code-editor/CodeServerIframe';
import { FileBrowser } from './file-browser';
import { Code, Files, Terminal } from 'lucide-react';

interface CodeEditorPanelProps {
  sandboxId: string;
  className?: string;
}

export function CodeEditorPanel({ sandboxId, className = '' }: CodeEditorPanelProps) {
  const [activeTab, setActiveTab] = useState('editor');

  return (
    <div className={`h-full flex flex-col ${className}`}>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="editor" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            Code Editor
          </TabsTrigger>
          <TabsTrigger value="files" className="flex items-center gap-2">
            <Files className="h-4 w-4" />
            File Browser
          </TabsTrigger>
          <TabsTrigger value="terminal" className="flex items-center gap-2">
            <Terminal className="h-4 w-4" />
            Terminal
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="editor" className="flex-1 mt-0">
          <CodeServerIframe 
            sandboxId={sandboxId}
            className="h-full"
            onReady={() => console.log('Code Server ready')}
          />
        </TabsContent>
        
        <TabsContent value="files" className="flex-1 mt-0">
          <FileBrowser 
            sandboxId={sandboxId}
            onSelectFile={(path, content) => {
              // يمكن إضافة منطق لفتح الملف في Code Server
              console.log('Selected file:', path);
            }}
          />
        </TabsContent>
        
        <TabsContent value="terminal" className="flex-1 mt-0">
          {/* يمكن إضافة Terminal مدمج هنا */}
          <div className="h-full flex items-center justify-center text-muted-foreground">
            Terminal integration coming soon...
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

### المرحلة 3: تحسين التكامل مع الأدوات

#### 3.1 تحديث أداة تطوير الويب
```python
# backend/agent/tools/enhanced_web_dev_tool.py
from .sb_web_dev_tool import SandboxWebDevTool
from ..sandbox.code_server_manager import CodeServerManager

class EnhancedWebDevTool(SandboxWebDevTool):
    """أداة تطوير ويب محسنة مع دعم Code Server"""
    
    def __init__(self, project_id: str, thread_id: str, thread_manager):
        super().__init__(project_id, thread_id, thread_manager)
        self.code_server_manager = None
    
    async def _ensure_code_server(self):
        """التأكد من تشغيل Code Server"""
        if not self.code_server_manager:
            self.code_server_manager = CodeServerManager(
                sandbox_id=self.project_id,
                workspace_path=self.workspace_path
            )
        
        if not self.code_server_manager.is_running():
            await self.code_server_manager.start_code_server()
    
    @openapi_schema({
        "name": "create_project_with_ide",
        "description": "إنشاء مشروع جديد مع فتح IDE مدمج",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "اسم المشروع"},
                "template": {"type": "string", "description": "قالب المشروع"},
                "open_in_ide": {"type": "boolean", "description": "فتح في IDE", "default": True}
            },
            "required": ["project_name", "template"]
        }
    })
    async def create_project_with_ide(
        self, 
        project_name: str, 
        template: str,
        open_in_ide: bool = True
    ) -> ToolResult:
        """إنشاء مشروع جديد مع فتح IDE"""
        try:
            # إنشاء المشروع
            result = await self.create_project(project_name, template)
            
            if open_in_ide:
                # بدء تشغيل Code Server
                await self._ensure_code_server()
                
                return ToolResult(
                    success=True,
                    result=f"Project '{project_name}' created successfully and opened in IDE",
                    metadata={
                        "project_path": f"{self.workspace_path}/{project_name}",
                        "ide_url": f"http://localhost:{self.code_server_manager.code_server_port}",
                        "template": template
                    }
                )
            
            return result
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to create project: {str(e)}"
            )
```

### المرحلة 4: إضافة الميزات المتقدمة

#### 4.1 تكامل Git
```python
# backend/sandbox/git_integration.py
import subprocess
from typing import Dict, Any, List

class GitIntegration:
    """تكامل Git مع Code Server"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
    
    async def init_repository(self) -> Dict[str, Any]:
        """تهيئة مستودع Git جديد"""
        try:
            subprocess.run(["git", "init"], cwd=self.workspace_path, check=True)
            return {"status": "success", "message": "Git repository initialized"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
    
    async def clone_repository(self, repo_url: str) -> Dict[str, Any]:
        """استنساخ مستودع Git"""
        try:
            subprocess.run(
                ["git", "clone", repo_url, "."], 
                cwd=self.workspace_path, 
                check=True
            )
            return {"status": "success", "message": f"Repository cloned from {repo_url}"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """الحصول على حالة Git"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"], 
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                "status": "success",
                "changes": result.stdout.strip().split('\n') if result.stdout.strip() else []
            }
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
```

#### 4.2 تكامل مع أدوات البناء
```python
# backend/sandbox/build_tools.py
import asyncio
import subprocess
from typing import Dict, Any, Optional

class BuildToolsManager:
    """مدير أدوات البناء والتطوير"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
    
    async def detect_project_type(self) -> str:
        """اكتشاف نوع المشروع"""
        import os
        
        if os.path.exists(f"{self.workspace_path}/package.json"):
            return "nodejs"
        elif os.path.exists(f"{self.workspace_path}/requirements.txt"):
            return "python"
        elif os.path.exists(f"{self.workspace_path}/Cargo.toml"):
            return "rust"
        elif os.path.exists(f"{self.workspace_path}/go.mod"):
            return "go"
        else:
            return "unknown"
    
    async def install_dependencies(self) -> Dict[str, Any]:
        """تثبيت التبعيات حسب نوع المشروع"""
        project_type = await self.detect_project_type()
        
        try:
            if project_type == "nodejs":
                subprocess.run(["npm", "install"], cwd=self.workspace_path, check=True)
            elif project_type == "python":
                subprocess.run(["pip", "install", "-r", "requirements.txt"], 
                             cwd=self.workspace_path, check=True)
            elif project_type == "rust":
                subprocess.run(["cargo", "build"], cwd=self.workspace_path, check=True)
            elif project_type == "go":
                subprocess.run(["go", "mod", "download"], cwd=self.workspace_path, check=True)
            
            return {"status": "success", "project_type": project_type}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
    
    async def run_dev_server(self) -> Dict[str, Any]:
        """تشغيل خادم التطوير"""
        project_type = await self.detect_project_type()
        
        try:
            if project_type == "nodejs":
                # تشغيل في الخلفية
                process = subprocess.Popen(
                    ["npm", "run", "dev"],
                    cwd=self.workspace_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                return {"status": "success", "pid": process.pid, "project_type": project_type}
            # إضافة دعم لأنواع مشاريع أخرى
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

---

## 🔧 التكوين والإعداد

### 1. تحديث Docker Configuration
```dockerfile
# backend/sandbox/docker/Dockerfile
FROM ubuntu:22.04

# تثبيت Code Server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# تثبيت الأدوات الأساسية
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    python3 \
    python3-pip \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# إعداد Code Server
RUN mkdir -p /root/.config/code-server
COPY code-server-config.yaml /root/.config/code-server/config.yaml

# تثبيت Extensions الأساسية
RUN code-server --install-extension ms-python.python
RUN code-server --install-extension bradlc.vscode-tailwindcss
RUN code-server --install-extension esbenp.prettier-vscode

EXPOSE 8080
```

### 2. تحديث Frontend Package.json
```json
{
  "dependencies": {
    "@monaco-editor/react": "^4.6.0",
    "xterm": "^5.3.0",
    "xterm-addon-fit": "^0.8.0",
    "socket.io-client": "^4.7.5"
  }
}
```

---

## 🚀 الميزات المتوقعة بعد التنفيذ

### ✅ للمطورين:
- **IDE كامل في المتصفح** مثل VS Code
- **IntelliSense وإكمال تلقائي** للكود
- **Git integration** مدمج
- **Terminal مدمج** للأوامر
- **Extensions support** للإضافات
- **Multi-file editing** تحرير عدة ملفات
- **Real-time collaboration** تعاون فوري

### ✅ للمشاريع:
- **Project templates** قوالب جاهزة
- **Auto dependency management** إدارة تلقائية للتبعيات
- **Live preview** معاينة مباشرة
- **Hot reload** إعادة تحميل فورية
- **Build tools integration** تكامل أدوات البناء

### ✅ للفرق:
- **Shared workspaces** مساحات عمل مشتركة
- **Real-time editing** تحرير متزامن
- **Code review tools** أدوات مراجعة الكود
- **Version control** تحكم في الإصدارات

---

## 📊 خطة التنفيذ الزمنية

### الأسبوع 1-2: Backend Setup
- [ ] إعداد Code Server Manager
- [ ] إضافة APIs للتحكم
- [ ] تحديث Sandbox configuration

### الأسبوع 3-4: Frontend Integration
- [ ] إنشاء Code Server component
- [ ] دمج في Thread interface
- [ ] إضافة File browser integration

### الأسبوع 5-6: Advanced Features
- [ ] Git integration
- [ ] Build tools support
- [ ] Extensions management

### الأسبوع 7-8: Testing & Polish
- [ ] اختبار شامل
- [ ] تحسين الأداء
- [ ] إضافة التوثيق

---

## 🎯 النتيجة المتوقعة

بعد تنفيذ هذه الخطة، سيصبح لدى Suna AI:

1. **IDE متكامل** مثل VS Code في المتصفح
2. **تكامل سلس** مع الأدوات الحالية
3. **تجربة تطوير متقدمة** مثل بيئة OpenHands
4. **إمكانيات تعاون فوري** للفرق
5. **دعم شامل** لجميع لغات البرمجة

هذا سيجعل Suna AI منصة تطوير فول ستاك حقيقية وقوية! 🚀
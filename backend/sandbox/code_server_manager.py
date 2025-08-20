"""
Code Server Manager for Suna AI
Integrates VS Code in the browser with Sandbox environment
"""

import asyncio
import subprocess
import aiohttp
import yaml
import os
import signal
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class CodeServerConfig:
    """Configuration for Code Server instance"""
    bind_addr: str = "0.0.0.0"
    port: int = 8080
    auth: str = "none"
    cert: bool = False
    disable_telemetry: bool = True
    disable_update_check: bool = True
    workspace_path: str = "/workspace"


class CodeServerManager:
    """
    Manager for Code Server instances integrated with Suna AI Sandbox
    Provides VS Code in browser functionality with real-time file editing
    """
    
    def __init__(self, sandbox_id: str, workspace_path: str = "/workspace"):
        self.sandbox_id = sandbox_id
        self.workspace_path = Path(workspace_path)
        self.config = CodeServerConfig(workspace_path=str(self.workspace_path))
        self.process: Optional[subprocess.Popen] = None
        self.is_ready = False
        
        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized Code Server Manager for sandbox {sandbox_id}")
    
    async def start_code_server(self) -> Dict[str, Any]:
        """
        Start Code Server instance
        Returns status information including URL and port
        """
        try:
            if self.is_running():
                return {
                    "status": "already_running",
                    "port": self.config.port,
                    "url": f"http://localhost:{self.config.port}",
                    "workspace": str(self.workspace_path)
                }
            
            # Ensure Code Server is installed
            await self._ensure_code_server_installed()
            
            # Setup configuration
            await self._setup_config()
            
            # Install essential extensions
            await self._install_essential_extensions()
            
            # Start Code Server process
            await self._start_process()
            
            # Wait for startup
            await self._wait_for_startup()
            
            self.is_ready = True
            
            logger.info(f"Code Server started successfully for sandbox {self.sandbox_id}")
            
            return {
                "status": "running",
                "port": self.config.port,
                "url": f"http://localhost:{self.config.port}",
                "workspace": str(self.workspace_path),
                "pid": self.process.pid if self.process else None
            }
            
        except Exception as e:
            logger.error(f"Failed to start Code Server for sandbox {self.sandbox_id}: {str(e)}")
            return {
                "status": "error", 
                "message": str(e),
                "workspace": str(self.workspace_path)
            }
    
    async def _ensure_code_server_installed(self):
        """Ensure Code Server is installed in the system"""
        try:
            # Check if already installed
            result = subprocess.run(
                ["code-server", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.debug("Code Server already installed")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        logger.info("Installing Code Server...")
        
        # Install Code Server using the official script
        install_script = """
        curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone
        """
        
        process = await asyncio.create_subprocess_shell(
            install_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to install Code Server: {stderr.decode()}")
        
        logger.info("Code Server installed successfully")
    
    async def _setup_config(self):
        """Setup Code Server configuration"""
        config_dir = Path.home() / ".config" / "code-server"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            "bind-addr": f"{self.config.bind_addr}:{self.config.port}",
            "auth": self.config.auth,
            "cert": self.config.cert,
            "disable-telemetry": self.config.disable_telemetry,
            "disable-update-check": self.config.disable_update_check,
        }
        
        config_file = config_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        logger.debug(f"Code Server config written to {config_file}")
    
    async def _install_essential_extensions(self):
        """Install essential VS Code extensions"""
        essential_extensions = [
            "ms-python.python",
            "ms-vscode.vscode-typescript-next",
            "bradlc.vscode-tailwindcss",
            "esbenp.prettier-vscode",
            "ms-vscode.vscode-json",
            "redhat.vscode-yaml",
            "ms-vscode.vscode-css",
            "formulahendry.auto-rename-tag",
            "christian-kohler.path-intellisense",
            "ms-vscode.vscode-eslint"
        ]
        
        logger.info("Installing essential VS Code extensions...")
        
        for extension in essential_extensions:
            try:
                process = await asyncio.create_subprocess_exec(
                    "code-server", "--install-extension", extension,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    logger.debug(f"Installed extension: {extension}")
                else:
                    logger.warning(f"Failed to install extension {extension}: {stderr.decode()}")
                    
            except Exception as e:
                logger.warning(f"Error installing extension {extension}: {str(e)}")
    
    async def _start_process(self):
        """Start the Code Server process"""
        cmd = [
            "code-server",
            "--bind-addr", f"{self.config.bind_addr}:{self.config.port}",
            "--auth", self.config.auth,
            "--disable-telemetry",
            "--disable-update-check",
            str(self.workspace_path)
        ]
        
        logger.debug(f"Starting Code Server with command: {' '.join(cmd)}")
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.workspace_path),
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Give it a moment to start
        await asyncio.sleep(2)
        
        if self.process.poll() is not None:
            # Process died immediately
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"Code Server failed to start: {stderr.decode()}")
    
    async def _wait_for_startup(self, timeout: int = 60):
        """Wait for Code Server to be ready to accept connections"""
        logger.info("Waiting for Code Server to be ready...")
        
        for attempt in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{self.config.port}",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.info("Code Server is ready!")
                            return
            except Exception:
                pass
            
            await asyncio.sleep(1)
            
            # Check if process is still running
            if self.process and self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"Code Server process died: {stderr.decode()}")
        
        raise TimeoutError(f"Code Server failed to start within {timeout} seconds")
    
    async def stop_code_server(self) -> Dict[str, Any]:
        """Stop the Code Server instance"""
        try:
            if not self.process:
                return {"status": "not_running"}
            
            # Send SIGTERM to the process group
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop gracefully
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()
            
            self.process = None
            self.is_ready = False
            
            logger.info(f"Code Server stopped for sandbox {self.sandbox_id}")
            
            return {"status": "stopped"}
            
        except Exception as e:
            logger.error(f"Error stopping Code Server: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def is_running(self) -> bool:
        """Check if Code Server process is running"""
        return self.process is not None and self.process.poll() is None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of Code Server"""
        if self.is_running():
            return {
                "status": "running",
                "ready": self.is_ready,
                "port": self.config.port,
                "url": f"http://localhost:{self.config.port}",
                "workspace": str(self.workspace_path),
                "pid": self.process.pid if self.process else None
            }
        else:
            return {
                "status": "stopped",
                "ready": False,
                "workspace": str(self.workspace_path)
            }
    
    async def create_project_structure(self, project_type: str, project_name: str) -> Dict[str, Any]:
        """Create a project structure based on type"""
        project_path = self.workspace_path / project_name
        project_path.mkdir(exist_ok=True)
        
        try:
            if project_type == "react":
                await self._create_react_project(project_path)
            elif project_type == "nextjs":
                await self._create_nextjs_project(project_path)
            elif project_type == "python":
                await self._create_python_project(project_path)
            elif project_type == "fastapi":
                await self._create_fastapi_project(project_path)
            else:
                await self._create_basic_project(project_path)
            
            return {
                "status": "success",
                "project_path": str(project_path),
                "project_type": project_type
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _create_react_project(self, project_path: Path):
        """Create a React project structure"""
        # Create package.json
        package_json = {
            "name": project_path.name,
            "version": "0.1.0",
            "private": True,
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
                "eject": "react-scripts eject"
            }
        }
        
        with open(project_path / "package.json", "w") as f:
            import json
            json.dump(package_json, f, indent=2)
        
        # Create basic React structure
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "public").mkdir(exist_ok=True)
        
        # Create App.js
        app_js = '''import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Welcome to React</h1>
        <p>Edit <code>src/App.js</code> and save to reload.</p>
      </header>
    </div>
  );
}

export default App;
'''
        with open(project_path / "src" / "App.js", "w") as f:
            f.write(app_js)
        
        # Create index.js
        index_js = '''import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
'''
        with open(project_path / "src" / "index.js", "w") as f:
            f.write(index_js)
    
    async def _create_nextjs_project(self, project_path: Path):
        """Create a Next.js project structure"""
        # Use npx to create Next.js project
        process = await asyncio.create_subprocess_exec(
            "npx", "create-next-app@latest", str(project_path), "--typescript", "--tailwind", "--eslint", "--app",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
    
    async def _create_python_project(self, project_path: Path):
        """Create a Python project structure"""
        # Create requirements.txt
        requirements = """fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
"""
        with open(project_path / "requirements.txt", "w") as f:
            f.write(requirements)
        
        # Create main.py
        main_py = '''"""
Simple Python application
"""

def main():
    print("Hello, World!")
    print("Welcome to your Python project!")

if __name__ == "__main__":
    main()
'''
        with open(project_path / "main.py", "w") as f:
            f.write(main_py)
    
    async def _create_fastapi_project(self, project_path: Path):
        """Create a FastAPI project structure"""
        # Create requirements.txt
        requirements = """fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
"""
        with open(project_path / "requirements.txt", "w") as f:
            f.write(requirements)
        
        # Create main.py
        main_py = '''from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="My FastAPI App", version="1.0.0")

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

@app.post("/items/")
async def create_item(item: Item):
    return item

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        with open(project_path / "main.py", "w") as f:
            f.write(main_py)
    
    async def _create_basic_project(self, project_path: Path):
        """Create a basic project structure"""
        # Create README.md
        readme = f"""# {project_path.name}

A new project created with Suna AI Code Server.

## Getting Started

This is a basic project structure. You can start building your application here.

## Project Structure

```
{project_path.name}/
├── README.md
├── src/
└── docs/
```

Happy coding! 🚀
"""
        with open(project_path / "README.md", "w") as f:
            f.write(readme)
        
        # Create basic directories
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "docs").mkdir(exist_ok=True)
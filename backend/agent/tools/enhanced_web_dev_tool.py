"""
Enhanced Web Development Tool with Code Server Integration
Extends the existing web dev tool with VS Code in browser capabilities
"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

from agentpress.tool import ToolResult, openapi_schema, usage_example
from .sb_web_dev_tool import SandboxWebDevTool
from ..sandbox.code_server_manager import CodeServerManager
from utils.logger import logger


class EnhancedWebDevTool(SandboxWebDevTool):
    """
    Enhanced Web Development Tool with integrated Code Server (VS Code in browser)
    Provides full-stack development capabilities with real-time editing
    """
    
    def __init__(self, project_id: str, thread_id: str, thread_manager):
        super().__init__(project_id, thread_id, thread_manager)
        self.code_server_manager: Optional[CodeServerManager] = None
        logger.info(f"Initialized Enhanced Web Dev Tool for project {project_id}")
    
    async def _ensure_code_server(self) -> CodeServerManager:
        """Ensure Code Server is available and running"""
        if not self.code_server_manager:
            self.code_server_manager = CodeServerManager(
                sandbox_id=self.project_id,
                workspace_path=self.workspace_path
            )
        
        if not self.code_server_manager.is_running():
            result = await self.code_server_manager.start_code_server()
            if result["status"] != "running":
                raise RuntimeError(f"Failed to start Code Server: {result.get('message', 'Unknown error')}")
        
        return self.code_server_manager
    
    @openapi_schema({
        "name": "create_project_with_ide",
        "description": "Create a new project and open it in VS Code browser IDE",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string", 
                    "description": "Name of the project to create"
                },
                "project_type": {
                    "type": "string",
                    "enum": ["react", "nextjs", "python", "fastapi", "basic"],
                    "description": "Type of project to create"
                },
                "open_in_ide": {
                    "type": "boolean", 
                    "description": "Whether to open the project in VS Code IDE",
                    "default": True
                },
                "install_dependencies": {
                    "type": "boolean",
                    "description": "Whether to automatically install project dependencies",
                    "default": True
                }
            },
            "required": ["project_name", "project_type"]
        }
    })
    @usage_example({
        "project_name": "my-react-app",
        "project_type": "react",
        "open_in_ide": True,
        "install_dependencies": True
    })
    async def create_project_with_ide(
        self, 
        project_name: str, 
        project_type: str,
        open_in_ide: bool = True,
        install_dependencies: bool = True
    ) -> ToolResult:
        """
        Create a new project with full project structure and open in VS Code IDE
        
        Args:
            project_name: Name of the project
            project_type: Type of project (react, nextjs, python, fastapi, basic)
            open_in_ide: Whether to open in VS Code IDE
            install_dependencies: Whether to install dependencies automatically
        
        Returns:
            ToolResult with project creation status and IDE information
        """
        try:
            logger.info(f"Creating {project_type} project '{project_name}' with IDE integration")
            
            # Ensure sandbox is ready
            await self._ensure_sandbox()
            
            # Create project structure
            if open_in_ide:
                # Ensure Code Server is running
                code_server = await self._ensure_code_server()
                
                # Create project using Code Server manager
                project_result = await code_server.create_project_structure(
                    project_type, project_name
                )
                
                if project_result["status"] != "success":
                    raise RuntimeError(f"Failed to create project: {project_result.get('message')}")
                
                # Install dependencies if requested
                if install_dependencies:
                    await self._install_project_dependencies(project_name, project_type)
                
                # Get Code Server status
                server_status = code_server.get_status()
                
                return ToolResult(
                    success=True,
                    result=f"✅ Project '{project_name}' created successfully and opened in VS Code IDE!\n\n"
                           f"📁 Project Type: {project_type}\n"
                           f"📂 Project Path: {project_result['project_path']}\n"
                           f"🌐 IDE URL: {server_status['url']}\n"
                           f"⚡ Dependencies: {'Installed' if install_dependencies else 'Not installed'}\n\n"
                           f"You can now start coding in your browser with full VS Code features!",
                    metadata={
                        "project_name": project_name,
                        "project_type": project_type,
                        "project_path": project_result["project_path"],
                        "ide_url": server_status["url"],
                        "ide_port": server_status["port"],
                        "workspace": server_status["workspace"],
                        "dependencies_installed": install_dependencies
                    }
                )
            else:
                # Create basic project without IDE
                result = await self._create_basic_project_structure(project_name, project_type)
                
                return ToolResult(
                    success=True,
                    result=f"✅ Project '{project_name}' created successfully!\n\n"
                           f"📁 Project Type: {project_type}\n"
                           f"📂 Project Path: {result['project_path']}\n\n"
                           f"Use 'open_project_in_ide' to open it in VS Code later.",
                    metadata=result
                )
                
        except Exception as e:
            logger.error(f"Failed to create project '{project_name}': {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to create project '{project_name}': {str(e)}"
            )
    
    @openapi_schema({
        "name": "open_project_in_ide",
        "description": "Open an existing project in VS Code browser IDE",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project to open (optional if opening workspace root)"
                }
            }
        }
    })
    async def open_project_in_ide(self, project_name: Optional[str] = None) -> ToolResult:
        """
        Open a project or workspace in VS Code browser IDE
        
        Args:
            project_name: Name of specific project to open, or None for workspace root
        
        Returns:
            ToolResult with IDE access information
        """
        try:
            logger.info(f"Opening {'project ' + project_name if project_name else 'workspace'} in IDE")
            
            # Ensure Code Server is running
            code_server = await self._ensure_code_server()
            server_status = code_server.get_status()
            
            if server_status["status"] != "running":
                raise RuntimeError("Code Server is not running")
            
            # If specific project requested, check if it exists
            if project_name:
                project_path = Path(self.workspace_path) / project_name
                if not project_path.exists():
                    return ToolResult(
                        success=False,
                        error=f"Project '{project_name}' does not exist in workspace"
                    )
            
            return ToolResult(
                success=True,
                result=f"🚀 {'Project ' + project_name if project_name else 'Workspace'} is now open in VS Code IDE!\n\n"
                       f"🌐 IDE URL: {server_status['url']}\n"
                       f"📂 Workspace: {server_status['workspace']}\n"
                       f"🔌 Port: {server_status['port']}\n\n"
                       f"You can now code with full VS Code features in your browser!",
                metadata={
                    "ide_url": server_status["url"],
                    "ide_port": server_status["port"],
                    "workspace": server_status["workspace"],
                    "project_name": project_name,
                    "status": "ready"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to open project in IDE: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to open project in IDE: {str(e)}"
            )
    
    @openapi_schema({
        "name": "list_workspace_projects",
        "description": "List all projects in the current workspace",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    })
    async def list_workspace_projects(self) -> ToolResult:
        """
        List all projects in the workspace with their types and status
        
        Returns:
            ToolResult with list of projects
        """
        try:
            workspace_path = Path(self.workspace_path)
            projects = []
            
            if workspace_path.exists():
                for item in workspace_path.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        project_info = {
                            "name": item.name,
                            "path": str(item),
                            "type": "unknown",
                            "has_package_json": False,
                            "has_requirements_txt": False,
                            "has_cargo_toml": False
                        }
                        
                        # Detect project type
                        if (item / "package.json").exists():
                            project_info["has_package_json"] = True
                            try:
                                with open(item / "package.json", "r") as f:
                                    package_data = json.load(f)
                                    deps = package_data.get("dependencies", {})
                                    if "next" in deps:
                                        project_info["type"] = "nextjs"
                                    elif "react" in deps:
                                        project_info["type"] = "react"
                                    else:
                                        project_info["type"] = "nodejs"
                            except:
                                project_info["type"] = "nodejs"
                        elif (item / "requirements.txt").exists():
                            project_info["has_requirements_txt"] = True
                            project_info["type"] = "python"
                        elif (item / "Cargo.toml").exists():
                            project_info["has_cargo_toml"] = True
                            project_info["type"] = "rust"
                        elif (item / "go.mod").exists():
                            project_info["type"] = "go"
                        
                        projects.append(project_info)
            
            # Format result
            if not projects:
                result_text = "📁 No projects found in workspace.\n\nUse 'create_project_with_ide' to create your first project!"
            else:
                result_text = f"📁 Found {len(projects)} project(s) in workspace:\n\n"
                for project in projects:
                    result_text += f"• **{project['name']}** ({project['type']})\n"
                    result_text += f"  📂 Path: {project['path']}\n\n"
            
            return ToolResult(
                success=True,
                result=result_text,
                metadata={
                    "projects": projects,
                    "workspace": str(workspace_path),
                    "total_projects": len(projects)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to list projects: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to list projects: {str(e)}"
            )
    
    @openapi_schema({
        "name": "install_project_dependencies",
        "description": "Install dependencies for a specific project",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project"
                }
            },
            "required": ["project_name"]
        }
    })
    async def install_project_dependencies(self, project_name: str) -> ToolResult:
        """
        Install dependencies for a specific project
        
        Args:
            project_name: Name of the project
        
        Returns:
            ToolResult with installation status
        """
        try:
            project_path = Path(self.workspace_path) / project_name
            
            if not project_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Project '{project_name}' does not exist"
                )
            
            # Detect project type and install dependencies
            project_type = await self._detect_project_type(project_path)
            await self._install_project_dependencies(project_name, project_type)
            
            return ToolResult(
                success=True,
                result=f"✅ Dependencies installed successfully for '{project_name}' ({project_type})",
                metadata={
                    "project_name": project_name,
                    "project_type": project_type,
                    "project_path": str(project_path)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to install dependencies for '{project_name}': {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to install dependencies: {str(e)}"
            )
    
    async def _install_project_dependencies(self, project_name: str, project_type: str):
        """Install dependencies based on project type"""
        project_path = Path(self.workspace_path) / project_name
        
        try:
            if project_type in ["react", "nextjs", "nodejs"]:
                # Install npm dependencies
                result = await self._execute_command(
                    f"cd {project_path} && npm install",
                    timeout=300  # 5 minutes timeout
                )
                if result.get("exit_code", 0) != 0:
                    raise RuntimeError(f"npm install failed: {result.get('stderr', 'Unknown error')}")
                    
            elif project_type == "python":
                # Install pip dependencies
                if (project_path / "requirements.txt").exists():
                    result = await self._execute_command(
                        f"cd {project_path} && pip install -r requirements.txt",
                        timeout=300
                    )
                    if result.get("exit_code", 0) != 0:
                        raise RuntimeError(f"pip install failed: {result.get('stderr', 'Unknown error')}")
                        
            elif project_type == "rust":
                # Build Rust project (downloads dependencies)
                result = await self._execute_command(
                    f"cd {project_path} && cargo build",
                    timeout=600  # 10 minutes timeout
                )
                if result.get("exit_code", 0) != 0:
                    raise RuntimeError(f"cargo build failed: {result.get('stderr', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Failed to install dependencies for {project_type} project: {str(e)}")
            raise
    
    async def _detect_project_type(self, project_path: Path) -> str:
        """Detect the type of project"""
        if (project_path / "package.json").exists():
            try:
                with open(project_path / "package.json", "r") as f:
                    package_data = json.load(f)
                    deps = package_data.get("dependencies", {})
                    if "next" in deps:
                        return "nextjs"
                    elif "react" in deps:
                        return "react"
                    else:
                        return "nodejs"
            except:
                return "nodejs"
        elif (project_path / "requirements.txt").exists():
            return "python"
        elif (project_path / "Cargo.toml").exists():
            return "rust"
        elif (project_path / "go.mod").exists():
            return "go"
        else:
            return "basic"
    
    async def _create_basic_project_structure(self, project_name: str, project_type: str) -> Dict[str, Any]:
        """Create basic project structure without Code Server"""
        project_path = Path(self.workspace_path) / project_name
        project_path.mkdir(exist_ok=True)
        
        # Create README
        readme_content = f"""# {project_name}

A {project_type} project created with Suna AI.

## Getting Started

This project was created using Suna AI's enhanced web development tools.

## Project Structure

```
{project_name}/
├── README.md
└── src/
```

Happy coding! 🚀
"""
        
        with open(project_path / "README.md", "w") as f:
            f.write(readme_content)
        
        # Create src directory
        (project_path / "src").mkdir(exist_ok=True)
        
        return {
            "project_name": project_name,
            "project_type": project_type,
            "project_path": str(project_path)
        }
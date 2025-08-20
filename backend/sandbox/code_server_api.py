"""
Code Server API endpoints for Suna AI
Provides REST API to manage Code Server instances
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel

from .code_server_manager import CodeServerManager
from utils.auth_utils import get_user_id
from utils.logger import logger

# Router for Code Server endpoints
router = APIRouter(prefix="/code-server", tags=["code-server"])

# Global storage for Code Server managers
code_servers: Dict[str, CodeServerManager] = {}


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project"""
    project_name: str
    project_type: str = "basic"  # react, nextjs, python, fastapi, basic
    auto_install_deps: bool = True


class CodeServerResponse(BaseModel):
    """Response model for Code Server operations"""
    status: str
    message: Optional[str] = None
    port: Optional[int] = None
    url: Optional[str] = None
    workspace: Optional[str] = None
    pid: Optional[int] = None


def get_code_server_manager(sandbox_id: str, workspace_path: str = "/workspace") -> CodeServerManager:
    """Get or create Code Server manager for a sandbox"""
    if sandbox_id not in code_servers:
        code_servers[sandbox_id] = CodeServerManager(sandbox_id, workspace_path)
    return code_servers[sandbox_id]


@router.post("/start/{sandbox_id}", response_model=CodeServerResponse)
async def start_code_server(
    sandbox_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Start Code Server for a specific sandbox
    
    Args:
        sandbox_id: Unique identifier for the sandbox
        background_tasks: FastAPI background tasks
        user_id: Authenticated user ID
    
    Returns:
        Code Server status and connection information
    """
    try:
        logger.info(f"Starting Code Server for sandbox {sandbox_id} (user: {user_id})")
        
        manager = get_code_server_manager(sandbox_id)
        
        # Check if already running
        if manager.is_running():
            status = manager.get_status()
            logger.info(f"Code Server already running for sandbox {sandbox_id}")
            return status
        
        # Start Code Server
        result = await manager.start_code_server()
        
        if result["status"] == "running":
            logger.info(f"Code Server started successfully for sandbox {sandbox_id}")
        else:
            logger.error(f"Failed to start Code Server for sandbox {sandbox_id}: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error starting Code Server for sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start Code Server: {str(e)}")


@router.post("/stop/{sandbox_id}", response_model=CodeServerResponse)
async def stop_code_server(
    sandbox_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Stop Code Server for a specific sandbox
    
    Args:
        sandbox_id: Unique identifier for the sandbox
        user_id: Authenticated user ID
    
    Returns:
        Stop operation status
    """
    try:
        logger.info(f"Stopping Code Server for sandbox {sandbox_id} (user: {user_id})")
        
        if sandbox_id not in code_servers:
            return {"status": "not_running", "message": "Code Server was not initialized"}
        
        manager = code_servers[sandbox_id]
        result = await manager.stop_code_server()
        
        # Remove from global storage if stopped successfully
        if result["status"] == "stopped":
            del code_servers[sandbox_id]
            logger.info(f"Code Server stopped and removed for sandbox {sandbox_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error stopping Code Server for sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop Code Server: {str(e)}")


@router.get("/status/{sandbox_id}", response_model=CodeServerResponse)
async def get_code_server_status(
    sandbox_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Get Code Server status for a specific sandbox
    
    Args:
        sandbox_id: Unique identifier for the sandbox
        user_id: Authenticated user ID
    
    Returns:
        Current status of Code Server
    """
    try:
        if sandbox_id not in code_servers:
            return {
                "status": "not_initialized",
                "message": "Code Server has not been initialized for this sandbox"
            }
        
        manager = code_servers[sandbox_id]
        status = manager.get_status()
        
        logger.debug(f"Code Server status for sandbox {sandbox_id}: {status['status']}")
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting Code Server status for sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/create-project/{sandbox_id}")
async def create_project(
    sandbox_id: str,
    request: ProjectCreateRequest,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Create a new project in the Code Server workspace
    
    Args:
        sandbox_id: Unique identifier for the sandbox
        request: Project creation parameters
        user_id: Authenticated user ID
    
    Returns:
        Project creation status and information
    """
    try:
        logger.info(f"Creating project '{request.project_name}' of type '{request.project_type}' for sandbox {sandbox_id}")
        
        manager = get_code_server_manager(sandbox_id)
        
        # Create project structure
        result = await manager.create_project_structure(
            request.project_type, 
            request.project_name
        )
        
        if result["status"] == "success":
            logger.info(f"Project '{request.project_name}' created successfully for sandbox {sandbox_id}")
            
            # Start Code Server if not running
            if not manager.is_running():
                server_result = await manager.start_code_server()
                result["code_server"] = server_result
            else:
                result["code_server"] = manager.get_status()
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating project for sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/list-projects/{sandbox_id}")
async def list_projects(
    sandbox_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    List all projects in the Code Server workspace
    
    Args:
        sandbox_id: Unique identifier for the sandbox
        user_id: Authenticated user ID
    
    Returns:
        List of projects in the workspace
    """
    try:
        manager = get_code_server_manager(sandbox_id)
        workspace_path = manager.workspace_path
        
        projects = []
        
        if workspace_path.exists():
            for item in workspace_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    project_info = {
                        "name": item.name,
                        "path": str(item),
                        "type": "unknown"
                    }
                    
                    # Detect project type
                    if (item / "package.json").exists():
                        with open(item / "package.json", "r") as f:
                            import json
                            package_data = json.load(f)
                            if "next" in package_data.get("dependencies", {}):
                                project_info["type"] = "nextjs"
                            elif "react" in package_data.get("dependencies", {}):
                                project_info["type"] = "react"
                            else:
                                project_info["type"] = "nodejs"
                    elif (item / "requirements.txt").exists():
                        project_info["type"] = "python"
                    elif (item / "Cargo.toml").exists():
                        project_info["type"] = "rust"
                    elif (item / "go.mod").exists():
                        project_info["type"] = "go"
                    
                    projects.append(project_info)
        
        return {
            "status": "success",
            "projects": projects,
            "workspace": str(workspace_path)
        }
        
    except Exception as e:
        logger.error(f"Error listing projects for sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.delete("/delete-project/{sandbox_id}/{project_name}")
async def delete_project(
    sandbox_id: str,
    project_name: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Delete a project from the Code Server workspace
    
    Args:
        sandbox_id: Unique identifier for the sandbox
        project_name: Name of the project to delete
        user_id: Authenticated user ID
    
    Returns:
        Deletion status
    """
    try:
        logger.info(f"Deleting project '{project_name}' for sandbox {sandbox_id}")
        
        manager = get_code_server_manager(sandbox_id)
        project_path = manager.workspace_path / project_name
        
        if not project_path.exists():
            return {
                "status": "error",
                "message": f"Project '{project_name}' does not exist"
            }
        
        # Remove project directory
        import shutil
        shutil.rmtree(project_path)
        
        logger.info(f"Project '{project_name}' deleted successfully for sandbox {sandbox_id}")
        
        return {
            "status": "success",
            "message": f"Project '{project_name}' deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting project '{project_name}' for sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for Code Server API
    
    Returns:
        API health status
    """
    return {
        "status": "healthy",
        "active_servers": len(code_servers),
        "servers": {
            sandbox_id: manager.get_status()["status"] 
            for sandbox_id, manager in code_servers.items()
        }
    }


@router.post("/restart/{sandbox_id}")
async def restart_code_server(
    sandbox_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Restart Code Server for a specific sandbox
    
    Args:
        sandbox_id: Unique identifier for the sandbox
        user_id: Authenticated user ID
    
    Returns:
        Restart operation status
    """
    try:
        logger.info(f"Restarting Code Server for sandbox {sandbox_id}")
        
        if sandbox_id in code_servers:
            manager = code_servers[sandbox_id]
            
            # Stop if running
            if manager.is_running():
                await manager.stop_code_server()
        
        # Create new manager and start
        manager = get_code_server_manager(sandbox_id)
        result = await manager.start_code_server()
        
        logger.info(f"Code Server restarted for sandbox {sandbox_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error restarting Code Server for sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to restart Code Server: {str(e)}")


# Cleanup function to be called on application shutdown
async def cleanup_code_servers():
    """Clean up all running Code Server instances"""
    logger.info("Cleaning up Code Server instances...")
    
    for sandbox_id, manager in code_servers.items():
        try:
            if manager.is_running():
                await manager.stop_code_server()
                logger.info(f"Stopped Code Server for sandbox {sandbox_id}")
        except Exception as e:
            logger.error(f"Error stopping Code Server for sandbox {sandbox_id}: {str(e)}")
    
    code_servers.clear()
    logger.info("Code Server cleanup completed")
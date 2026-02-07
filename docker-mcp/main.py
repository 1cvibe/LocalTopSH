"""
Docker MCP Server - управление Docker через Model Context Protocol
Позволяет агенту управлять контейнерами, образами, сетями и volumes
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import docker
import json
from datetime import datetime

app = FastAPI(title="Docker MCP Server", version="1.0")

# Docker client
client = docker.from_env()

# ============ Models ============

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: Dict[str, Any] = {}

class ToolResult(BaseModel):
    content: List[Dict[str, Any]]
    isError: bool = False

# ============ Tool Definitions ============

TOOLS = [
    {
        "name": "docker_ps",
        "description": "List running containers. Use all=true to include stopped containers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "all": {"type": "boolean", "description": "Include stopped containers", "default": False},
                "filters": {"type": "object", "description": "Filters as dict, e.g. {'name': 'myapp'}"}
            }
        }
    },
    {
        "name": "docker_images",
        "description": "List Docker images",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Filter by image name"}
            }
        }
    },
    {
        "name": "docker_run",
        "description": "Run a new container from an image",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Image name (e.g. nginx:latest)"},
                "name": {"type": "string", "description": "Container name"},
                "ports": {"type": "object", "description": "Port mapping, e.g. {'80/tcp': 8080}"},
                "environment": {"type": "object", "description": "Environment variables"},
                "volumes": {"type": "object", "description": "Volume mounts, e.g. {'/host/path': {'bind': '/container/path', 'mode': 'rw'}}"},
                "detach": {"type": "boolean", "description": "Run in background", "default": True},
                "remove": {"type": "boolean", "description": "Remove container when it exits", "default": False},
                "network": {"type": "string", "description": "Network to connect to"},
                "command": {"type": "string", "description": "Command to run in container"}
            },
            "required": ["image"]
        }
    },
    {
        "name": "docker_stop",
        "description": "Stop a running container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "timeout": {"type": "integer", "description": "Seconds to wait before killing", "default": 10}
            },
            "required": ["container"]
        }
    },
    {
        "name": "docker_start",
        "description": "Start a stopped container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"}
            },
            "required": ["container"]
        }
    },
    {
        "name": "docker_restart",
        "description": "Restart a container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "timeout": {"type": "integer", "description": "Seconds to wait before killing", "default": 10}
            },
            "required": ["container"]
        }
    },
    {
        "name": "docker_rm",
        "description": "Remove a container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "force": {"type": "boolean", "description": "Force removal of running container", "default": False},
                "v": {"type": "boolean", "description": "Remove associated volumes", "default": False}
            },
            "required": ["container"]
        }
    },
    {
        "name": "docker_logs",
        "description": "Get container logs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "tail": {"type": "integer", "description": "Number of lines from end", "default": 100},
                "since": {"type": "string", "description": "Show logs since timestamp (e.g. '2024-01-01' or '10m')"},
                "timestamps": {"type": "boolean", "description": "Show timestamps", "default": False}
            },
            "required": ["container"]
        }
    },
    {
        "name": "docker_exec",
        "description": "Execute a command in a running container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "command": {"type": "string", "description": "Command to execute"},
                "workdir": {"type": "string", "description": "Working directory"},
                "user": {"type": "string", "description": "User to run as"}
            },
            "required": ["container", "command"]
        }
    },
    {
        "name": "docker_inspect",
        "description": "Get detailed information about a container",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"}
            },
            "required": ["container"]
        }
    },
    {
        "name": "docker_pull",
        "description": "Pull an image from registry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Image name (e.g. nginx:latest)"}
            },
            "required": ["image"]
        }
    },
    {
        "name": "docker_build",
        "description": "Build an image from Dockerfile",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to build context (directory with Dockerfile)"},
                "tag": {"type": "string", "description": "Image tag (e.g. myapp:latest)"},
                "dockerfile": {"type": "string", "description": "Dockerfile name if not 'Dockerfile'"},
                "buildargs": {"type": "object", "description": "Build arguments"},
                "nocache": {"type": "boolean", "description": "Do not use cache", "default": False}
            },
            "required": ["path", "tag"]
        }
    },
    {
        "name": "docker_networks",
        "description": "List Docker networks",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "docker_volumes",
        "description": "List Docker volumes",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "docker_stats",
        "description": "Get container resource usage statistics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID (optional, all if not specified)"}
            }
        }
    },
    {
        "name": "docker_compose_up",
        "description": "Run docker compose up in a directory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to directory with docker-compose.yml"},
                "services": {"type": "array", "items": {"type": "string"}, "description": "Specific services to start"},
                "build": {"type": "boolean", "description": "Build images before starting", "default": False},
                "detach": {"type": "boolean", "description": "Run in background", "default": True}
            },
            "required": ["path"]
        }
    },
    {
        "name": "docker_compose_down",
        "description": "Run docker compose down in a directory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to directory with docker-compose.yml"},
                "volumes": {"type": "boolean", "description": "Remove volumes", "default": False},
                "rmi": {"type": "string", "description": "Remove images: 'all' or 'local'"}
            },
            "required": ["path"]
        }
    }
]

# ============ Tool Implementations ============

def docker_ps(all: bool = False, filters: dict = None) -> str:
    containers = client.containers.list(all=all, filters=filters)
    result = []
    for c in containers:
        result.append({
            "id": c.short_id,
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "status": c.status,
            "ports": c.ports,
            "created": c.attrs["Created"][:19]
        })
    return json.dumps(result, indent=2, ensure_ascii=False)

def docker_images(name: str = None) -> str:
    images = client.images.list(name=name)
    result = []
    for img in images:
        result.append({
            "id": img.short_id,
            "tags": img.tags,
            "size": f"{img.attrs['Size'] / 1024 / 1024:.1f} MB",
            "created": img.attrs["Created"][:19]
        })
    return json.dumps(result, indent=2, ensure_ascii=False)

def docker_run(image: str, name: str = None, ports: dict = None, environment: dict = None,
               volumes: dict = None, detach: bool = True, remove: bool = False,
               network: str = None, command: str = None) -> str:
    try:
        container = client.containers.run(
            image=image,
            name=name,
            ports=ports,
            environment=environment,
            volumes=volumes,
            detach=detach,
            remove=remove,
            network=network,
            command=command
        )
        if detach:
            return f"Container started: {container.name} ({container.short_id})"
        else:
            return container.decode('utf-8') if isinstance(container, bytes) else str(container)
    except docker.errors.ImageNotFound:
        return f"Error: Image '{image}' not found. Try docker_pull first."
    except docker.errors.APIError as e:
        return f"Error: {str(e)}"

def docker_stop(container: str, timeout: int = 10) -> str:
    try:
        c = client.containers.get(container)
        c.stop(timeout=timeout)
        return f"Container '{container}' stopped"
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_start(container: str) -> str:
    try:
        c = client.containers.get(container)
        c.start()
        return f"Container '{container}' started"
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_restart(container: str, timeout: int = 10) -> str:
    try:
        c = client.containers.get(container)
        c.restart(timeout=timeout)
        return f"Container '{container}' restarted"
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_rm(container: str, force: bool = False, v: bool = False) -> str:
    try:
        c = client.containers.get(container)
        c.remove(force=force, v=v)
        return f"Container '{container}' removed"
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_logs(container: str, tail: int = 100, since: str = None, timestamps: bool = False) -> str:
    try:
        c = client.containers.get(container)
        logs = c.logs(tail=tail, since=since, timestamps=timestamps)
        return logs.decode('utf-8', errors='replace')
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_exec(container: str, command: str, workdir: str = None, user: str = None) -> str:
    try:
        c = client.containers.get(container)
        result = c.exec_run(command, workdir=workdir, user=user)
        output = result.output.decode('utf-8', errors='replace')
        return f"Exit code: {result.exit_code}\n{output}"
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_inspect(container: str) -> str:
    try:
        c = client.containers.get(container)
        # Return relevant info, not full attrs
        info = {
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "created": c.attrs["Created"],
            "ports": c.ports,
            "mounts": [{"source": m["Source"], "destination": m["Destination"], "mode": m["Mode"]} 
                      for m in c.attrs["Mounts"]],
            "env": c.attrs["Config"]["Env"],
            "network": list(c.attrs["NetworkSettings"]["Networks"].keys()),
            "ip": next(iter(c.attrs["NetworkSettings"]["Networks"].values()), {}).get("IPAddress", "N/A")
        }
        return json.dumps(info, indent=2, ensure_ascii=False)
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_pull(image: str) -> str:
    try:
        img = client.images.pull(image)
        return f"Pulled: {img.tags[0] if img.tags else img.short_id}"
    except docker.errors.APIError as e:
        return f"Error: {str(e)}"

def docker_build(path: str, tag: str, dockerfile: str = None, buildargs: dict = None, nocache: bool = False) -> str:
    try:
        image, logs = client.images.build(
            path=path,
            tag=tag,
            dockerfile=dockerfile,
            buildargs=buildargs,
            nocache=nocache
        )
        log_output = []
        for log in logs:
            if 'stream' in log:
                log_output.append(log['stream'].strip())
        return f"Built: {tag}\n" + "\n".join(log_output[-20:])  # Last 20 lines
    except docker.errors.BuildError as e:
        return f"Build error: {str(e)}"

def docker_networks() -> str:
    networks = client.networks.list()
    result = []
    for net in networks:
        result.append({
            "id": net.short_id,
            "name": net.name,
            "driver": net.attrs["Driver"],
            "scope": net.attrs["Scope"]
        })
    return json.dumps(result, indent=2, ensure_ascii=False)

def docker_volumes() -> str:
    volumes = client.volumes.list()
    result = []
    for vol in volumes:
        result.append({
            "name": vol.name,
            "driver": vol.attrs["Driver"],
            "mountpoint": vol.attrs["Mountpoint"]
        })
    return json.dumps(result, indent=2, ensure_ascii=False)

def docker_stats(container: str = None) -> str:
    try:
        if container:
            containers = [client.containers.get(container)]
        else:
            containers = client.containers.list()
        
        result = []
        for c in containers:
            stats = c.stats(stream=False)
            
            # Calculate CPU %
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * 100 if system_delta > 0 else 0
            
            # Memory
            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            mem_percent = (mem_usage / mem_limit) * 100
            
            result.append({
                "name": c.name,
                "cpu": f"{cpu_percent:.2f}%",
                "memory": f"{mem_usage / 1024 / 1024:.1f}MB / {mem_limit / 1024 / 1024:.1f}MB ({mem_percent:.1f}%)"
            })
        
        return json.dumps(result, indent=2, ensure_ascii=False)
    except docker.errors.NotFound:
        return f"Error: Container '{container}' not found"

def docker_compose_up(path: str, services: list = None, build: bool = False, detach: bool = True) -> str:
    import subprocess
    cmd = ["docker", "compose", "-f", f"{path}/docker-compose.yml", "up"]
    if detach:
        cmd.append("-d")
    if build:
        cmd.append("--build")
    if services:
        cmd.extend(services)
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    output = result.stdout + result.stderr
    return output if output else "Compose up completed"

def docker_compose_down(path: str, volumes: bool = False, rmi: str = None) -> str:
    import subprocess
    cmd = ["docker", "compose", "-f", f"{path}/docker-compose.yml", "down"]
    if volumes:
        cmd.append("-v")
    if rmi:
        cmd.extend(["--rmi", rmi])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr
    return output if output else "Compose down completed"

# ============ Tool Router ============

TOOL_FUNCTIONS = {
    "docker_ps": docker_ps,
    "docker_images": docker_images,
    "docker_run": docker_run,
    "docker_stop": docker_stop,
    "docker_start": docker_start,
    "docker_restart": docker_restart,
    "docker_rm": docker_rm,
    "docker_logs": docker_logs,
    "docker_exec": docker_exec,
    "docker_inspect": docker_inspect,
    "docker_pull": docker_pull,
    "docker_build": docker_build,
    "docker_networks": docker_networks,
    "docker_volumes": docker_volumes,
    "docker_stats": docker_stats,
    "docker_compose_up": docker_compose_up,
    "docker_compose_down": docker_compose_down,
}

# ============ Endpoints ============

@app.get("/health")
async def health():
    try:
        client.ping()
        return {"status": "ok", "docker": "connected"}
    except:
        return {"status": "error", "docker": "disconnected"}

@app.post("/")
async def json_rpc(request: JsonRpcRequest):
    """JSON-RPC 2.0 endpoint for MCP"""
    
    if request.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": {"tools": TOOLS}
        }
    
    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        if tool_name not in TOOL_FUNCTIONS:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
            }
        
        try:
            result = TOOL_FUNCTIONS[tool_name](**arguments)
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {"code": -32601, "message": f"Method '{request.method}' not found"}
        }

# ============ REST API (альтернатива MCP) ============

@app.get("/containers")
async def list_containers(all: bool = False):
    return {"containers": json.loads(docker_ps(all=all))}

@app.get("/containers/{container}/logs")
async def get_logs(container: str, tail: int = 100):
    return {"logs": docker_logs(container, tail=tail)}

@app.post("/containers/{container}/start")
async def start_container(container: str):
    return {"result": docker_start(container)}

@app.post("/containers/{container}/stop")
async def stop_container(container: str):
    return {"result": docker_stop(container)}

@app.post("/containers/{container}/restart")
async def restart_container(container: str):
    return {"result": docker_restart(container)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)

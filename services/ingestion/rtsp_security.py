"""
IBVAP RTSP Security & Runtime Configuration Engine
===================================================
Production-Grade RTSP Security, Validation, and Credential Protection
Mandated for College CCTV and Real-World Field Validation (SIH26187)

Features:
1. SSRF Protection: Blocks cloud metadata IPs (169.254.169.254), multicast, loopback abuse,
   while permitting legitimate private enterprise/campus subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).
2. Path Traversal & Injection Prevention: Blocks shell metacharacters, directory traversal (../),
   null bytes, and parameter injections.
3. Credential Masking: Completely strips passwords from logging, API responses, terminal reports,
   and audit trails (e.g. rtsp://admin:***@192.168.1.100:554/ch0).
4. Direct RTSP Support: Enables college IP cameras to stream directly without requiring MediaMTX relay.
5. Runtime Registry: Secure local runtime configuration stored in git-ignored runtime vault.
"""

from __future__ import annotations

import os
import re
import socket
import json
import ipaddress
import urllib.parse
from typing import Optional, Dict, Any, Tuple, List
from pydantic import BaseModel, Field, field_validator
import structlog

logger = structlog.get_logger()

# Dangerous cloud metadata addresses to strictly block (SSRF protection)
BLOCKED_METADATA_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata",
    "instance-data",
    "169.254.169.250",
    "169.254.169.251",
    "169.254.169.252",
    "169.254.169.253",
}

# Dangerous characters for shell or path abuse
FORBIDDEN_CHARACTERS_REGEX = re.compile(r"[\x00-\x1f\x7f\x80-\xff;&|`$><\"'\\\n\r\t]")


class SecurityValidationError(ValueError):
    """Raised when an RTSP target fails security or SSRF validation."""
    pass


def mask_rtsp_url(url: Optional[str]) -> str:
    """
    Masks credentials in an RTSP/HTTP URL.
    Returns safe URL suitable for logging, frontend, and error messages.
    Example:
        rtsp://admin:mySecretPass123@192.168.1.50:554/live
        -> rtsp://admin:***@192.168.1.50:554/live
    """
    if not url:
        return ""
    
    url_str = str(url).strip()
    if not ("@" in url_str and ("://" in url_str)):
        return url_str
        
    try:
        parsed = urllib.parse.urlsplit(url_str)
        if parsed.password is not None:
            # Mask the password
            username = parsed.username or ""
            netloc = f"{username}:***@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            masked = urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
            return masked
        elif parsed.username is not None:
            # User present without password
            netloc = f"{parsed.username}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            masked = urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
            return masked
    except Exception:
        pass
        
    # Regex fallback
    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", url_str)


def build_rtsp_url(
    host: str,
    port: int = 554,
    stream_path: str = "/",
    username: Optional[str] = None,
    password: Optional[str] = None,
    scheme: str = "rtsp"
) -> str:
    """
    Constructs a canonical, properly encoded RTSP stream URL from components.
    """
    host_clean = host.strip()
    if not stream_path.startswith("/"):
        stream_path = f"/{stream_path}"
        
    port_str = f":{port}" if port and port != 554 else ""
    
    if username and password:
        # Quote credentials to safely handle characters while preserving security
        u = urllib.parse.quote(username, safe="")
        p = urllib.parse.quote(password, safe="")
        userinfo = f"{u}:{p}@"
    elif username:
        u = urllib.parse.quote(username, safe="")
        userinfo = f"{u}@"
    else:
        userinfo = ""
        
    return f"{scheme}://{userinfo}{host_clean}{port_str}{stream_path}"


def validate_rtsp_url(
    url: str,
    allow_private_ips: bool = True,
    allow_localhost: bool = True,
    allowed_schemes: Tuple[str, ...] = ("rtsp", "rtsps", "http", "https")
) -> Tuple[bool, Optional[str]]:
    """
    Validates an RTSP or IP camera URL against security policies.
    Returns (True, None) if safe, or (False, error_reason) if rejected.
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    url_str = url.strip()

    # 1. Shell Injection & Control Character Check
    if FORBIDDEN_CHARACTERS_REGEX.search(url_str):
        return False, "URL contains illegal control or shell metacharacters."

    # 2. Scheme check
    try:
        parsed = urllib.parse.urlsplit(url_str)
    except Exception as e:
        return False, f"Malformed URL syntax: {e}"

    if not parsed.scheme or parsed.scheme.lower() not in allowed_schemes:
        return False, f"Invalid scheme '{parsed.scheme}'. Allowed: {', '.join(allowed_schemes)}"

    # 3. Hostname check
    host = parsed.hostname
    if not host:
        return False, "URL missing valid hostname or IP address."

    host_lower = host.lower().strip("[]")

    # SSRF: Block cloud metadata services
    if host_lower in BLOCKED_METADATA_HOSTS:
        return False, f"SSRF Protection: Access to cloud metadata host '{host_lower}' is blocked."

    # Check IP address safety
    try:
        ip = ipaddress.ip_address(host_lower)
        
        # Block cloud metadata subnet 169.254.0.0/16
        if ip in ipaddress.ip_network("169.254.0.0/16"):
            return False, f"SSRF Protection: Link-local metadata address '{ip}' is blocked."

        # Block multicast (224.0.0.0/4)
        if ip.is_multicast:
            return False, "Multicast IP addresses are not permitted."

        # Block loopback if disallowed
        if ip.is_loopback and not allow_localhost:
            return False, "Loopback addresses (127.0.0.1) are not permitted."

        # Verify private IPs are permitted for college LAN cameras
        if ip.is_private and not allow_private_ips:
            return False, "Private LAN IP addresses are restricted."

    except ValueError:
        # Not a raw IP; it's a domain/hostname
        if "metadata" in host_lower:
            return False, "SSRF Protection: Hostname contains blocked keyword 'metadata'."

    # 4. Port Check
    try:
        port = parsed.port
    except ValueError as e:
        return False, f"Port out of valid range: {e}"

    if port is not None:
        if port < 1 or port > 65535:
            return False, f"Port {port} out of valid range (1-65535)."

    # 5. Path Abuse & Directory Traversal Check
    path = parsed.path
    if ".." in path or "%2e%2e" in path.lower():
        return False, "Directory traversal ('..') detected in stream path."
    if "\x00" in path or "%00" in path:
        return False, "Null byte injection detected in stream path."

    return True, None


class RTSPCameraConfig(BaseModel):
    """
    Standardized configuration for direct real-world IP CCTV cameras.
    Guarantees credential security and schema uniformity.
    """
    camera_id: str = Field(..., description="Unique ID for camera (e.g. COLLEGE-CAM-01)")
    name: str = Field(default="College IP Camera", description="Friendly descriptive name")
    host: str = Field(..., description="IP address or hostname of camera")
    port: int = Field(default=554, ge=1, le=65535, description="RTSP port (default 554)")
    stream_path: str = Field(default="/Streaming/Channels/101", description="Stream path on camera")
    username: Optional[str] = Field(default=None, description="Camera auth username")
    password: Optional[str] = Field(default=None, description="Camera auth password")
    scenario: str = Field(default="zone_intrusion", description="Default operational scenario")
    fps_limit: int = Field(default=25, ge=1, le=60, description="Target capture FPS")
    reconnect_delay_seconds: float = Field(default=2.0, ge=0.5, le=30.0, description="Reconnect retry delay")
    max_reconnect_attempts: int = Field(default=0, ge=0, description="Max reconnects (0 = infinite auto-retry)")
    buffer_size: int = Field(default=15, ge=1, le=100, description="Zero-lag ring buffer depth")
    scheme: str = Field(default="rtsp", description="Protocol scheme (rtsp or rtsps)")

    @field_validator("camera_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        clean = v.strip().upper()
        if not re.match(r"^[A-Z0-9_-]{3,32}$", clean):
            raise ValueError("camera_id must be 3-32 alphanumeric characters, dashes, or underscores.")
        return clean

    @field_validator("stream_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        clean = v.strip()
        if not clean.startswith("/"):
            clean = "/" + clean
        if ".." in clean:
            raise ValueError("Path traversal ('..') not permitted in stream path.")
        return clean

    def get_connection_url(self) -> str:
        """Constructs unmasked URL with credentials for OpenCV/FFmpeg connection."""
        return build_rtsp_url(
            host=self.host,
            port=self.port,
            stream_path=self.stream_path,
            username=self.username,
            password=self.password,
            scheme=self.scheme
        )

    def get_masked_url(self) -> str:
        """Constructs safe URL with password masked for UI, logging, and reports."""
        unmasked = self.get_connection_url()
        return mask_rtsp_url(unmasked)

    def to_runtime_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Serializes configuration, omitting secrets by default."""
        data = {
            "camera_id": self.camera_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "stream_path": self.stream_path,
            "username": self.username,
            "scenario": self.scenario,
            "fps_limit": self.fps_limit,
            "reconnect_delay_seconds": self.reconnect_delay_seconds,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "buffer_size": self.buffer_size,
            "scheme": self.scheme,
            "masked_url": self.get_masked_url(),
        }
        if include_secrets:
            data["password"] = self.password
            data["connection_url"] = self.get_connection_url()
        return data


class RTSPRuntimeRegistry:
    """
    Manages live runtime camera configurations in a local git-ignored JSON vault.
    Allows runtime configuration of college IP cameras without hardcoded IPs.
    """
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.config_path = os.path.join(project_root, "configs", "cameras_runtime.json")
        else:
            self.config_path = config_path

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load cameras_runtime.json", error=str(e))
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register_camera(self, config: RTSPCameraConfig) -> None:
        """Saves camera configuration to local runtime registry."""
        data = self._load()
        data[config.camera_id] = config.to_runtime_dict(include_secrets=True)
        self._save(data)
        logger.info("Registered RTSP camera", camera_id=config.camera_id, url=config.get_masked_url())

    def get_camera(self, camera_id: str) -> Optional[RTSPCameraConfig]:
        """Retrieves camera configuration by ID."""
        data = self._load()
        cam_data = data.get(camera_id)
        if not cam_data:
            return None
        return RTSPCameraConfig(
            camera_id=cam_data["camera_id"],
            name=cam_data.get("name", "Camera"),
            host=cam_data["host"],
            port=cam_data.get("port", 554),
            stream_path=cam_data.get("stream_path", "/"),
            username=cam_data.get("username"),
            password=cam_data.get("password"),
            scenario=cam_data.get("scenario", "zone_intrusion"),
            fps_limit=cam_data.get("fps_limit", 25),
            reconnect_delay_seconds=cam_data.get("reconnect_delay_seconds", 2.0),
            max_reconnect_attempts=cam_data.get("max_reconnect_attempts", 0),
            buffer_size=cam_data.get("buffer_size", 15),
            scheme=cam_data.get("scheme", "rtsp"),
        )

    def get_connection_url(self, camera_id: str) -> Optional[str]:
        """Returns the full unmasked connection URL for worker process execution."""
        cam = self.get_camera(camera_id)
        return cam.get_connection_url() if cam else None

    def list_cameras(self, mask_credentials: bool = True) -> List[Dict[str, Any]]:
        """Returns list of all registered cameras, with masked credentials by default."""
        data = self._load()
        result = []
        for cam_id, details in data.items():
            if mask_credentials:
                safe_copy = dict(details)
                safe_copy.pop("password", None)
                safe_copy.pop("connection_url", None)
                result.append(safe_copy)
            else:
                result.append(details)
        return result

    def delete_camera(self, camera_id: str) -> bool:
        """Removes a camera from runtime registry."""
        data = self._load()
        if camera_id in data:
            del data[camera_id]
            self._save(data)
            logger.info("Deleted RTSP camera from registry", camera_id=camera_id)
            return True
        return False


def probe_rtsp_target(host: str, port: int = 554, timeout_seconds: float = 2.0) -> Dict[str, Any]:
    """
    Fast pre-flight physical reachability probe for college cameras.
    Tests TCP socket connectivity without hanging or starting heavy AI pipelines.
    """
    clean_host = host.strip("[]").strip()
    result = {
        "host": clean_host,
        "port": port,
        "tcp_reachable": False,
        "latency_ms": 0.0,
        "error": None
    }
    
    start_time = socket.getdefaulttimeout()
    import time
    t0 = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_seconds)
        conn_res = sock.connect_ex((clean_host, port))
        t1 = time.time()
        if conn_res == 0:
            result["tcp_reachable"] = True
            result["latency_ms"] = round((t1 - t0) * 1000.0, 2)
        else:
            result["error"] = f"Socket connect_ex returned errno {conn_res}"
        sock.close()
    except Exception as e:
        result["error"] = str(e)
        
    return result

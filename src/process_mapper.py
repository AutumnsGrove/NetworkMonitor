"""
Process mapping for network connections.

Maps network connections (IP:port) to processes/applications.
Uses lsof on macOS to identify which process owns each connection.
"""
import subprocess
import logging
import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path

from src.utils import get_process_name_from_path
from src.config_manager import get_config


logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Information about a process."""
    pid: int
    name: str
    path: str
    bundle_id: Optional[str] = None
    remote_address: Optional[str] = None  # Remote IP:port from lsof (e.g., "192.168.1.1:443")


class ProcessMapper:
    """
    Maps network connections to processes.

    Uses lsof to determine which process owns a connection.
    """

    def __init__(self):
        """Initialize process mapper."""
        self.config = get_config()
        self.connection_cache: Dict[Tuple[str, int], ProcessInfo] = {}
        logger.info("Initialized ProcessMapper")

    def get_process_for_connection(
        self,
        local_ip: str,
        local_port: int
    ) -> Optional[ProcessInfo]:
        """
        Get process information for a connection.

        Args:
            local_ip: Local IP address
            local_port: Local port number

        Returns:
            ProcessInfo if found, None otherwise
        """
        # Check cache first
        key = (local_ip, local_port)
        if key in self.connection_cache:
            return self.connection_cache[key]

        # Use lsof to find the process
        process_info = self._lsof_lookup(local_port)
        if process_info:
            self.connection_cache[key] = process_info
            return process_info

        return None

    def _lsof_lookup(self, port: int) -> Optional[ProcessInfo]:
        """
        Use lsof to find process owning a port.

        Args:
            port: Port number to lookup

        Returns:
            ProcessInfo if found, None otherwise
        """
        try:
            # Run lsof to find process listening/connected on port
            cmd = ['lsof', '-i', f':{port}', '-n', '-P', '-F', 'pcn']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.process_mapper.ps_timeout_seconds
            )

            if result.returncode != 0:
                return None

            # Parse lsof output
            # Format: p<pid>\nc<command>\nn<name>
            lines = result.stdout.strip().split('\n')
            pid = None
            command = None
            path = None

            for line in lines:
                if not line:
                    continue

                if line.startswith('p'):
                    pid = int(line[1:])
                elif line.startswith('c'):
                    command = line[1:]
                elif line.startswith('n'):
                    # This is the network connection info
                    pass

            if pid and command:
                # Get full path using ps
                path = self._get_process_path(pid)
                bundle_id = self._get_bundle_id(path) if path else None

                return ProcessInfo(
                    pid=pid,
                    name=command,
                    path=path or command,
                    bundle_id=bundle_id
                )

        except subprocess.TimeoutExpired:
            logger.warning(f"lsof timeout for port {port}")
        except Exception as e:
            logger.debug(f"Error in lsof lookup: {e}")

        return None

    def _get_process_path(self, pid: int) -> Optional[str]:
        """
        Get full path for a process.

        Args:
            pid: Process ID

        Returns:
            Full path to process executable
        """
        try:
            cmd = ['ps', '-p', str(pid), '-o', 'comm=']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.process_mapper.ps_timeout_seconds
            )

            if result.returncode == 0:
                return result.stdout.strip()

        except Exception as e:
            logger.debug(f"Error getting process path: {e}")

        return None

    def _get_bundle_id(self, path: str) -> Optional[str]:
        """
        Get macOS bundle ID for an application.

        Args:
            path: Path to application

        Returns:
            Bundle ID if found (e.g., com.apple.Safari)
        """
        try:
            # Check if it's a .app bundle
            if '.app' in path:
                # Extract .app path
                app_path = path.split('.app')[0] + '.app'

                # Read Info.plist
                plist_path = Path(app_path) / 'Contents' / 'Info.plist'
                if plist_path.exists():
                    # Use plutil to read CFBundleIdentifier
                    cmd = [
                        'plutil',
                        '-extract',
                        'CFBundleIdentifier',
                        'raw',
                        str(plist_path)
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.config.process_mapper.bundle_timeout_seconds
                    )

                    if result.returncode == 0:
                        return result.stdout.strip()

        except Exception as e:
            logger.debug(f"Error getting bundle ID: {e}")

        return None

    def get_all_network_processes(self) -> List[ProcessInfo]:
        """
        Get all processes with network connections.

        Returns:
            List of ProcessInfo for all processes with network activity
        """
        processes = []

        try:
            # Run lsof for all network connections
            # Format: p=PID, c=command, n=network address
            cmd = ['lsof', '-i', '-n', '-P', '-F', 'pcn']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.process_mapper.lsof_timeout_seconds
            )

            if result.returncode != 0:
                return []

            # Parse output - lsof -F format is field-per-line
            # p<pid>, c<command>, n<network_addr>
            lines = result.stdout.strip().split('\n')
            current_pid = None
            current_name = None
            current_path = None
            current_bundle = None

            for line in lines:
                if not line:
                    continue

                if line.startswith('p'):
                    # New process - commit previous if exists
                    current_pid = int(line[1:])
                    current_name = None
                    current_path = None
                    current_bundle = None
                elif line.startswith('c'):
                    current_name = line[1:]
                elif line.startswith('n'):
                    # Network address - create ProcessInfo for each connection
                    if current_pid and current_name:
                        network_addr = line[1:]

                        # Extract remote address from network string
                        # Format examples:
                        # *:7000 (listening)
                        # 192.168.1.1:443->192.168.1.2:54321 (established)
                        # [::1]:8080->[::1]:54322 (IPv6)
                        remote_addr = None
                        if '->' in network_addr:
                            # Extract remote part after ->
                            remote_part = network_addr.split('->')[1]
                            # Clean up IPv6 brackets if present
                            remote_addr = remote_part.strip('[]')

                        # Get process info (cache these to avoid repeated lookups)
                        if not current_path:
                            current_path = self._get_process_path(current_pid)
                        if not current_bundle and current_path:
                            current_bundle = self._get_bundle_id(current_path)

                        processes.append(ProcessInfo(
                            pid=current_pid,
                            name=current_name,
                            path=current_path or current_name,
                            bundle_id=current_bundle,
                            remote_address=remote_addr
                        ))

        except Exception as e:
            logger.error(f"Error getting network processes: {e}", exc_info=True)

        return processes

    def clear_cache(self) -> None:
        """Clear the connection cache."""
        self.connection_cache.clear()
        logger.debug("Cleared process mapper cache")

    def refresh_cache(self) -> int:
        """
        Refresh cache with current network processes.

        Returns:
            Number of processes cached
        """
        self.clear_cache()
        # This could be enhanced to pre-populate cache
        # For now, cache is populated on-demand
        return 0


class MacOSProcessHelper:
    """
    Helper for macOS-specific process operations.

    Provides utilities for getting process information using
    macOS-specific tools and APIs.
    """

    @staticmethod
    def get_process_info_by_pid(pid: int) -> Optional[ProcessInfo]:
        """
        Get process information by PID.

        Args:
            pid: Process ID

        Returns:
            ProcessInfo if found
        """
        try:
            # Get process name
            cmd = ['ps', '-p', str(pid), '-o', 'comm=']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.process_mapper.ps_timeout_seconds
            )

            if result.returncode != 0:
                return None

            path = result.stdout.strip()
            name = get_process_name_from_path(path)

            # Try to get bundle ID
            bundle_id = None
            if '.app' in path:
                mapper = ProcessMapper()
                bundle_id = mapper._get_bundle_id(path)

            return ProcessInfo(
                pid=pid,
                name=name,
                path=path,
                bundle_id=bundle_id
            )

        except Exception as e:
            logger.debug(f"Error getting process info for PID {pid}: {e}")
            return None

    @staticmethod
    def get_listening_ports() -> Dict[int, ProcessInfo]:
        """
        Get all listening ports and their processes.

        Returns:
            Dictionary mapping port number to ProcessInfo
        """
        port_map = {}

        try:
            # Get all listening TCP ports
            cmd = ['lsof', '-i', 'TCP', '-s', 'TCP:LISTEN', '-n', '-P', '-F', 'pcn']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.process_mapper.lsof_timeout_seconds
            )

            if result.returncode != 0:
                return {}

            lines = result.stdout.strip().split('\n')
            current = {}

            for line in lines:
                if not line:
                    if current and 'pid' in current and 'port' in current:
                        # Create ProcessInfo
                        path = ProcessMapper()._get_process_path(current['pid'])
                        name = current.get('name', 'unknown')
                        bundle_id = ProcessMapper()._get_bundle_id(path) if path else None

                        port_map[current['port']] = ProcessInfo(
                            pid=current['pid'],
                            name=name,
                            path=path or name,
                            bundle_id=bundle_id
                        )
                    current = {}
                    continue

                if line.startswith('p'):
                    current['pid'] = int(line[1:])
                elif line.startswith('c'):
                    current['name'] = line[1:]
                elif line.startswith('n'):
                    # Parse network info to extract port
                    # Format: *:PORT or IP:PORT
                    match = re.search(r':(\d+)', line)
                    if match:
                        current['port'] = int(match.group(1))

        except Exception as e:
            logger.error(f"Error getting listening ports: {e}", exc_info=True)

        return port_map

"""
Network packet capture using scapy.

Captures network packets to track application-level usage and domain access.
Requires sudo/root permissions for packet sniffing.

NOTE: This module is DEPRECATED. Use NetTopMonitor for simpler, more reliable
per-process network monitoring on macOS.
"""
import logging
import subprocess
from datetime import datetime
from typing import Dict, Set, Optional, Tuple, Callable, List
from collections import defaultdict
import asyncio
from dataclasses import dataclass, field

try:
    from scapy.all import (
        sniff, IP, IPv6, TCP, UDP, DNS, DNSQR, DNSRR,
        get_if_list, conf
    )
    # Try to import TLS (may not be available in all scapy versions)
    try:
        from scapy.layers.tls.all import TLS
        TLS_AVAILABLE = True
    except ImportError:
        TLS = None
        TLS_AVAILABLE = False
        logging.info("TLS layer not available in scapy - HTTPS SNI extraction disabled")

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    TLS = None
    TLS_AVAILABLE = False
    logging.warning("Scapy not available - packet capture will not work")


logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Track statistics for a connection."""
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    domains: Set[str] = field(default_factory=set)


@dataclass
class PacketInfo:
    """Information extracted from a packet."""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str  # TCP or UDP
    packet_size: int
    direction: str  # 'sent' or 'received'
    timestamp: datetime
    domain: Optional[str] = None


class NetworkCapture:
    """
    Network packet capture engine.

    Captures packets using scapy and extracts:
    - Source/destination IPs and ports
    - Packet sizes
    - DNS queries
    - TLS SNI (Server Name Indication) for HTTPS domains
    """

    def __init__(
        self,
        interface: Optional[str] = None,
        capture_filter: str = "tcp or udp",
    ):
        """
        Initialize network capture.

        Args:
            interface: Network interface to capture on (None = all interfaces)
            capture_filter: BPF filter for packet capture
        """
        if not SCAPY_AVAILABLE:
            raise RuntimeError("Scapy is required for packet capture")

        self.interface = interface
        self.capture_filter = capture_filter
        self.running = False
        self.stats: Dict[Tuple[str, int], ConnectionStats] = defaultdict(ConnectionStats)
        self.dns_cache: Dict[str, str] = {}  # IP -> domain mapping
        self.packet_callback: Optional[Callable] = None
        self._capture_task: Optional[asyncio.Task] = None

        logger.info(f"Initialized NetworkCapture on interface: {interface or 'all'}")

    def start(self, packet_callback: Optional[Callable] = None) -> None:
        """
        Start packet capture.

        Args:
            packet_callback: Optional callback function called for each packet
        """
        if self.running:
            logger.warning("Capture already running")
            return

        self.running = True
        self.packet_callback = packet_callback

        logger.info("Starting packet capture")

        try:
            # Start sniffing in a separate thread (scapy handles this)
            sniff(
                iface=self.interface,
                filter=self.capture_filter,
                prn=self._process_packet,
                store=False,  # Don't store packets in memory
                stop_filter=lambda _: not self.running
            )
        except Exception as e:
            logger.error(f"Error starting packet capture: {e}", exc_info=True)
            self.running = False

    def stop(self) -> None:
        """Stop packet capture."""
        if not self.running:
            return

        logger.info("Stopping packet capture")
        self.running = False

    def _process_packet(self, packet) -> None:
        """
        Process a captured packet.

        Extracts relevant information and updates statistics.
        """
        try:
            # Extract DNS queries first (for domain mapping)
            if packet.haslayer(DNS):
                self._process_dns(packet)

            # Extract TLS SNI (for HTTPS domains)
            if TLS and packet.haslayer(TLS):
                self._process_tls(packet)

            # Extract general packet info
            packet_info = self._extract_packet_info(packet)
            if packet_info:
                # Update statistics
                self._update_stats(packet_info)

                # Call callback if provided
                if self.packet_callback:
                    self.packet_callback(packet_info)

        except Exception as e:
            logger.debug(f"Error processing packet: {e}")

    def _process_dns(self, packet) -> None:
        """Extract DNS query information."""
        try:
            if packet.haslayer(DNSQR):
                # DNS query
                query_name = packet[DNSQR].qname.decode('utf-8', errors='ignore').rstrip('.')
                logger.debug(f"DNS query: {query_name}")

            if packet.haslayer(DNSRR):
                # DNS response
                for i in range(packet[DNS].ancount):
                    dnsrr = packet[DNSRR][i] if i < len(packet[DNSRR]) else packet[DNSRR]
                    if dnsrr.type == 1:  # A record (IPv4)
                        domain = dnsrr.rrname.decode('utf-8', errors='ignore').rstrip('.')
                        ip = dnsrr.rdata
                        self.dns_cache[ip] = domain
                        logger.debug(f"DNS mapping: {ip} -> {domain}")
                    elif dnsrr.type == 28:  # AAAA record (IPv6)
                        domain = dnsrr.rrname.decode('utf-8', errors='ignore').rstrip('.')
                        ip = dnsrr.rdata
                        self.dns_cache[ip] = domain
                        logger.debug(f"DNS mapping (IPv6): {ip} -> {domain}")

        except Exception as e:
            logger.debug(f"Error processing DNS: {e}")

    def _process_tls(self, packet) -> None:
        """Extract TLS SNI (Server Name Indication)."""
        try:
            # TLS SNI extraction is complex in scapy
            # This is a simplified version - may need enhancement
            if hasattr(packet[TLS], 'msg') and packet[TLS].msg:
                # Look for ClientHello
                for msg in packet[TLS].msg:
                    if hasattr(msg, 'ext') and msg.ext:
                        for ext in msg.ext:
                            if hasattr(ext, 'servernames') and ext.servernames:
                                for servername in ext.servernames:
                                    if hasattr(servername, 'servername'):
                                        sni = servername.servername.decode('utf-8', errors='ignore')
                                        # Map IP to domain
                                        if packet.haslayer(IP):
                                            ip = packet[IP].dst
                                            self.dns_cache[ip] = sni
                                            logger.debug(f"TLS SNI: {ip} -> {sni}")

        except Exception as e:
            logger.debug(f"Error processing TLS: {e}")

    def _extract_packet_info(self, packet) -> Optional[PacketInfo]:
        """Extract relevant information from packet."""
        try:
            # Determine if IPv4 or IPv6
            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                packet_size = len(packet)
            elif packet.haslayer(IPv6):
                src_ip = packet[IPv6].src
                dst_ip = packet[IPv6].dst
                packet_size = len(packet)
            else:
                return None

            # Get transport layer info
            src_port = 0
            dst_port = 0
            protocol = "UNKNOWN"

            if packet.haslayer(TCP):
                src_port = packet[TCP].sport
                dst_port = packet[TCP].dport
                protocol = "TCP"
            elif packet.haslayer(UDP):
                src_port = packet[UDP].sport
                dst_port = packet[UDP].dport
                protocol = "UDP"
            else:
                return None

            # Determine direction (simplified - assumes local machine is source for sent)
            # In real implementation, would need to check if src_ip is local
            direction = "sent"  # Placeholder

            # Look up domain from DNS cache
            domain = self.dns_cache.get(dst_ip)

            return PacketInfo(
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                packet_size=packet_size,
                direction=direction,
                timestamp=datetime.now(),
                domain=domain
            )

        except Exception as e:
            logger.debug(f"Error extracting packet info: {e}")
            return None

    def _update_stats(self, packet_info: PacketInfo) -> None:
        """Update connection statistics."""
        # Use (dst_ip, dst_port) as connection key
        key = (packet_info.dst_ip, packet_info.dst_port)
        stats = self.stats[key]

        if packet_info.direction == "sent":
            stats.bytes_sent += packet_info.packet_size
            stats.packets_sent += 1
        else:
            stats.bytes_received += packet_info.packet_size
            stats.packets_received += 1

        stats.last_seen = packet_info.timestamp

        if packet_info.domain:
            stats.domains.add(packet_info.domain)

    def get_stats(self) -> Dict[Tuple[str, int], ConnectionStats]:
        """Get current connection statistics."""
        return dict(self.stats)

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.stats.clear()
        logger.debug("Reset capture statistics")

    def get_dns_cache(self) -> Dict[str, str]:
        """Get DNS cache (IP -> domain mapping)."""
        return dict(self.dns_cache)

    @staticmethod
    def list_interfaces() -> list:
        """List available network interfaces."""
        if not SCAPY_AVAILABLE:
            return []
        return get_if_list()

    @staticmethod
    def get_default_interface() -> Optional[str]:
        """Get the default network interface."""
        if not SCAPY_AVAILABLE:
            return None

        # Get default interface from scapy config
        return conf.iface if hasattr(conf, 'iface') else None


class SimpleNetworkMonitor:
    """
    Simplified network monitor using lsof as fallback.

    Used when packet sniffing is not available or desired.
    Less accurate but doesn't require sudo.
    """

    def __init__(self):
        """Initialize simple network monitor."""
        self.running = False
        logger.info("Initialized SimpleNetworkMonitor (lsof-based)")

    async def start(self) -> None:
        """Start monitoring using lsof."""
        if self.running:
            return

        self.running = True
        logger.info("Starting lsof-based network monitoring")

        # This would use subprocess to run lsof periodically
        # Simplified placeholder for now
        raise NotImplementedError("lsof-based monitoring not yet implemented")

    async def stop(self) -> None:
        """Stop monitoring."""
        self.running = False
        logger.info("Stopped lsof-based monitoring")


# Convenience functions

def create_capture(
    interface: Optional[str] = None,
    use_simple: bool = False
) -> 'NetworkCapture | SimpleNetworkMonitor':
    """
    Create appropriate network capture instance.

    Args:
        interface: Network interface (None = all)
        use_simple: Use simple lsof-based monitor instead of packet sniffing

    Returns:
        NetworkCapture or SimpleNetworkMonitor instance
    """
    if use_simple or not SCAPY_AVAILABLE:
        return SimpleNetworkMonitor()

    return NetworkCapture(interface=interface)


def check_capture_permissions() -> bool:
    """
    Check if we have permissions for packet capture.

    Returns:
        True if we can capture packets (running as root)
    """
    import os
    return os.geteuid() == 0


class NetTopMonitor:
    """
    Network monitoring using macOS nettop command.

    Simpler and more reliable than packet capture - uses native macOS tool
    that shows per-process network usage without requiring sudo.

    nettop provides direct per-process byte counts in CSV format:
        process_name.pid,bytes_in,bytes_out

    Advantages over scapy:
    - No sudo required
    - Per-process data built-in (no IP:port mapping needed)
    - Native macOS tool (always available)
    - Simple CSV output
    - Delta mode shows bytes since last call
    """

    def __init__(self):
        """Initialize nettop monitor."""
        self.running = False
        logger.info("Initialized NetTopMonitor (macOS nettop-based)")

    async def sample(self) -> List[Dict]:
        """
        Sample network usage using nettop.

        Runs nettop for 1 sample in CSV format to get per-process byte counts.

        Returns:
            List of process stats with bytes_in/bytes_out
            Example: [
                {'process_name': 'Safari', 'pid': 1234, 'bytes_in': 1024, 'bytes_out': 512},
                ...
            ]
        """
        try:
            # Run nettop for 1 sample, CSV format, process summaries only
            # -P: Process mode
            # -L 1: Sample once
            # -J bytes_in,bytes_out: Only show these columns
            # -x: No header
            cmd = ['nettop', '-P', '-L', '1', '-J', 'bytes_in,bytes_out']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.error(f"nettop failed with return code {result.returncode}: {result.stderr}")
                return []

            # Parse CSV output
            processes = []
            lines = result.stdout.strip().split('\n')

            # Skip header line if present
            start_idx = 1 if lines and lines[0].startswith(',bytes_in,bytes_out') else 0

            for line in lines[start_idx:]:
                if not line or not line.strip():
                    continue

                parts = line.split(',')
                if len(parts) < 3:
                    continue

                # Parse process_name.pid format
                process_info = parts[0]
                if not process_info or '.' not in process_info:
                    continue

                # Split process name and PID
                last_dot = process_info.rfind('.')
                process_name = process_info[:last_dot]
                try:
                    pid = int(process_info[last_dot+1:])
                except ValueError:
                    continue

                # Parse bytes
                try:
                    bytes_in = int(parts[1]) if parts[1] else 0
                    bytes_out = int(parts[2]) if parts[2] else 0
                except (ValueError, IndexError):
                    continue

                # Only include processes with non-zero traffic
                if bytes_in > 0 or bytes_out > 0:
                    processes.append({
                        'process_name': process_name,
                        'pid': pid,
                        'bytes_in': bytes_in,
                        'bytes_out': bytes_out
                    })

            return processes

        except subprocess.TimeoutExpired:
            logger.error("nettop command timed out")
            return []
        except Exception as e:
            logger.error(f"Error running nettop: {e}", exc_info=True)
            return []

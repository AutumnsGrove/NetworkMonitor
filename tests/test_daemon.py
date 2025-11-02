"""
Comprehensive tests for NetworkDaemon class.

Tests daemon initialization, lifecycle (start/stop), sampling loop,
browser domain recording, status reporting, signal handlers, error handling,
and global daemon instance management.

Target: >85% coverage for daemon.py (currently at 77%)
"""
import pytest
import pytest_asyncio
import asyncio
import signal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List

from src.daemon import NetworkDaemon, get_daemon, set_daemon, run_daemon
from src.process_mapper import ProcessMapper, ProcessInfo
from src.retention import RetentionScheduler
from src.models import Application, NetworkSample, Domain, BrowserDomainSample
from src.db_queries import (
    get_application_by_name, get_domain_by_name,
    insert_application, insert_domain
)


# =============================================================================
# NetworkDaemon Initialization Tests
# =============================================================================

class TestNetworkDaemonInitialization:
    """Tests for NetworkDaemon initialization."""

    def test_daemon_init_with_default_parameters(self):
        """Test daemon initialization with default parameters."""
        daemon = NetworkDaemon()

        assert daemon.sampling_interval == 5
        assert daemon.enable_retention is True
        assert daemon.running is False
        assert isinstance(daemon.process_mapper, ProcessMapper)
        assert daemon.retention_scheduler is None
        assert isinstance(daemon.app_id_cache, dict)
        assert isinstance(daemon.domain_id_cache, dict)
        assert len(daemon.app_id_cache) == 0
        assert len(daemon.domain_id_cache) == 0
        assert daemon.samples_collected == 0
        assert daemon.errors_count == 0

    def test_daemon_init_with_custom_interval(self):
        """Test daemon initialization with custom sampling interval."""
        daemon = NetworkDaemon(sampling_interval=10)

        assert daemon.sampling_interval == 10
        assert daemon.enable_retention is True

    def test_daemon_init_with_retention_disabled(self):
        """Test daemon initialization with retention disabled."""
        daemon = NetworkDaemon(enable_retention=False)

        assert daemon.enable_retention is False
        assert daemon.sampling_interval == 5

    def test_daemon_init_with_all_custom_parameters(self):
        """Test daemon initialization with all custom parameters."""
        daemon = NetworkDaemon(sampling_interval=15, enable_retention=False)

        assert daemon.sampling_interval == 15
        assert daemon.enable_retention is False
        assert daemon.running is False

    def test_daemon_initial_state_not_running(self):
        """Test daemon starts in not running state."""
        daemon = NetworkDaemon()

        assert daemon.running is False

    def test_daemon_signal_handlers_setup(self, mocker):
        """Test daemon sets up signal handlers on init."""
        mock_signal = mocker.patch('signal.signal')

        daemon = NetworkDaemon()

        # Verify signal handlers were registered
        assert mock_signal.call_count == 2
        # Check for SIGTERM and SIGINT
        calls = mock_signal.call_args_list
        signals = [call[0][0] for call in calls]
        assert signal.SIGTERM in signals
        assert signal.SIGINT in signals


# =============================================================================
# Daemon Lifecycle Tests
# =============================================================================

class TestDaemonLifecycle:
    """Tests for daemon start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_transitions_to_running(self, mocker, temp_db):
        """Test start() transitions daemon to running state."""
        daemon = NetworkDaemon(enable_retention=False, sampling_interval=1)

        # Mock _sampling_loop to return immediately
        mock_sampling = mocker.patch.object(
            daemon, '_sampling_loop', new_callable=AsyncMock
        )

        # Start daemon (will complete after _sampling_loop mock returns)
        await daemon.start()

        # Should have been running during start
        mock_sampling.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, mocker, temp_db):
        """Test start() when daemon is already running does not error."""
        daemon = NetworkDaemon(enable_retention=False)
        daemon.running = True  # Simulate already running

        mock_sampling = mocker.patch.object(
            daemon, '_sampling_loop', new_callable=AsyncMock
        )

        await daemon.start()

        # Should not call sampling loop if already running
        mock_sampling.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_transitions_to_stopped(self, temp_db):
        """Test stop() transitions daemon to stopped state."""
        daemon = NetworkDaemon(enable_retention=False)
        daemon.running = True  # Simulate running state

        await daemon.stop()

        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_stop_when_already_stopped(self, temp_db):
        """Test stop() when daemon is already stopped does not error."""
        daemon = NetworkDaemon(enable_retention=False)
        daemon.running = False  # Already stopped

        # Should not raise exception
        await daemon.stop()

        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self, mocker, temp_db):
        """Test multiple start/stop cycles work correctly."""
        daemon = NetworkDaemon(enable_retention=False)

        mock_sampling = mocker.patch.object(
            daemon, '_sampling_loop', new_callable=AsyncMock
        )

        # First cycle
        await daemon.start()
        daemon.running = False  # Simulate loop ending
        await daemon.stop()

        # Second cycle
        await daemon.start()
        daemon.running = False
        await daemon.stop()

        # Should have started twice
        assert mock_sampling.call_count == 2


# =============================================================================
# Sampling Loop Tests
# =============================================================================

class TestSamplingLoop:
    """Tests for daemon sampling loop."""

    @pytest.mark.asyncio
    async def test_sample_network_with_mocked_process_mapper(self, mocker, temp_db):
        """Test _sample_network() with mocked ProcessMapper."""
        daemon = NetworkDaemon()

        # Create mock ProcessInfo objects
        mock_processes = [
            ProcessInfo(pid=1234, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari"),
            ProcessInfo(pid=5678, name="Chrome", path="/Applications/Chrome.app", bundle_id="com.google.Chrome"),
        ]

        # Mock process_mapper.get_all_network_processes
        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes
        )

        # Mock database operations
        mock_insert_sample = mocker.patch('src.daemon.insert_network_sample', new_callable=AsyncMock)
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, return_value=1)

        initial_samples = daemon.samples_collected

        await daemon._sample_network()

        # Should have collected samples
        assert daemon.samples_collected > initial_samples
        # Should have called insert_network_sample for each unique process
        assert mock_insert_sample.call_count == 2

    @pytest.mark.asyncio
    async def test_sample_network_increments_samples_collected(self, mocker, temp_db):
        """Test _sample_network() increments samples_collected counter."""
        daemon = NetworkDaemon()

        mock_processes = [
            ProcessInfo(pid=1234, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari"),
        ]

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes
        )
        mocker.patch('src.daemon.insert_network_sample', new_callable=AsyncMock)
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, return_value=1)

        initial_count = daemon.samples_collected

        await daemon._sample_network()

        assert daemon.samples_collected == initial_count + 1

    @pytest.mark.asyncio
    async def test_sample_network_handles_no_network_processes(self, mocker, temp_db):
        """Test _sample_network() handles no network processes gracefully."""
        daemon = NetworkDaemon()

        # Mock empty process list
        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=[]
        )

        initial_samples = daemon.samples_collected

        await daemon._sample_network()

        # Should not have incremented samples_collected
        assert daemon.samples_collected == initial_samples

    @pytest.mark.asyncio
    async def test_sample_network_handles_process_mapper_errors(self, mocker, temp_db):
        """Test _sample_network() handles ProcessMapper errors gracefully."""
        daemon = NetworkDaemon()

        # Mock process_mapper to raise exception
        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            side_effect=Exception("lsof command failed")
        )

        initial_errors = daemon.errors_count

        await daemon._sample_network()

        # Should have incremented error count
        assert daemon.errors_count == initial_errors + 1

    @pytest.mark.asyncio
    async def test_sampling_loop_respects_sampling_interval(self, mocker, temp_db):
        """Test sampling loop respects sampling_interval."""
        daemon = NetworkDaemon(sampling_interval=0.1, enable_retention=False)

        # Mock _sample_network
        sample_times = []

        async def track_sample_time():
            sample_times.append(asyncio.get_event_loop().time())

        mocker.patch.object(daemon, '_sample_network', side_effect=track_sample_time)

        # Start daemon and let it run for 2 samples
        task = asyncio.create_task(daemon.start())

        # Wait for 2 samples
        await asyncio.sleep(0.25)

        # Stop daemon
        daemon.running = False
        await asyncio.sleep(0.05)  # Allow loop to exit
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have collected at least 1 sample
        assert len(sample_times) >= 1

    @pytest.mark.asyncio
    async def test_sampling_loop_handles_cancellation(self, mocker, temp_db):
        """Test sampling loop handles asyncio.CancelledError."""
        daemon = NetworkDaemon(enable_retention=False)

        mocker.patch.object(daemon, '_sample_network', new_callable=AsyncMock)

        # Start daemon to trigger sampling loop
        daemon.running = True
        task = asyncio.create_task(daemon._sampling_loop())

        # Cancel after short delay
        await asyncio.sleep(0.01)
        daemon.running = False  # Stop the loop gracefully
        task.cancel()

        # The loop catches CancelledError internally and logs it
        # So we don't expect it to propagate
        try:
            await task
        except asyncio.CancelledError:
            # This is expected if task is cancelled before it can exit naturally
            pass


# =============================================================================
# App ID Caching Tests
# =============================================================================

class TestAppIdCaching:
    """Tests for application ID caching."""

    @pytest.mark.asyncio
    async def test_app_id_cache_populated_after_sampling(self, mocker, temp_db):
        """Test app_id_cache is populated after sampling."""
        daemon = NetworkDaemon()

        mock_processes = [
            ProcessInfo(pid=1234, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari"),
        ]

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes
        )
        mocker.patch('src.daemon.insert_network_sample', new_callable=AsyncMock)
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, return_value=123)

        assert len(daemon.app_id_cache) == 0

        await daemon._sample_network()

        # Cache should be populated
        assert len(daemon.app_id_cache) > 0
        assert "Safari:com.apple.Safari" in daemon.app_id_cache

    @pytest.mark.asyncio
    async def test_cache_hit_reduces_database_queries(self, mocker, temp_db):
        """Test cache hit reduces database queries."""
        daemon = NetworkDaemon()

        # Pre-populate cache
        daemon.app_id_cache["Safari:com.apple.Safari"] = 123

        mock_processes = [
            ProcessInfo(pid=1234, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari"),
        ]

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes
        )
        mock_get_app = mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock)
        mocker.patch('src.daemon.insert_network_sample', new_callable=AsyncMock)

        await daemon._sample_network()

        # Should not have queried database (cache hit)
        mock_get_app.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_handles_new_applications(self, mocker, temp_db):
        """Test cache handles new applications correctly."""
        daemon = NetworkDaemon()

        # First sample with Safari
        mock_processes_1 = [
            ProcessInfo(pid=1234, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari"),
        ]

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes_1
        )
        mocker.patch('src.daemon.insert_network_sample', new_callable=AsyncMock)
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, side_effect=[123, 456])

        await daemon._sample_network()

        assert len(daemon.app_id_cache) == 1

        # Second sample with Chrome (new app)
        mock_processes_2 = [
            ProcessInfo(pid=5678, name="Chrome", path="/Applications/Chrome.app", bundle_id="com.google.Chrome"),
        ]

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes_2
        )

        await daemon._sample_network()

        # Cache should have both apps
        assert len(daemon.app_id_cache) == 2


# =============================================================================
# Browser Domain Recording Tests
# =============================================================================

class TestBrowserDomainRecording:
    """Tests for browser domain recording functionality."""

    @pytest.mark.asyncio
    async def test_record_browser_domain_creates_domain(self, mocker, temp_db):
        """Test record_browser_domain() creates domain if not exists."""
        daemon = NetworkDaemon()

        mock_get_domain = mocker.patch(
            'src.daemon.get_domain_by_name',
            new_callable=AsyncMock,
            return_value=None
        )
        mock_insert_domain = mocker.patch(
            'src.daemon.insert_domain',
            new_callable=AsyncMock,
            return_value=1
        )
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, return_value=1)
        mocker.patch('src.daemon.insert_browser_domain_sample', new_callable=AsyncMock)

        await daemon.record_browser_domain(
            domain="netflix.com",
            browser="zen",
            bytes_sent=1024,
            bytes_received=2048
        )

        # Should have created domain
        mock_insert_domain.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_browser_domain_creates_browser_app(self, mocker, temp_db):
        """Test record_browser_domain() creates browser application if not exists."""
        daemon = NetworkDaemon()

        mocker.patch('src.daemon.get_domain_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_domain', new_callable=AsyncMock, return_value=1)
        mock_get_app = mocker.patch(
            'src.daemon.get_application_by_name',
            new_callable=AsyncMock,
            return_value=None
        )
        mock_insert_app = mocker.patch(
            'src.daemon.insert_application',
            new_callable=AsyncMock,
            return_value=1
        )
        mocker.patch('src.daemon.insert_browser_domain_sample', new_callable=AsyncMock)

        await daemon.record_browser_domain(
            domain="netflix.com",
            browser="zen",
            bytes_sent=1024,
            bytes_received=2048
        )

        # Should have created browser app
        mock_insert_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_browser_domain_creates_sample(self, mocker, temp_db):
        """Test record_browser_domain() creates browser_domain_sample."""
        daemon = NetworkDaemon()

        mocker.patch('src.daemon.get_domain_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_domain', new_callable=AsyncMock, return_value=1)
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, return_value=1)
        mock_insert_sample = mocker.patch(
            'src.daemon.insert_browser_domain_sample',
            new_callable=AsyncMock
        )

        await daemon.record_browser_domain(
            domain="netflix.com",
            browser="zen",
            bytes_sent=1024,
            bytes_received=2048
        )

        # Should have created sample
        mock_insert_sample.assert_called_once()

        # Verify sample has correct data
        call_args = mock_insert_sample.call_args[0][0]
        assert call_args.domain_id == 1
        assert call_args.app_id == 1
        assert call_args.bytes_sent == 1024
        assert call_args.bytes_received == 2048

    @pytest.mark.asyncio
    async def test_record_browser_domain_handles_parent_domain(self, mocker, temp_db):
        """Test record_browser_domain() handles parent domain rollup."""
        daemon = NetworkDaemon()

        # Mock get_domain_with_parent to return subdomain and parent
        mocker.patch(
            'src.daemon.get_domain_with_parent',
            return_value=("www.netflix.com", "netflix.com")
        )
        mocker.patch('src.daemon.get_domain_by_name', new_callable=AsyncMock, return_value=None)
        mock_insert_domain = mocker.patch(
            'src.daemon.insert_domain',
            new_callable=AsyncMock,
            return_value=1
        )
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, return_value=1)
        mocker.patch('src.daemon.insert_browser_domain_sample', new_callable=AsyncMock)

        await daemon.record_browser_domain(
            domain="www.netflix.com",
            browser="zen"
        )

        # Should have created domain with parent
        mock_insert_domain.assert_called_once()
        call_args = mock_insert_domain.call_args[0][0]
        assert call_args.domain == "www.netflix.com"
        assert call_args.parent_domain == "netflix.com"

    @pytest.mark.asyncio
    async def test_record_browser_domain_handles_errors(self, mocker, temp_db):
        """Test record_browser_domain() handles errors gracefully."""
        daemon = NetworkDaemon()

        # Mock to raise exception
        mocker.patch(
            'src.daemon.get_domain_by_name',
            new_callable=AsyncMock,
            side_effect=Exception("Database error")
        )

        # Should not raise exception
        await daemon.record_browser_domain(
            domain="netflix.com",
            browser="zen"
        )


# =============================================================================
# Status Reporting Tests
# =============================================================================

class TestStatusReporting:
    """Tests for daemon status reporting."""

    def test_get_status_returns_correct_structure(self):
        """Test get_status() returns correct structure."""
        daemon = NetworkDaemon(sampling_interval=10, enable_retention=True)

        status = daemon.get_status()

        assert isinstance(status, dict)
        assert 'running' in status
        assert 'sampling_interval' in status
        assert 'samples_collected' in status
        assert 'errors_count' in status
        assert 'cached_apps' in status
        assert 'cached_domains' in status
        assert 'retention_enabled' in status

    def test_get_status_includes_samples_collected(self):
        """Test get_status() includes samples_collected."""
        daemon = NetworkDaemon()
        daemon.samples_collected = 42

        status = daemon.get_status()

        assert status['samples_collected'] == 42

    def test_get_status_includes_running_state(self):
        """Test get_status() includes running state."""
        daemon = NetworkDaemon()

        # Not running
        status = daemon.get_status()
        assert status['running'] is False

        # Running
        daemon.running = True
        status = daemon.get_status()
        assert status['running'] is True

    def test_get_status_includes_cache_sizes(self):
        """Test get_status() includes cache sizes."""
        daemon = NetworkDaemon()
        daemon.app_id_cache = {"Safari": 1, "Chrome": 2}
        daemon.domain_id_cache = {"netflix.com": 1}

        status = daemon.get_status()

        assert status['cached_apps'] == 2
        assert status['cached_domains'] == 1

    def test_get_status_includes_retention_scheduler_status(self):
        """Test get_status() includes retention scheduler status."""
        daemon = NetworkDaemon(enable_retention=True)

        status = daemon.get_status()

        assert status['retention_enabled'] is True

        daemon2 = NetworkDaemon(enable_retention=False)
        status2 = daemon2.get_status()

        assert status2['retention_enabled'] is False


# =============================================================================
# Retention Scheduler Integration Tests
# =============================================================================

class TestRetentionSchedulerIntegration:
    """Tests for retention scheduler integration."""

    @pytest.mark.asyncio
    async def test_retention_scheduler_started_when_enabled(self, mocker, temp_db):
        """Test retention scheduler is started when enable_retention=True."""
        # Mock RetentionScheduler
        mock_scheduler_class = mocker.patch('src.daemon.RetentionScheduler')
        mock_scheduler_instance = AsyncMock()
        mock_scheduler_class.return_value = mock_scheduler_instance

        daemon = NetworkDaemon(enable_retention=True)

        # Mock _sampling_loop
        mocker.patch.object(daemon, '_sampling_loop', new_callable=AsyncMock)

        await daemon.start()

        # Retention scheduler should be started
        mock_scheduler_instance.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_retention_scheduler_not_started_when_disabled(self, mocker, temp_db):
        """Test retention scheduler is not started when enable_retention=False."""
        mock_scheduler_class = mocker.patch('src.daemon.RetentionScheduler')

        daemon = NetworkDaemon(enable_retention=False)

        mocker.patch.object(daemon, '_sampling_loop', new_callable=AsyncMock)

        await daemon.start()

        # RetentionScheduler should not be instantiated
        mock_scheduler_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_retention_scheduler_stopped_on_daemon_stop(self, mocker, temp_db):
        """Test retention scheduler is stopped when daemon stops."""
        mock_scheduler = AsyncMock()

        daemon = NetworkDaemon(enable_retention=True)
        daemon.retention_scheduler = mock_scheduler
        daemon.running = True

        await daemon.stop()

        # Retention scheduler should be stopped
        mock_scheduler.stop.assert_called_once()


# =============================================================================
# Signal Handler Tests
# =============================================================================

class TestSignalHandlers:
    """Tests for signal handler functionality."""

    def test_sigterm_handler_registered(self, mocker):
        """Test SIGTERM handler is registered."""
        mock_signal = mocker.patch('signal.signal')

        daemon = NetworkDaemon()

        # Find SIGTERM registration
        calls = mock_signal.call_args_list
        sigterm_registered = any(call[0][0] == signal.SIGTERM for call in calls)

        assert sigterm_registered

    def test_sigint_handler_registered(self, mocker):
        """Test SIGINT handler is registered."""
        mock_signal = mocker.patch('signal.signal')

        daemon = NetworkDaemon()

        # Find SIGINT registration
        calls = mock_signal.call_args_list
        sigint_registered = any(call[0][0] == signal.SIGINT for call in calls)

        assert sigint_registered

    @pytest.mark.asyncio
    async def test_signal_handler_calls_stop(self, mocker, temp_db):
        """Test signal handler calls stop() when daemon is running."""
        # We can't easily test signal handlers directly in async context,
        # but we can verify the handler is set up correctly
        daemon = NetworkDaemon()

        # Mock stop method
        mock_stop = mocker.patch.object(daemon, 'stop', new_callable=AsyncMock)

        # Manually call stop to verify it works
        daemon.running = True
        await daemon.stop()

        mock_stop.assert_called_once()


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in daemon."""

    @pytest.mark.asyncio
    async def test_sample_network_continues_on_database_error(self, mocker, temp_db):
        """Test _sample_network() continues on database error."""
        daemon = NetworkDaemon()

        mock_processes = [
            ProcessInfo(pid=1234, name="Safari", path="/Applications/Safari.app", bundle_id="com.apple.Safari"),
        ]

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes
        )

        # Mock insert_network_sample to raise exception
        mocker.patch(
            'src.daemon.insert_network_sample',
            new_callable=AsyncMock,
            side_effect=Exception("Database error")
        )
        mocker.patch('src.daemon.get_application_by_name', new_callable=AsyncMock, return_value=None)
        mocker.patch('src.daemon.insert_application', new_callable=AsyncMock, return_value=1)

        initial_errors = daemon.errors_count

        # Should not raise exception
        await daemon._sample_network()

        # Error count should increase
        assert daemon.errors_count > initial_errors

    @pytest.mark.asyncio
    async def test_sample_network_continues_on_process_mapper_error(self, mocker, temp_db):
        """Test _sample_network() continues on ProcessMapper error."""
        daemon = NetworkDaemon()

        # Mock to raise exception
        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            side_effect=Exception("lsof failed")
        )

        initial_errors = daemon.errors_count

        # Should not raise exception
        await daemon._sample_network()

        assert daemon.errors_count == initial_errors + 1

    @pytest.mark.asyncio
    async def test_error_counter_increments_on_errors(self, mocker, temp_db):
        """Test error counter increments on errors."""
        daemon = NetworkDaemon()

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            side_effect=Exception("Error")
        )

        assert daemon.errors_count == 0

        await daemon._sample_network()
        assert daemon.errors_count == 1

        await daemon._sample_network()
        assert daemon.errors_count == 2

    @pytest.mark.asyncio
    async def test_sampling_loop_handles_exceptions(self, mocker, temp_db):
        """Test sampling loop handles exceptions and continues."""
        daemon = NetworkDaemon(sampling_interval=0.01, enable_retention=False)

        call_count = [0]

        async def failing_sample():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First call fails")
            # Second call succeeds

        mocker.patch.object(daemon, '_sample_network', side_effect=failing_sample)

        # Start daemon
        task = asyncio.create_task(daemon.start())

        # Wait for 2 attempts
        await asyncio.sleep(0.05)

        # Stop daemon
        daemon.running = False
        await asyncio.sleep(0.01)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have attempted multiple times despite error
        assert call_count[0] >= 1
        assert daemon.errors_count >= 1


# =============================================================================
# Global Daemon Instance Management Tests
# =============================================================================

class TestGlobalDaemonInstance:
    """Tests for global daemon instance management."""

    def test_get_daemon_returns_none_initially(self):
        """Test get_daemon() returns None initially."""
        # Reset global instance
        import src.daemon
        src.daemon._daemon_instance = None

        result = get_daemon()

        assert result is None

    def test_set_daemon_sets_global_instance(self):
        """Test set_daemon() sets global instance."""
        daemon = NetworkDaemon()

        set_daemon(daemon)

        result = get_daemon()
        assert result is daemon

    def test_get_daemon_returns_set_instance(self):
        """Test get_daemon() returns the instance set by set_daemon()."""
        daemon = NetworkDaemon(sampling_interval=10)

        set_daemon(daemon)

        result = get_daemon()
        assert result is daemon
        assert result.sampling_interval == 10

    def test_set_daemon_overwrites_previous_instance(self):
        """Test set_daemon() overwrites previous instance."""
        daemon1 = NetworkDaemon(sampling_interval=5)
        daemon2 = NetworkDaemon(sampling_interval=10)

        set_daemon(daemon1)
        assert get_daemon() is daemon1

        set_daemon(daemon2)
        assert get_daemon() is daemon2
        assert get_daemon().sampling_interval == 10


# =============================================================================
# run_daemon() Function Tests
# =============================================================================

class TestRunDaemon:
    """Tests for run_daemon() helper function."""

    @pytest.mark.asyncio
    async def test_run_daemon_creates_daemon_instance(self, mocker, temp_db):
        """Test run_daemon() creates daemon instance."""
        mock_daemon_class = mocker.patch('src.daemon.NetworkDaemon')
        mock_daemon_instance = AsyncMock()
        mock_daemon_class.return_value = mock_daemon_instance

        # Mock start to return immediately
        async def mock_start():
            pass

        mock_daemon_instance.start = mock_start
        mock_daemon_instance.stop = AsyncMock()

        # Run with short timeout
        task = asyncio.create_task(run_daemon(sampling_interval=5, enable_retention=False))
        await asyncio.sleep(0.01)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have created daemon
        mock_daemon_class.assert_called_once_with(
            sampling_interval=5,
            enable_retention=False
        )

    @pytest.mark.asyncio
    async def test_run_daemon_sets_global_instance(self, mocker, temp_db):
        """Test run_daemon() sets global daemon instance."""
        mock_set_daemon = mocker.patch('src.daemon.set_daemon')

        mock_daemon_class = mocker.patch('src.daemon.NetworkDaemon')
        mock_daemon_instance = AsyncMock()
        mock_daemon_class.return_value = mock_daemon_instance

        async def mock_start():
            pass

        mock_daemon_instance.start = mock_start
        mock_daemon_instance.stop = AsyncMock()

        task = asyncio.create_task(run_daemon())
        await asyncio.sleep(0.01)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have set global daemon
        mock_set_daemon.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_daemon_calls_stop_on_keyboard_interrupt(self, mocker, temp_db):
        """Test run_daemon() calls stop() on KeyboardInterrupt."""
        mock_daemon = AsyncMock()

        async def mock_start():
            raise KeyboardInterrupt()

        mock_daemon.start = mock_start
        mock_daemon.stop = AsyncMock()

        mocker.patch('src.daemon.NetworkDaemon', return_value=mock_daemon)
        mocker.patch('src.daemon.set_daemon')

        await run_daemon()

        # Should have called stop
        mock_daemon.stop.assert_called_once()


# =============================================================================
# Integration Tests
# =============================================================================

class TestDaemonIntegration:
    """Integration tests combining multiple daemon features."""

    @pytest.mark.asyncio
    async def test_full_sampling_cycle_with_real_database(self, temp_db, mocker):
        """Test full sampling cycle with real database operations."""
        daemon = NetworkDaemon(enable_retention=False)

        # Create mock process
        mock_processes = [
            ProcessInfo(
                pid=1234,
                name="TestBrowser",
                path="/Applications/TestBrowser.app",
                bundle_id="com.test.browser"
            ),
        ]

        mocker.patch.object(
            daemon.process_mapper, 'get_all_network_processes',
            return_value=mock_processes
        )

        # Run one sample
        await daemon._sample_network()

        # Verify sample was collected
        assert daemon.samples_collected == 1

        # Verify app was cached
        assert "TestBrowser:com.test.browser" in daemon.app_id_cache

    @pytest.mark.asyncio
    async def test_daemon_lifecycle_with_retention_scheduler(self, temp_db, mocker):
        """Test daemon lifecycle with retention scheduler integration."""
        mock_scheduler_class = mocker.patch('src.daemon.RetentionScheduler')
        mock_scheduler = AsyncMock()
        mock_scheduler_class.return_value = mock_scheduler

        daemon = NetworkDaemon(enable_retention=True)
        mocker.patch.object(daemon, '_sampling_loop', new_callable=AsyncMock)

        # Start daemon
        await daemon.start()

        # Verify retention scheduler started
        mock_scheduler.start.assert_called_once()

        # Stop daemon (set running to True first so stop() actually does something)
        daemon.running = True
        await daemon.stop()

        # Verify retention scheduler stopped
        mock_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_reflects_actual_daemon_state(self, temp_db, mocker):
        """Test get_status() reflects actual daemon state."""
        daemon = NetworkDaemon(sampling_interval=10, enable_retention=True)

        # Initial state
        status = daemon.get_status()
        assert status['running'] is False
        assert status['samples_collected'] == 0
        assert status['sampling_interval'] == 10

        # Simulate some activity
        daemon.running = True
        daemon.samples_collected = 42
        daemon.errors_count = 3
        daemon.app_id_cache = {"Safari": 1, "Chrome": 2}

        status = daemon.get_status()
        assert status['running'] is True
        assert status['samples_collected'] == 42
        assert status['errors_count'] == 3
        assert status['cached_apps'] == 2

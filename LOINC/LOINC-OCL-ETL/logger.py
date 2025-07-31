"""
Logging Module for LOINC to OCL Transformation

This module provides comprehensive logging and progress tracking including:
- Multi-level logging with rotation and archiving
- Progress tracking with ETA calculations
- Performance monitoring and statistics
- Error aggregation and reporting
- Integration with all transformation phases

Author: LOINC OCL Transform Project
Date: July 2025
"""

import os
import sys
import logging
import logging.handlers
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, TextIO
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import threading
from contextlib import contextmanager


@dataclass
class ProgressStats:
    """Data class for progress tracking statistics"""
    total_items: int
    processed_items: int = 0
    failed_items: int = 0
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 100.0
        return (self.processed_items / self.total_items) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.processed_items == 0:
            return 100.0
        return ((self.processed_items - self.failed_items) / self.processed_items) * 100.0
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    @property
    def items_per_second(self) -> float:
        """Calculate processing rate"""
        elapsed = self.elapsed_time
        if elapsed == 0:
            return 0.0
        return self.processed_items / elapsed
    
    @property
    def estimated_remaining_time(self) -> float:
        """Estimate remaining time in seconds"""
        if self.processed_items == 0 or self.completion_percentage >= 100.0:
            return 0.0
        
        rate = self.items_per_second
        if rate == 0:
            return float('inf')
        
        remaining_items = self.total_items - self.processed_items
        return remaining_items / rate


@dataclass
class ErrorSummary:
    """Data class for error aggregation and summary"""
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_samples: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    warning_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    warning_samples: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    def add_error(self, error_type: str, message: str, max_samples: int = 5) -> None:
        """Add error to summary"""
        self.error_counts[error_type] += 1
        if len(self.error_samples[error_type]) < max_samples:
            self.error_samples[error_type].append(message)
    
    def add_warning(self, warning_type: str, message: str, max_samples: int = 5) -> None:
        """Add warning to summary"""
        self.warning_counts[warning_type] += 1
        if len(self.warning_samples[warning_type]) < max_samples:
            self.warning_samples[warning_type].append(message)
    
    @property
    def total_errors(self) -> int:
        return sum(self.error_counts.values())
    
    @property
    def total_warnings(self) -> int:
        return sum(self.warning_counts.values())


class ProgressTracker:
    """
    Progress tracking utility with ETA calculations and reporting.
    """
    
    def __init__(self, name: str, total_items: int, logger: Optional[logging.Logger] = None):
        """
        Initialize progress tracker
        
        Args:
            name: Name of the process being tracked
            total_items: Total number of items to process
            logger: Optional logger instance
        """
        self.name = name
        self.stats = ProgressStats(total_items)
        self.logger = logger or logging.getLogger(__name__)
        self.last_log_time = 0.0
        self.log_interval = 5.0  # Log progress every 5 seconds
        self.lock = threading.Lock()
    
    def update(self, processed: int = 1, failed: int = 0) -> None:
        """
        Update progress counters
        
        Args:
            processed: Number of items processed (default: 1)
            failed: Number of items that failed (default: 0)
        """
        with self.lock:
            self.stats.processed_items += processed
            self.stats.failed_items += failed
            self.stats.last_update_time = time.time()
            
            # Log progress periodically
            if self.stats.last_update_time - self.last_log_time >= self.log_interval:
                self._log_progress()
                self.last_log_time = self.stats.last_update_time
    
    def _log_progress(self) -> None:
        """Log current progress"""
        percentage = self.stats.completion_percentage
        rate = self.stats.items_per_second
        eta_seconds = self.stats.estimated_remaining_time
        
        # Format ETA
        if eta_seconds == float('inf'):
            eta_str = "unknown"
        elif eta_seconds > 3600:
            eta_str = f"{eta_seconds/3600:.1f}h"
        elif eta_seconds > 60:
            eta_str = f"{eta_seconds/60:.1f}m"
        else:
            eta_str = f"{eta_seconds:.0f}s"
        
        self.logger.info(
            f"{self.name}: {self.stats.processed_items:,}/{self.stats.total_items:,} "
            f"({percentage:.1f}%) | {rate:.1f}/s | ETA: {eta_str}"
        )
        
        if self.stats.failed_items > 0:
            failure_rate = (self.stats.failed_items / self.stats.processed_items) * 100
            self.logger.warning(f"{self.name}: {self.stats.failed_items} failures ({failure_rate:.1f}%)")
    
    def complete(self) -> None:
        """Mark progress as complete and log final statistics"""
        with self.lock:
            self.stats.processed_items = self.stats.total_items
        
        elapsed = self.stats.elapsed_time
        rate = self.stats.items_per_second
        success_rate = self.stats.success_rate
        
        self.logger.info(
            f"{self.name} COMPLETE: {self.stats.total_items:,} items in {elapsed:.2f}s "
            f"({rate:.1f}/s) | Success: {success_rate:.1f}%"
        )
        
        if self.stats.failed_items > 0:
            self.logger.warning(f"{self.name}: {self.stats.failed_items} total failures")


class TransformationLogger:
    """
    Comprehensive logging system for LOINC transformation process.
    
    Features:
    - Multi-level logging with file rotation
    - Progress tracking with ETAs
    - Error aggregation and reporting
    - Performance monitoring
    - JSON-formatted structured logging option
    """
    
    def __init__(self, config_manager=None, log_level: str = "INFO"):
        """
        Initialize transformation logger
        
        Args:
            config_manager: Optional ConfigManager instance
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.config_manager = config_manager
        self.log_level = getattr(logging, log_level.upper())
        
        # Get log directory from config or use default
        if config_manager and hasattr(config_manager, 'paths'):
            self.log_dir = config_manager.paths.logs_dir
        else:
            self.log_dir = Path('./logs')
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Session information - MUST be set before setting up logger
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start_time = time.time()
        
        # Initialize logging components
        self.main_logger = self._setup_main_logger()
        self.progress_trackers: Dict[str, ProgressTracker] = {}
        self.error_summary = ErrorSummary()
        
        # Performance tracking
        self.phase_start_times: Dict[str, float] = {}
        self.phase_durations: Dict[str, float] = {}
        
        # Create session log file
        self._setup_session_logging()
    
    def _setup_main_logger(self) -> logging.Logger:
        """Set up main logger with file and console handlers"""
        
        # Create logger
        logger = logging.getLogger('loinc_transformation')
        logger.setLevel(self.log_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler with proper encoding
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        
        # Try to set UTF-8 encoding for console if possible
        try:
            if hasattr(console_handler.stream, 'reconfigure'):
                console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            # Fall back to default handling if reconfigure isn't available
            pass
            
        logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = self.log_dir / f'loinc_transform_{self.session_id}.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)  # Always debug level for file
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
        # Error file handler (errors and warnings only)
        error_file = self.log_dir / f'loinc_errors_{self.session_id}.log'
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(file_format)
        logger.addHandler(error_handler)
        
        return logger
    
    def _setup_session_logging(self) -> None:
        """Set up session-specific logging"""
        session_info = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'log_level': logging.getLevelName(self.log_level),
            'log_directory': str(self.log_dir)
        }
        
        self.main_logger.info("=" * 60)
        self.main_logger.info("LOINC TO OCL TRANSFORMATION SESSION STARTED")
        self.main_logger.info("=" * 60)
        self.main_logger.info(f"Session ID: {session_info['session_id']}")
        self.main_logger.info(f"Start Time: {session_info['start_time']}")
        self.main_logger.info(f"Log Level: {session_info['log_level']}")
        self.main_logger.info(f"Log Directory: {session_info['log_directory']}")
        self.main_logger.info("=" * 60)
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Get a logger instance
        
        Args:
            name: Optional logger name (uses main logger if None)
            
        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(f'loinc_transformation.{name}')
        return self.main_logger
    
    def start_phase(self, phase_name: str) -> None:
        """Mark the start of a transformation phase"""
        self.phase_start_times[phase_name] = time.time()
        self.main_logger.info(f"STARTING PHASE: {phase_name}")
        self.main_logger.info("-" * 40)
    
    def end_phase(self, phase_name: str) -> None:
        """Mark the end of a transformation phase"""
        if phase_name in self.phase_start_times:
            duration = time.time() - self.phase_start_times[phase_name]
            self.phase_durations[phase_name] = duration
            self.main_logger.info("-" * 40)
            self.main_logger.info(f"COMPLETED PHASE: {phase_name} ({duration:.2f}s)")
            self.main_logger.info("")
        else:
            self.main_logger.warning(f"End phase called for {phase_name} but no start time recorded")
    
    @contextmanager
    def phase_context(self, phase_name: str):
        """Context manager for automatic phase timing"""
        self.start_phase(phase_name)
        try:
            yield
        finally:
            self.end_phase(phase_name)
    
    def create_progress_tracker(self, name: str, total_items: int) -> ProgressTracker:
        """
        Create a new progress tracker
        
        Args:
            name: Name of the process
            total_items: Total number of items to process
            
        Returns:
            ProgressTracker instance
        """
        tracker = ProgressTracker(name, total_items, self.main_logger)
        self.progress_trackers[name] = tracker
        return tracker
    
    def log_error(self, error_type: str, message: str, exc_info: bool = False) -> None:
        """
        Log an error with categorization
        
        Args:
            error_type: Category of error
            message: Error message
            exc_info: Include exception info
        """
        self.main_logger.error(message, exc_info=exc_info)
        self.error_summary.add_error(error_type, message)
    
    def log_warning(self, warning_type: str, message: str) -> None:
        """
        Log a warning with categorization
        
        Args:
            warning_type: Category of warning
            message: Warning message
        """
        self.main_logger.warning(message)
        self.error_summary.add_warning(warning_type, message)
    
    def log_statistics(self, stats_name: str, statistics: Dict[str, Any]) -> None:
        """
        Log statistics in structured format
        
        Args:
            stats_name: Name of the statistics set
            statistics: Dictionary of statistics
        """
        self.main_logger.info(f"STATISTICS - {stats_name}:")
        for key, value in statistics.items():
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    formatted_value = f"{value:,.2f}" if value >= 1 else f"{value:.4f}"
                else:
                    formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)
            self.main_logger.info(f"  {key}: {formatted_value}")
    
    def generate_session_report(self) -> Dict[str, Any]:
        """Generate comprehensive session report"""
        session_duration = time.time() - self.session_start_time
        
        report = {
            'session_info': {
                'session_id': self.session_id,
                'start_time': datetime.fromtimestamp(self.session_start_time).isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_seconds': session_duration,
                'duration_formatted': str(timedelta(seconds=int(session_duration)))
            },
            'phase_performance': {
                phase: {
                    'duration_seconds': duration,
                    'duration_formatted': str(timedelta(seconds=int(duration)))
                }
                for phase, duration in self.phase_durations.items()
            },
            'progress_summary': {
                name: {
                    'total_items': tracker.stats.total_items,
                    'processed_items': tracker.stats.processed_items,
                    'failed_items': tracker.stats.failed_items,
                    'completion_percentage': tracker.stats.completion_percentage,
                    'success_rate': tracker.stats.success_rate,
                    'items_per_second': tracker.stats.items_per_second
                }
                for name, tracker in self.progress_trackers.items()
            },
            'error_summary': {
                'total_errors': self.error_summary.total_errors,
                'total_warnings': self.error_summary.total_warnings,
                'error_types': dict(self.error_summary.error_counts),
                'warning_types': dict(self.error_summary.warning_counts),
                'error_samples': {k: v[:3] for k, v in self.error_summary.error_samples.items()},
                'warning_samples': {k: v[:3] for k, v in self.error_summary.warning_samples.items()}
            }
        }
        
        return report
    
    def save_session_report(self, filename: Optional[str] = None) -> Path:
        """
        Save session report to JSON file
        
        Args:
            filename: Optional filename (uses session ID if None)
            
        Returns:
            Path to saved report file
        """
        if not filename:
            filename = f'session_report_{self.session_id}.json'
        
        report_path = self.log_dir / filename
        report = self.generate_session_report()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.main_logger.info(f"Session report saved to: {report_path}")
        return report_path
    
    def finalize_session(self) -> None:
        """Finalize logging session with summary report"""
        
        # Complete any active progress trackers
        for tracker in self.progress_trackers.values():
            if tracker.stats.completion_percentage < 100:
                tracker.complete()
        
        # Generate and log final report
        report = self.generate_session_report()
        
        self.main_logger.info("=" * 60)
        self.main_logger.info("TRANSFORMATION SESSION SUMMARY")
        self.main_logger.info("=" * 60)
        
        session_info = report['session_info']
        self.main_logger.info(f"Session Duration: {session_info['duration_formatted']}")
        
        if report['phase_performance']:
            self.main_logger.info("\nPhase Performance:")
            for phase, perf in report['phase_performance'].items():
                self.main_logger.info(f"  {phase}: {perf['duration_formatted']}")
        
        if report['progress_summary']:
            self.main_logger.info("\nProgress Summary:")
            for name, progress in report['progress_summary'].items():
                self.main_logger.info(
                    f"  {name}: {progress['processed_items']:,}/{progress['total_items']:,} "
                    f"({progress['completion_percentage']:.1f}%) | {progress['items_per_second']:.1f}/s"
                )
        
        error_summary = report['error_summary']
        self.main_logger.info(f"\nErrors: {error_summary['total_errors']}")
        self.main_logger.info(f"Warnings: {error_summary['total_warnings']}")
        
        # Save detailed report
        report_path = self.save_session_report()
        
        self.main_logger.info("=" * 60)
        self.main_logger.info("SESSION COMPLETED")
        self.main_logger.info("=" * 60)


# Example usage and testing
if __name__ == "__main__":
    # Test the logging system
    print("Testing LOINC Transformation Logger...")
    print("=" * 50)
    
    try:
        # Initialize logger
        logger_system = TransformationLogger(log_level="INFO")
        
        # Test phase logging
        with logger_system.phase_context("Test Phase"):
            logger = logger_system.get_logger("test")
            logger.info("This is a test log message")
            
            # Test progress tracking
            progress = logger_system.create_progress_tracker("Test Process", 100)
            
            # Simulate some progress
            for i in range(0, 101, 10):
                progress.update(10)
                time.sleep(0.1)  # Simulate work
            
            progress.complete()
            
            # Test error logging
            logger_system.log_error("test_error", "This is a test error")
            logger_system.log_warning("test_warning", "This is a test warning")
            
            # Test statistics logging
            logger_system.log_statistics("Test Stats", {
                "items_processed": 1000,
                "success_rate": 95.5,
                "average_time_per_item": 0.125
            })
        
        # Finalize session
        logger_system.finalize_session()
        
        print("✓ Logger testing completed successfully")
        print(f"Logs saved to: {logger_system.log_dir}")
        
    except Exception as e:
        print(f"✗ Error testing logger: {str(e)}")
        import traceback
        traceback.print_exc()
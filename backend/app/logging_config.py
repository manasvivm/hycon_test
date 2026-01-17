# backend/app/logging_config.py
"""
Production-grade logging configuration with rotation and retention
Prevents log files from growing indefinitely
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

def setup_logging():
    """
    Configure logging with rotation and retention policies
    
    Log Structure:
    - logs/app.log - Main application log (rotated)
    - logs/websocket.log - WebSocket-specific log (rotated)
    - logs/ldap.log - LDAP authentication log (rotated)
    - logs/error.log - Error-only log (rotated)
    """
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Log format with more context
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    root_logger.handlers.clear()
    
    # 1. Main Application Log (Rotating File Handler)
    # Rotates when file reaches 10MB, keeps 7 backup files (7 days worth)
    app_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=7,  # Keep 7 old files
        encoding='utf-8'
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_handler)
    
    # 2. Error-Only Log (Separate file for critical issues)
    # Rotates when file reaches 5MB, keeps 14 backup files
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=14,  # Keep 2 weeks of errors
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # 3. Console Handler (for terminal output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # 4. WebSocket-Specific Log (Time-based rotation)
    # Rotates at midnight, keeps 7 days
    websocket_logger = logging.getLogger('websocket')
    websocket_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "websocket.log",
        when='midnight',
        interval=1,
        backupCount=7,  # Keep 7 days
        encoding='utf-8'
    )
    websocket_handler.setLevel(logging.INFO)
    websocket_handler.setFormatter(detailed_formatter)
    websocket_logger.addHandler(websocket_handler)
    websocket_logger.setLevel(logging.INFO)
    websocket_logger.propagate = False  # Don't duplicate to root logger
    
    # 5. LDAP Authentication Log (Time-based rotation)
    # Rotates at midnight, keeps 30 days for security audit
    ldap_logger = logging.getLogger('ldap')
    ldap_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "ldap.log",
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days for compliance
        encoding='utf-8'
    )
    ldap_handler.setLevel(logging.INFO)
    ldap_handler.setFormatter(detailed_formatter)
    ldap_logger.addHandler(ldap_handler)
    ldap_logger.setLevel(logging.INFO)
    ldap_logger.propagate = False
    
    # 6. Database Query Log (Optional - Enable for debugging)
    # Uncomment to log all database queries (WARNING: Very verbose!)
    # db_logger = logging.getLogger('sqlalchemy.engine')
    # db_logger.setLevel(logging.WARNING)  # Only log warnings/errors
    
    # Log startup message
    root_logger.info("=" * 80)
    root_logger.info("HyCON Equipment Management System - Starting")
    root_logger.info(f"Log Directory: {log_dir.absolute()}")
    root_logger.info(f"Retention: App logs=7 days, Errors=14 days, LDAP=30 days")
    root_logger.info("=" * 80)
    
    return root_logger

def cleanup_old_logs(days_to_keep=30):
    """
    Manual cleanup function for very old logs
    Called by background scheduler
    
    Args:
        days_to_keep: Delete logs older than this many days
    """
    log_dir = Path("logs")
    if not log_dir.exists():
        return
    
    cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
    deleted_count = 0
    
    for log_file in log_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                deleted_count += 1
            except Exception as e:
                logging.error(f"Failed to delete old log {log_file}: {e}")
    
    if deleted_count > 0:
        logging.info(f"Cleaned up {deleted_count} old log files (older than {days_to_keep} days)")

def get_log_stats():
    """Get statistics about current log files"""
    log_dir = Path("logs")
    if not log_dir.exists():
        return {}
    
    stats = {}
    total_size = 0
    
    for log_file in log_dir.glob("*.log*"):
        size = log_file.stat().st_size
        total_size += size
        stats[log_file.name] = {
            'size_mb': round(size / (1024 * 1024), 2),
            'modified': datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    
    stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
    return stats

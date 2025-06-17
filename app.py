"""
Wind Farm Turbine Investigation Application
Main application entry point for the Silent Loss Detector.
"""

import dash
import dash_bootstrap_components as dbc
import logging
import logging.handlers
import os
from datetime import datetime
import sys

# Import layouts and callbacks
from src.layouts.main_dashboard import create_main_dashboard_layout

# Import callbacks to register them
from src.callbacks import main_callbacks, investigation_callbacks  # noqa: F401


# Global variable to track if logging has been setup
_logging_initialized = False
_log_files = None

def setup_logging():
    """Setup comprehensive logging for the Dash application."""
    global _logging_initialized, _log_files

    # Return existing log files if already initialized
    if _logging_initialized and _log_files:
        return _log_files

    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Create date-based log files (one per day)
    date_str = datetime.now().strftime("%Y%m%d")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # 1. Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # 2. General application log file (rotating)
    app_log_file = os.path.join(logs_dir, f"dash_app_{date_str}.log")
    app_file_handler = logging.handlers.RotatingFileHandler(
        app_log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB files, keep 5 backups
    )
    app_file_handler.setLevel(logging.DEBUG)
    app_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_file_handler)

    # 3. Error-only log file
    error_log_file = os.path.join(logs_dir, f"dash_errors_{date_str}.log")
    error_file_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=5*1024*1024, backupCount=3  # 5MB files, keep 3 backups
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_file_handler)

    # 4. Dash-specific log file
    dash_log_file = os.path.join(logs_dir, f"dash_debug_{date_str}.log")
    dash_file_handler = logging.handlers.RotatingFileHandler(
        dash_log_file, maxBytes=10*1024*1024, backupCount=3
    )
    dash_file_handler.setLevel(logging.DEBUG)
    dash_file_handler.setFormatter(detailed_formatter)

    # Configure Dash logger specifically
    dash_logger = logging.getLogger('dash')
    dash_logger.addHandler(dash_file_handler)
    dash_logger.setLevel(logging.DEBUG)

    # Configure Flask/Werkzeug loggers (Dash runs on Flask)
    flask_logger = logging.getLogger('werkzeug')
    flask_logger.addHandler(dash_file_handler)
    flask_logger.setLevel(logging.INFO)

    # Store log file paths
    _log_files = (app_log_file, error_log_file, dash_log_file)
    _logging_initialized = True

    # Log startup information
    logging.info("="*60)
    logging.info("Wind Farm Turbine Investigation Application Starting")
    logging.info(f"Timestamp: {datetime.now()}")
    logging.info(f"Log files created in: {os.path.abspath(logs_dir)}")
    logging.info(f"Application log: {app_log_file}")
    logging.info(f"Error log: {error_log_file}")
    logging.info(f"Dash debug log: {dash_log_file}")
    logging.info("="*60)

    return _log_files


def get_log_files():
    """Get the current log file paths without setting up logging."""
    global _log_files
    return _log_files if _log_files else (None, None, None)


def log_exception_handler(exc_type, exc_value, exc_traceback):
    """Custom exception handler to log uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupts
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Wind Farm Turbine Investigation",
    suppress_callback_exceptions=True,
)

# Set the layout
app.layout = create_main_dashboard_layout()

# Server for deployment
server = app.server

if __name__ == "__main__":
    # Determine if the application is running in debug mode for the server.
    # This should match the debug flag passed to app.run().
    APP_DEBUG_MODE = True  # As app.run(debug=True) is used below.

    # Setup logging and application-specific startup messages only in the main worker process
    # (when Werkzeug reloader is active and this is the child process) or when not in debug mode.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not APP_DEBUG_MODE:
        log_files = setup_logging() # setup_logging() contains "Application Starting" messages
        if log_files: # Only proceed if logging was successfully set up
            sys.excepthook = log_exception_handler

            # Log app initialization details after logging setup
            logging.info("Dash app initialized successfully")
            logging.info(f"App title: {app.title}")
            logging.info(f"Suppress callback exceptions: {app.config.suppress_callback_exceptions}")
            logging.info("Starting Dash development server...")
            logging.info("Server will be available at: http://localhost:8050")
            logging.info("Press Ctrl+C to stop the server")
    # else:
        # This branch is executed by the parent reloader process when APP_DEBUG_MODE is True.
        # No main logging setup is performed here to avoid duplicates.
        # _logging_initialized remains False for this parent process.
        pass

    try:
        app.run(debug=APP_DEBUG_MODE, port=8050)
    except Exception as e:
        # Log the error only if logging was initialized in this process's execution path.
        if _logging_initialized:
            logging.error(f"Failed to start Dash server: {e}", exc_info=True)
        else:
            # Fallback for errors in the parent reloader process before logging is set up by child.
            import traceback # Ensure traceback is imported for this block
            sys.stderr.write(f"Critical error during Dash server startup (parent reloader or pre-logging): {e}\n")
            traceback.print_exc(file=sys.stderr)
        raise
    finally:
        # Log shutdown only if logging was initialized by this process.
        # This typically means it will log if not in debug mode.
        # The parent reloader process (if APP_DEBUG_MODE=True) will have _logging_initialized=False.
        if _logging_initialized:
            logging.info("Dash application shutdown sequence initiated.")
            logging.info("="*60)
else:
    # For imports (like in tests), setup minimal logging
    if not _logging_initialized:
        # Create a basic console logger for imports
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        _logging_initialized = True # Mark that basic logging has been configured
        logging.info("app.py imported. Basic logging configured for module context.")

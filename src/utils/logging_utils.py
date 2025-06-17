"""
Logging utilities for the Wind Farm Turbine Investigation Application.
Provides decorators and helper functions for enhanced logging.
"""

import logging
import functools
import time
from typing import Any, Callable
import traceback
from dash import callback_context


def log_callback_execution(func: Callable) -> Callable:
    """
    Decorator to log callback execution details including timing and errors.
    
    Args:
        func: The callback function to wrap
        
    Returns:
        Wrapped function with logging
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(f"dash.callback.{func.__name__}")
        
        # Get callback context info
        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'] if ctx.triggered else "unknown"
        
        start_time = time.time()
        
        logger.info(f"Callback '{func.__name__}' triggered by: {triggered_id}")
        logger.debug(f"Callback '{func.__name__}' args: {len(args)} kwargs: {len(kwargs)}")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"Callback '{func.__name__}' completed successfully in {execution_time:.3f}s")
            logger.debug(f"Callback '{func.__name__}' result type: {type(result)}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(f"Callback '{func.__name__}' failed after {execution_time:.3f}s")
            logger.error(f"Error in callback '{func.__name__}': {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            
            # Re-raise the exception to maintain normal error handling
            raise
    
    return wrapper


def log_data_operation(operation_name: str):
    """
    Decorator to log data operations like loading, processing, filtering.
    
    Args:
        operation_name: Name of the operation for logging
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f"data.{operation_name}")
            
            start_time = time.time()
            logger.info(f"Starting {operation_name} operation")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log data size if result is a DataFrame
                if hasattr(result, 'shape'):
                    logger.info(f"{operation_name} completed in {execution_time:.3f}s - Result shape: {result.shape}")
                elif hasattr(result, '__len__'):
                    logger.info(f"{operation_name} completed in {execution_time:.3f}s - Result length: {len(result)}")
                else:
                    logger.info(f"{operation_name} completed in {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.error(f"{operation_name} failed after {execution_time:.3f}s")
                logger.error(f"Error in {operation_name}: {str(e)}")
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                
                raise
        
        return wrapper
    return decorator


def log_file_operation(func: Callable) -> Callable:
    """
    Decorator to log file operations like uploads, saves, loads.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function with logging
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(f"file.{func.__name__}")
        
        start_time = time.time()
        logger.info(f"Starting file operation: {func.__name__}")
        
        # Try to extract filename from args/kwargs
        filename = "unknown"
        if args and isinstance(args[0], str):
            filename = args[0]
        elif 'filename' in kwargs:
            filename = kwargs['filename']
        elif 'file_path' in kwargs:
            filename = kwargs['file_path']
        
        logger.debug(f"File operation '{func.__name__}' on file: {filename}")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"File operation '{func.__name__}' completed in {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(f"File operation '{func.__name__}' failed after {execution_time:.3f}s")
            logger.error(f"Error in file operation '{func.__name__}': {str(e)}")
            logger.error(f"File: {filename}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            
            raise
    
    return wrapper


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_user_action(action: str, details: dict = None):
    """
    Log user actions for analytics and debugging.
    
    Args:
        action: Description of the user action
        details: Optional dictionary with additional details
    """
    logger = logging.getLogger("user.actions")
    
    log_message = f"User action: {action}"
    if details:
        log_message += f" - Details: {details}"
    
    logger.info(log_message)


def log_performance_metric(metric_name: str, value: float, unit: str = ""):
    """
    Log performance metrics.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Optional unit description
    """
    logger = logging.getLogger("performance")
    
    unit_str = f" {unit}" if unit else ""
    logger.info(f"Performance metric - {metric_name}: {value:.3f}{unit_str}")


def log_data_summary(data, operation: str = ""):
    """
    Log summary information about data.
    
    Args:
        data: Data to summarize (DataFrame, list, etc.)
        operation: Optional operation description
    """
    logger = logging.getLogger("data.summary")
    
    operation_str = f" after {operation}" if operation else ""
    
    if hasattr(data, 'shape'):
        # DataFrame or similar
        logger.info(f"Data summary{operation_str}: Shape {data.shape}")
        if hasattr(data, 'columns'):
            logger.debug(f"Columns: {list(data.columns)}")
    elif hasattr(data, '__len__'):
        # List or similar
        logger.info(f"Data summary{operation_str}: Length {len(data)}")
    else:
        logger.info(f"Data summary{operation_str}: Type {type(data)}")


def log_error_with_context(error: Exception, context: dict = None):
    """
    Log an error with additional context information.
    
    Args:
        error: The exception that occurred
        context: Optional dictionary with context information
    """
    logger = logging.getLogger("error.context")
    
    logger.error(f"Error occurred: {str(error)}")
    
    if context:
        logger.error(f"Context: {context}")
    
    logger.error(f"Traceback:\n{traceback.format_exc()}")

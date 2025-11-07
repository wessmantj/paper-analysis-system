# test_logger.py

from src.pipeline import setup_logger

# Test 1: Console only
print("Test 1: Console logging only")
logger = setup_logger('TestLogger')

logger.debug('This is a debug message (won\'t show in console)')
logger.info('This is an info message')
logger.warning('This is a warning')
logger.error('This is an error')
logger.critical('This is critical!')

# Test 2: Console + File
print("\n\nTest 2: Console + File logging")
logger2 = setup_logger('FileLogger', 'logs/test.log')

logger2.debug('Debug message (only in file)')
logger2.info('Info message (console + file)')
logger2.error('Error message (console + file)')

print("\n✓ Check logs/test.log to see all messages including DEBUG")
import logging

# Set up logger
PROD_ENV = False
logger = logging.getLogger("BigQuery Sink")
logging.basicConfig()

if PROD_ENV:
    logger.setLevel(logging.INFO)
    logger.info("Running in Production Mode...")
else:
    logger.setLevel(logging.DEBUG)
    logger.info("Running in Debug Mode...")
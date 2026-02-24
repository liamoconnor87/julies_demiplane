def uuid():
    import timeflake #type: ignore
    return timeflake.random().hex.lower()

def looger(msg):
    def _create_logger():
        import logging

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        return logger

    logger = _create_logger()

    return logger.warning(msg)


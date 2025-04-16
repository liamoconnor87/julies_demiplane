def uuid():
    import timeflake #type: ignore
    return timeflake.random().hex.lower()
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

def div_container(value):
    o = ["<div class='container'>"]
    o.append(value)
    o.append("</div>")
    return o

def div_row(value):
    o = ["<div class='row'>"]
    o.append(value)
    o.append("</div>")
    return o

def div_col(value, width=None, classes=""):
    w = "-"
    if width:
        w = f"-{width}"
    o = [f"<div class='col{w} {classes}'>"]
    o.append(value)
    o.append("</div>")
    return o

def group_fields(field_name:str, begin: tuple, end: tuple, create_field: str):
    o = []

    if field_name in begin:
        o.append("<div class='row'>")
    o.extend(div_col(create_field, 8, "col-sm-2"))
    if field_name in end:
        o.append("</div>")

    return o


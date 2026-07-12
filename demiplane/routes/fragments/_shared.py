def _rows_or_empty(result):
    if isinstance(result, list):
        return result
    return []


def _count_or_zero(result):
    if isinstance(result, int):
        return result
    if isinstance(result, list):
        return len(result)
    return 0

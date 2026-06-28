DEFAULT_FEEDBACK_KIND = 'success'
ERROR_FEEDBACK_KIND = 'error'
DEFAULT_ERROR_FEEDBACK_MESSAGE = 'Something went wrong. Please try again.'


def default_feedback(message=''):
    return {
        'message': str(message or '').strip(),
        'kind': DEFAULT_FEEDBACK_KIND,
    }


def error_feedback(message=DEFAULT_ERROR_FEEDBACK_MESSAGE):
    safe_message = str(message or DEFAULT_ERROR_FEEDBACK_MESSAGE).strip()
    if not safe_message:
        safe_message = DEFAULT_ERROR_FEEDBACK_MESSAGE

    return {
        'message': safe_message,
        'kind': ERROR_FEEDBACK_KIND,
    }


def feedback_template_context(prefix, feedback):
    safe_prefix = str(prefix or '').strip()
    message = str((feedback or {}).get('message') or '').strip()
    kind = str((feedback or {}).get('kind') or DEFAULT_FEEDBACK_KIND).strip() or DEFAULT_FEEDBACK_KIND

    return {
        f'{safe_prefix}_feedback_message': message,
        f'{safe_prefix}_feedback_kind': kind,
    }

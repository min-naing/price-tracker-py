from datetime import datetime


def truncate_to_milliseconds(value: datetime) -> datetime:
    return value.replace(
        microsecond=(value.microsecond // 1000) * 1000,
    )

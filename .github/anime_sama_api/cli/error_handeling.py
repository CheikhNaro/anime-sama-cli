from collections.abc import Sequence
from logging import LogRecord
from typing import Literal

Reaction = Literal["continue", "retry", "crash", ""]

how_to_react: dict[Reaction, Sequence[str]] = {
    "continue": (
        "[Errno 61] Connection refused",
        "Remote end closed connection without response",
        "HTTPError 404: Not Found",
        "Unsupported URL",
        "[Errno 7] No address associated with hostname",
        "[Errno 11002] getaddrinfo failed",
        "Requested format is not available",
        "Unable to extract player params",
        "Unable to extract",
    ),
    "retry": (
        "Unable to download webpage: HTTP Error 522",
        "unable to download video data: HTTP Error 416",
        "HTTPError 500: Internal Server Error",
        "The read operation timed out",
        "Waiting for vidmoly",  # Custom error msg to tell the downloader to retry
        "TransportError('timed out')",
        "[Errno 54] Connection reset by peer",
        "[Errno 104] Connection reset by peer",
        "HTTPError 503: Service Temporarily Unavailable",
        "[Errno 32] Broken pipe",
        "[Errno 101] Network is unreachable",
        "[Errno 51] Network is unreachable",
        "[Errno 2] No such file or directory",
    ),
    "crash": (),
}


def reaction_to(msg: str | None) -> Reaction:
    if msg is None:
        return "continue"

    for reaction, error_msgs in how_to_react.items():
        for error_msg in error_msgs:
            if error_msg in msg:
                return reaction
    return ""


def is_error_handle(msg: str) -> bool:
    return bool(reaction_to(msg))


def YDL_log_filter(record: LogRecord) -> bool:
    if record.filename != "YoutubeDL.py":
        return True

    match record.levelname:
        case "WARNING":
            if any(
                msg in record.msg
                for msg in (
                    "Falling back on generic information extractor",
                    "Live HLS streams are not supported by the native downloader.",
                )
            ):
                return False
            return True
        case "ERROR":
            # Ne pas afficher les erreurs qu'on gère (passage au lecteur suivant)
            if is_error_handle(record.msg):
                return False
            return True
        case "CRITICAL":
            # Ne pas afficher CRITICAL quand on a simplement essayé un lecteur et on passe au suivant
            if is_error_handle(record.msg):
                return False
            return True
        case _:
            return True

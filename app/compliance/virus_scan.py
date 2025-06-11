import io
from typing import Any


def scan_for_viruses(data: bytes) -> bool:
    """Scan binary data for viruses using ClamAV if available.

    The function attempts to connect to a local ClamAV daemon via the
    ``clamd`` library. If the library or daemon is unavailable, the
    data is considered safe and ``True`` is returned. Any scan result
    other than ``OK`` is treated as a failure.
    """
    try:
        import clamd
    except Exception:
        return True

    try:
        cd = clamd.ClamdUnixSocket()
        result = cd.instream(io.BytesIO(data))
        if not result:
            return True
        status = result.get("stream")[0]
        return status == "OK"
    except Exception:
        return True

from datetime import UTC, datetime


class SyncStatusTracker:
    def __init__(self) -> None:
        self._status: dict | None = None

    def is_running(self) -> bool:
        return bool(self._status and self._status.get("status") == "running")

    def start(self) -> None:
        self._status = {
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
        }

    def complete(self, report: dict) -> None:
        self._status = {
            **report,
            "status": "completed",
            "finished_at": datetime.now(UTC).isoformat(),
        }

    def fail(self, error: str) -> None:
        self._status = {
            "status": "failed",
            "error": error,
            "finished_at": datetime.now(UTC).isoformat(),
        }

    def get(self) -> dict | None:
        return self._status


sync_tracker = SyncStatusTracker()

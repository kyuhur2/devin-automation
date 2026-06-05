import json
from pathlib import Path
from typing import Dict

from app.models import Task


class TaskStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({})

    def _read(self) -> Dict[str, dict]:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: Dict[str, dict]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def list_tasks(self) -> list[Task]:
        return [Task(**value) for value in self._read().values()]

    def get_task(self, task_id: str) -> Task | None:
        data = self._read()
        task = data.get(task_id)
        return Task(**task) if task else None

    def upsert_task(self, task: Task) -> Task:
        data = self._read()
        data[task.task_id] = task.model_dump()
        self._write(data)
        return task

    def delete_task(self, task_id: str) -> bool:
        data = self._read()

        if task_id not in data:
            return False

        del data[task_id]
        self._write(data)
        return True

    def clear_tasks(self) -> int:
        data = self._read()
        deleted_count = len(data)
        self._write({})
        return deleted_count
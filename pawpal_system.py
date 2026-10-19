"""Data models and scheduling interfaces for PawPal+."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Owner:
    name: str
    preferences: list[str] = field(default_factory=list)
    available_minutes: int = 0

    def update_preferences(self, preferences: list[str]) -> None:
        ...

    def set_available_time(self, minutes: int) -> None:
        ...


@dataclass
class CareTask:
    title: str
    duration_minutes: int
    priority: str
    category: str = ""
    is_recurring: bool = False

    def is_essential(self) -> bool:
        ...

    def describe(self) -> str:
        ...


@dataclass
class Pet:
    name: str
    species: str
    age: int | None = None
    care_notes: str = ""
    tasks: list[CareTask] = field(default_factory=list)

    def add_task(self, task: CareTask) -> None:
        ...

    def remove_task(self, task: CareTask) -> None:
        ...

    def list_tasks(self) -> list[CareTask]:
        ...


@dataclass
class ScheduleEntry:
    task: CareTask
    start_time: str
    end_time: str
    reason: str

    def duration(self) -> int:
        ...

    def format_for_display(self) -> str:
        ...


@dataclass
class DailyPlan:
    pet: Pet
    entries: list[ScheduleEntry] = field(default_factory=list)
    total_scheduled_minutes: int = 0
    unused_minutes: int = 0

    def add_entry(self, entry: ScheduleEntry) -> None:
        ...

    def remaining_time(self) -> int:
        ...

    def summarize(self) -> str:
        ...


class Scheduler:
    def create_plan(
        self,
        pet: Pet,
        tasks: list[CareTask],
        available_minutes: int,
        preferences: list[str],
    ) -> DailyPlan:
        ...

    def explain_choice(self, task: CareTask) -> str:
        ...
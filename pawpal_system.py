"""Pet-care data models and daily scheduling logic for PawPal+."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, time, timedelta
from itertools import combinations
from typing import NamedTuple

PRIORITIES = ("low", "medium", "high")
HIGH_PRIORITY = "high"
DEFAULT_PRIORITY = "medium"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

FREQUENCIES = ("daily", "weekly", "once")
DEFAULT_FREQUENCY = "daily"
ONE_TIME_FREQUENCIES = {"once", "one-time", "one time"}
RECURRENCE_DAYS = {"daily": 1, "weekly": 7}

SPECIES = ("dog", "cat", "other")

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR
DEFAULT_DAY_START = time(8, 0)


def _is_whole_minute(value: time) -> bool:
    """Return whether a time has no seconds or microseconds."""
    return not (value.second or value.microsecond)


def _to_minutes(value: time) -> int:
    """Convert a time of day to minutes after midnight."""
    return value.hour * MINUTES_PER_HOUR + value.minute


def _from_minutes(minutes: int) -> time:
    """Convert minutes after midnight to a time of day."""
    return time(minutes // MINUTES_PER_HOUR, minutes % MINUTES_PER_HOUR)


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    """Return whether half-open spans [a_start, a_end) and [b_start, b_end) meet.

    Two spans overlap exactly when each one starts before the other ends.
    This single comparison covers every case: partial overlap, one span
    inside the other, and identical spans. Back-to-back spans, where one ends
    exactly when the other starts, do not overlap.

    Args:
        a_start, a_end: Start and end of the first span.
        b_start, b_end: Start and end of the second span.
            Any comparable values work, e.g. minutes after midnight or
            ``datetime.time`` objects, as long as all four are the same kind.

    Returns:
        True if the spans share at least one instant, otherwise False.
    """
    return a_start < b_end and b_start < a_end


def _format_span(start: int, end: int) -> str:
    """Format a minute range as HH:MM-HH:MM, wrapping past midnight."""
    return (
        f"{_from_minutes(start % MINUTES_PER_DAY):%H:%M}-"
        f"{_from_minutes(end % MINUTES_PER_DAY):%H:%M}"
    )


@dataclass
class Task:
    """A care activity for a pet."""

    description: str
    duration_minutes: int
    frequency: str = DEFAULT_FREQUENCY
    completed: bool = False
    priority: str = DEFAULT_PRIORITY
    category: str = "care"
    due_date: date | None = None
    fixed_time: time | None = None

    def __post_init__(self) -> None:
        """Validate task details and normalize its priority."""
        if not self.description.strip():
            raise ValueError("Task description cannot be empty.")
        if self.duration_minutes <= 0:
            raise ValueError("Task duration must be greater than zero.")
        if not self.frequency.strip():
            raise ValueError("Task frequency cannot be empty.")
        self.priority = self.priority.strip().lower()
        if self.priority not in PRIORITIES:
            raise ValueError(f"Task priority must be one of: {', '.join(PRIORITIES)}.")
        if self.fixed_time is not None and not _is_whole_minute(self.fixed_time):
            raise ValueError("Task fixed time must use whole minutes.")

    @property
    def time(self) -> int:
        """Task duration in minutes."""
        return self.duration_minutes

    @property
    def is_recurring(self) -> bool:
        """Report whether the task frequency indicates repetition."""
        return self.frequency.strip().lower() not in ONE_TIME_FREQUENCIES

    def is_essential(self) -> bool:
        """Return whether this task has high priority."""
        return self.priority == HIGH_PRIORITY

    def is_due(self, on: date) -> bool:
        """Return whether this task should be considered on the given date.

        A task with no ``due_date`` is always due. Otherwise it is due on its
        due date and on every later date, so a task that was missed stays in
        the plan until it is done instead of silently disappearing.

        Args:
            on: The date being planned.

        Returns:
            True if the task belongs in a plan for ``on``.
        """
        return self.due_date is None or self.due_date <= on

    def next_occurrence(self, completed_on: date) -> Task | None:
        """Return a fresh copy of a recurring task due after its interval.

        The interval comes from ``RECURRENCE_DAYS`` (daily = 1 day, weekly =
        7 days). The next due date is ``completed_on + timedelta(days=...)``.
        Using ``timedelta`` rolls correctly across month ends, year ends and
        leap days. The copy keeps every other field, such as priority,
        duration and fixed time, and starts out incomplete. This task itself
        is not modified.

        Args:
            completed_on: The date this occurrence was finished.

        Returns:
            The next ``Task``, or None for one-time tasks and for frequencies
            with no fixed interval.
        """
        interval = RECURRENCE_DAYS.get(self.frequency.strip().lower())
        if interval is None:
            return None
        return replace(
            self,
            completed=False,
            due_date=completed_on + timedelta(days=interval),
        )

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def mark_completed(self) -> None:
        """Backward-compatible alias for :meth:`mark_complete`."""
        self.mark_complete()

    def mark_incomplete(self) -> None:
        """Mark this task as not completed."""
        self.completed = False

    def describe(self) -> str:
        """Return a concise description of this task and its status."""
        status = "completed" if self.completed else "incomplete"
        return (
            f"{self.description} ({self.duration_minutes} min, "
            f"{self.priority} priority, {self.frequency}, {status})"
        )


@dataclass
class Pet:
    """A pet and the care tasks assigned to it."""

    name: str
    species: str
    age: int | None = None
    care_notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the pet's identifying details."""
        if not self.name.strip():
            raise ValueError("Pet name cannot be empty.")
        if not self.species.strip():
            raise ValueError("Pet species cannot be empty.")
        if self.age is not None and self.age < 0:
            raise ValueError("Pet age cannot be negative.")

    def add_task(self, task: Task) -> None:
        """Add a task unless it is already assigned to this pet."""
        if task in self.tasks:
            raise ValueError(f"Task is already assigned to {self.name}.")
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove an assigned task or raise an error if it is absent."""
        try:
            self.tasks.remove(task)
        except ValueError as exc:
            raise ValueError(f"Task is not assigned to {self.name}.") from exc

    def complete_task(self, task: Task, on: date | None = None) -> Task | None:
        """Mark a task complete and queue its next occurrence if it recurs.

        The completed task stays in the list as history, and the next
        occurrence (from :meth:`Task.next_occurrence`) is appended to this pet.

        Args:
            task: A task assigned to this pet. It is matched by identity, not
                equality.
            on: The completion date. Defaults to today.

        Returns:
            The newly added next occurrence, or None if the task doesn't recur.

        Raises:
            ValueError: If ``task`` is not assigned to this pet.
        """
        if not any(existing is task for existing in self.tasks):
            raise ValueError(f"Task is not assigned to {self.name}.")
        task.mark_complete()
        next_task = task.next_occurrence(on or date.today())
        if next_task is not None:
            self.add_task(next_task)
        return next_task

    def list_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)


@dataclass
class Owner:
    """An owner, their scheduling preferences, and their pets."""

    name: str
    preferences: list[str] = field(default_factory=list)
    available_minutes: int = 0
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the owner's name and available time."""
        if not self.name.strip():
            raise ValueError("Owner name cannot be empty.")
        if self.available_minutes < 0:
            raise ValueError("Available time cannot be negative.")

    def update_preferences(self, preferences: list[str]) -> None:
        """Replace the owner's scheduling preferences."""
        self.preferences = list(preferences)

    def set_available_time(self, minutes: int) -> None:
        """Set the owner's non-negative daily time budget."""
        if minutes < 0:
            raise ValueError("Available time cannot be negative.")
        self.available_minutes = minutes

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        if pet in self.pets:
            raise ValueError(f"{pet.name} is already registered to {self.name}.")
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Unregister a pet or raise an error if it is absent."""
        try:
            self.pets.remove(pet)
        except ValueError as exc:
            raise ValueError(f"{pet.name} is not registered to {self.name}.") from exc

    def list_pets(self) -> list[Pet]:
        """Return a copy of this owner's pet list."""
        return list(self.pets)

    def get_pet_tasks(self) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs for every pet, in insertion order."""
        pairs: list[tuple[Pet, Task]] = []
        assigned_task_ids: set[int] = set()
        for pet in self.pets:
            for task in pet.list_tasks():
                if id(task) in assigned_task_ids:
                    raise ValueError(
                        "A Task instance cannot be assigned to multiple pets."
                    )
                assigned_task_ids.add(id(task))
                pairs.append((pet, task))
        return pairs

    def get_all_tasks(self) -> list[Task]:
        """Return tasks for every pet, in pet and task insertion order."""
        return [task for _, task in self.get_pet_tasks()]

    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs matching an optional pet name and status.

        Each filter is applied only when it is given. Leaving both out returns
        every task. Results keep pet and task insertion order.

        Args:
            pet_name: Keep only tasks for the pet with this exact name.
            completed: True keeps only finished tasks, False keeps only
                unfinished ones, and None keeps both.

        Returns:
            A new list of matching ``(pet, task)`` pairs. It is empty if
            nothing matches.
        """
        return [
            (pet, task)
            for pet, task in self.get_pet_tasks()
            if (pet_name is None or pet.name == pet_name)
            and (completed is None or task.completed == completed)
        ]


class TimedTask(NamedTuple):
    """A set-time task with its span in minutes after midnight."""

    start: int
    end: int
    pet: Pet
    task: Task

    @classmethod
    def from_task(cls, pet: Pet, task: Task) -> TimedTask:
        """Build a span from a task's fixed time and duration.

        The end time is ``start + duration`` in minutes after midnight. It may
        go past 1440 for a task that runs past midnight, which keeps overlap
        comparisons correct.

        Args:
            pet: The pet the task belongs to.
            task: A task whose ``fixed_time`` is set.
        """
        start = _to_minutes(task.fixed_time)
        return cls(start, start + task.duration_minutes, pet, task)


def _conflict_message(a: TimedTask, b: TimedTask) -> str:
    """Describe an overlap between two set-time tasks.

    Returns:
        A one-line warning naming both pets, both tasks and their time spans.
        It is tagged ``[same pet]`` or ``[different pets]`` (compared by
        identity) so the owner can tell a double-booked pet from a
        double-booked owner.
    """
    scope = "same pet" if a.pet is b.pet else "different pets"
    return (
        f"{a.pet.name}'s '{a.task.description}' ({_format_span(a.start, a.end)}) "
        f"overlaps {b.pet.name}'s '{b.task.description}' "
        f"({_format_span(b.start, b.end)}) [{scope}]"
    )


@dataclass
class ScheduleEntry:
    """A task scheduled for a pet at a particular time."""

    pet: Pet
    task: Task
    start_time: time
    end_time: time
    reason: str

    def __post_init__(self) -> None:
        """Validate that the scheduled time span matches the task duration."""
        if not all(_is_whole_minute(v) for v in (self.start_time, self.end_time)):
            raise ValueError("Schedule times must use whole minutes.")
        if self.end_time <= self.start_time:
            raise ValueError("Schedule entry must end after it starts.")
        if self.duration() != self.task.duration_minutes:
            raise ValueError("Scheduled time must match the task duration.")

    def duration(self) -> int:
        """Return the scheduled duration in whole minutes."""
        return _to_minutes(self.end_time) - _to_minutes(self.start_time)

    def overlaps(self, other: ScheduleEntry) -> bool:
        """Return whether this entry's time span intersects another's."""
        return _overlaps(
            self.start_time, self.end_time, other.start_time, other.end_time
        )

    def format_for_display(self) -> str:
        """Format this entry as a readable schedule line."""
        return (
            f"{self.start_time:%H:%M}-{self.end_time:%H:%M} - "
            f"{self.pet.name}: {self.task.description} "
            f"({self.task.duration_minutes} min; {self.reason})"
        )


@dataclass
class SkippedTask:
    """A task the scheduler could not fit into the plan, and why."""

    pet: Pet
    task: Task
    reason: str

    def format_for_display(self) -> str:
        """Format this skipped task as a readable line."""
        return f"{self.pet.name}: {self.task.description} ({self.reason})"


@dataclass
class DailyPlan:
    """A time-budgeted plan containing entries for an owner's pets."""

    available_minutes: int
    entries: list[ScheduleEntry] = field(default_factory=list)
    skipped: list[SkippedTask] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the daily time budget."""
        if self.available_minutes < 0:
            raise ValueError("Available time cannot be negative.")

    @property
    def total_scheduled_minutes(self) -> int:
        """Calculate the total duration of scheduled entries."""
        return sum(entry.duration() for entry in self.entries)

    @property
    def unused_minutes(self) -> int:
        """Calculate the time budget remaining after scheduled entries."""
        return self.available_minutes - self.total_scheduled_minutes

    def sorted_entries(self) -> list[ScheduleEntry]:
        """Return entries in chronological order.

        Entries are stored in the order they were added. Set-time tasks are
        added before flexible ones, so that order isn't clock order. This
        returns a new list sorted by ``start_time``. It does not change
        ``entries``.
        """
        return sorted(self.entries, key=lambda entry: entry.start_time)

    def find_overlap(self, entry: ScheduleEntry) -> ScheduleEntry | None:
        """Return an existing entry that overlaps the given one, if any.

        Checks the candidate against each entry in turn and stops at the first
        clash. Each check is O(1), so the whole scan is O(n) in the number of
        entries.

        Returns:
            The first overlapping ``ScheduleEntry``, or None if the slot is free.
        """
        return next(
            (existing for existing in self.entries if existing.overlaps(entry)),
            None,
        )

    def add_entry(self, entry: ScheduleEntry) -> None:
        """Add a valid, non-overlapping entry within the time budget."""
        if entry.task.completed:
            raise ValueError("Completed tasks cannot be added to a daily plan.")
        if self.total_scheduled_minutes + entry.duration() > self.available_minutes:
            raise ValueError("Schedule entry exceeds the available time.")
        if any(existing.task is entry.task for existing in self.entries):
            raise ValueError("A task can only appear once in a daily plan.")
        if self.find_overlap(entry) is not None:
            raise ValueError("Schedule entries cannot overlap.")
        self.entries.append(entry)

    def remaining_time(self) -> int:
        """Return the number of available minutes not yet scheduled."""
        return self.unused_minutes

    def summarize(self) -> str:
        """Return a readable summary of the daily schedule."""
        if not self.entries:
            lines = ["No incomplete tasks fit into today's available time."]
        else:
            lines = ["Daily PawPal+ plan:"]
            lines.extend(f"- {e.format_for_display()}" for e in self.sorted_entries())
            lines.append(
                f"Scheduled {self.total_scheduled_minutes} of "
                f"{self.available_minutes} available minutes "
                f"({self.unused_minutes} minutes remaining)."
            )
        if self.skipped:
            lines.append("Not scheduled:")
            lines.extend(f"- {s.format_for_display()}" for s in self.skipped)
        if self.conflicts:
            lines.append("Conflicts:")
            lines.extend(f"- {conflict}" for conflict in self.conflicts)
        return "\n".join(lines)


class Scheduler:
    """Builds a priority-ordered schedule across all pets owned by a user."""

    def __init__(self, start_time: time = DEFAULT_DAY_START) -> None:
        """Create a scheduler with a whole-minute start time."""
        if not _is_whole_minute(start_time):
            raise ValueError("Scheduler start time must use whole minutes.")
        self.start_time = start_time

    def create_plan(self, owner: Owner, plan_date: date | None = None) -> DailyPlan:
        """Schedule due, incomplete tasks across all pets within the time budget.

        Algorithm:
            1. Collect every incomplete task that is due on ``plan_date``.
            2. Record conflict warnings between set-time tasks.
            3. Stable-sort the tasks by priority (high, medium, low).
               Equal priorities keep their insertion order.
            4. Place set-time tasks at their requested time. When two clash,
               the one placed first (higher priority) keeps the slot and the
               other is skipped.
            5. Place each flexible task in the earliest open slot at or after
               the scheduler's start time.
            A task that would exceed the remaining budget or run past
            midnight is skipped rather than placed.

        Args:
            owner: The owner whose pets' tasks and time budget are used.
            plan_date: The day being planned. Defaults to today.

        Returns:
            A ``DailyPlan`` with scheduled ``entries``, ``skipped`` tasks and
            the reasons they were skipped, and ``conflicts`` warnings.
        """
        due = self._due_tasks(owner, plan_date or date.today())
        plan = DailyPlan(
            available_minutes=owner.available_minutes,
            conflicts=self._find_conflicts(due),
        )

        # sorted() is stable, so equal priorities keep their insertion order.
        by_priority = sorted(due, key=lambda pair: PRIORITY_ORDER[pair[1].priority])
        fixed = [pair for pair in by_priority if pair[1].fixed_time is not None]
        flexible = [pair for pair in by_priority if pair[1].fixed_time is None]

        for pet, task in fixed:
            self._try_schedule(plan, pet, task, _to_minutes(task.fixed_time))

        day_start = _to_minutes(self.start_time)
        for pet, task in flexible:
            start = self._find_open_slot(plan, task.duration_minutes, day_start)
            self._try_schedule(plan, pet, task, start)

        return plan

    @staticmethod
    def _due_tasks(owner: Owner, plan_date: date) -> list[tuple[Pet, Task]]:
        """Return the owner's incomplete (pet, task) pairs due on the plan date.

        This is the shared first step of planning and conflict detection, so
        both look at the same set of tasks and the pets are walked only once.
        """
        return [
            (pet, task)
            for pet, task in owner.get_pet_tasks()
            if not task.completed and task.is_due(plan_date)
        ]

    def _find_open_slot(self, plan: DailyPlan, duration: int, earliest: int) -> int:
        """Return the earliest start minute where a task fits between entries.

        Walks the entries in clock order with a candidate start. Whenever the
        candidate span ``[start, start + duration)`` overlaps an entry, the
        candidate jumps to that entry's end. Entries are sorted, so the first
        candidate that survives the walk is the earliest free gap that is long
        enough.

        Args:
            plan: The plan whose existing entries block time.
            duration: Length of the task to place, in minutes.
            earliest: The first minute the task may start.

        Returns:
            A start minute. It may be past midnight; the caller checks that.
        """
        start = earliest
        for entry in plan.sorted_entries():
            busy_start = _to_minutes(entry.start_time)
            busy_end = _to_minutes(entry.end_time)
            if _overlaps(start, start + duration, busy_start, busy_end):
                start = busy_end
        return start

    def _try_schedule(self, plan: DailyPlan, pet: Pet, task: Task, start: int) -> None:
        """Add the task at the given minute, or record why it was skipped.

        The checks run in this order: remaining time budget, the midnight
        cutoff, then overlap with an existing entry. The first failure adds
        a ``SkippedTask`` with a readable reason to ``plan.skipped``. It never
        raises, so one bad task can't stop the rest of the plan.

        Args:
            plan: The plan being built. It is changed in place.
            pet: The pet the task belongs to.
            task: The task to place.
            start: Requested start, in minutes after midnight.
        """
        end = start + task.duration_minutes
        if task.duration_minutes > plan.remaining_time():
            plan.skipped.append(
                SkippedTask(
                    pet,
                    task,
                    f"needs {task.duration_minutes} min, "
                    f"only {plan.remaining_time()} min left",
                )
            )
            return
        if end >= MINUTES_PER_DAY:
            plan.skipped.append(SkippedTask(pet, task, "would run past midnight"))
            return

        entry = ScheduleEntry(
            pet=pet,
            task=task,
            start_time=_from_minutes(start),
            end_time=_from_minutes(end),
            reason=self.explain_choice(task),
        )
        clash = plan.find_overlap(entry)
        if clash is not None:
            plan.skipped.append(
                SkippedTask(pet, task, f"conflicts with {clash.task.description}")
            )
            return
        plan.add_entry(entry)

    @staticmethod
    def detect_conflicts(owner: Owner, plan_date: date | None = None) -> list[str]:
        """Return a warning for each pair of set-time tasks whose times overlap.

        This is a lightweight check: it reports problems as strings instead of
        raising, and the caller decides how to show them. Only due, incomplete
        tasks with a ``fixed_time`` are checked. Flexible tasks are always
        slotted into free time, so they can't clash. Durations are compared,
        not just start times, so 09:00-09:10 and 09:05-09:20 are reported.
        Conflicts reflect the requested times, not the final plan.

        Args:
            owner: The owner whose pets' tasks are checked.
            plan_date: The day being checked. Defaults to today.

        Returns:
            One message per overlapping pair, in start-time order. An empty
            list means there are no clashes.
        """
        return Scheduler._find_conflicts(
            Scheduler._due_tasks(owner, plan_date or date.today())
        )

    @staticmethod
    def _find_conflicts(pairs: list[tuple[Pet, Task]]) -> list[str]:
        """Compare every pair of set-time tasks and describe each overlap.

        The set-time tasks are sorted by start so warnings come out in clock
        order. Then ``itertools.combinations`` checks each unordered pair once
        with :func:`_overlaps`. That is O(n^2) in the number of set-time
        tasks, which was chosen for readability over a sorted sweep; a pet
        owner rarely has more than a handful of timed tasks per day.

        Args:
            pairs: Candidate ``(pet, task)`` pairs. Tasks without a
                ``fixed_time`` are ignored.

        Returns:
            One warning per overlapping pair.
        """
        timed = sorted(
            (
                TimedTask.from_task(pet, task)
                for pet, task in pairs
                if task.fixed_time is not None
            ),
            key=lambda item: item.start,
        )
        return [
            _conflict_message(a, b)
            for a, b in combinations(timed, 2)
            if _overlaps(a.start, a.end, b.start, b.end)
        ]

    @staticmethod
    def sort_by_time(tasks: list[Task], reverse: bool = False) -> list[Task]:
        """Return tasks ordered by their time (duration in minutes), shortest first.

        Uses ``sorted()`` with ``Task.time`` as the key. The sort is stable, so
        tasks with equal durations keep their original relative order, and the
        input list is not modified.

        Args:
            tasks: The tasks to order.
            reverse: If True, return longest first instead.

        Returns:
            A new sorted list.
        """
        return sorted(tasks, key=lambda task: task.time, reverse=reverse)

    @staticmethod
    def filter_tasks(
        owner: Owner,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        """Return the owner's tasks matching an optional pet name and status.

        A thin wrapper over :meth:`Owner.filter_tasks` that drops the pet
        from each pair, so the result can be passed straight to
        :meth:`sort_by_time`.

        Args:
            owner: The owner whose pets' tasks are searched.
            pet_name: Keep only tasks for the pet with this exact name.
            completed: True for finished, False for unfinished, None for both.

        Returns:
            Matching ``Task`` objects in pet and task insertion order.
        """
        return [task for _, task in owner.filter_tasks(pet_name, completed)]

    @staticmethod
    def mark_task_complete(
        owner: Owner, task: Task, on: date | None = None
    ) -> Task | None:
        """Complete an owner's task and return its next occurrence, if any.

        A ``Task`` doesn't know which pet it belongs to. This method searches
        the owner's pets for the task (by identity) and hands it to
        :meth:`Pet.complete_task`, which adds the next daily or weekly copy
        to that pet.

        Args:
            owner: The owner whose pets are searched.
            task: The task to mark complete.
            on: The completion date. Defaults to today.

        Returns:
            The new next occurrence, or None for one-time tasks.

        Raises:
            ValueError: If none of the owner's pets has this task.
        """
        for pet, owned_task in owner.get_pet_tasks():
            if owned_task is task:
                return pet.complete_task(task, on)
        raise ValueError(f"{task.description} is not assigned to {owner.name}'s pets.")

    def explain_choice(self, task: Task) -> str:
        """Explain the reason for scheduling a task."""
        if task.fixed_time is not None:
            return f"set for {task.fixed_time:%H:%M} ({task.priority} priority)"
        if task.is_essential():
            return "scheduled first because it is high priority"
        return f"scheduled because it fits the remaining time ({task.priority} priority)"


# Backwards-compatible name for the earlier UML class name.
CareTask = Task

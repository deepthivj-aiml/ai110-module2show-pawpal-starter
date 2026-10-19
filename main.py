"""Run a small multi-pet PawPal+ scheduling demo in the terminal."""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print a heading followed by one line per task."""
    print(f"\n{title}")
    if not tasks:
        print("  (none)")
    for task in tasks:
        print(f"  - {task.describe()}")


def main() -> None:
    owner = Owner(
        name="Jordan",
        preferences=["morning walks"],
        available_minutes=90,
    )

    # Tasks are added deliberately out of duration order.
    dog = Pet(name="Mochi", species="dog")
    dog.add_task(
        Task(
            description="Morning walk",
            duration_minutes=30,
            priority="high",
            category="exercise",
        )
    )
    dog.add_task(
        Task(
            description="Brush coat",
            duration_minutes=15,
            priority="low",
            category="grooming",
        )
    )
    dog.add_task(
        Task(
            description="Breakfast",
            duration_minutes=10,
            priority="high",
            category="feeding",
        )
    )

    cat = Pet(name="Luna", species="cat")
    cat.add_task(
        Task(
            description="Play and enrichment",
            duration_minutes=20,
            priority="medium",
            category="enrichment",
        )
    )
    cat.add_task(
        Task(
            description="Refresh water",
            duration_minutes=5,
            priority="medium",
            category="feeding",
        )
    )
    litter = Task(
        description="Clean litter box",
        duration_minutes=10,
        priority="medium",
        category="care",
    )
    cat.add_task(litter)
    litter.mark_complete()

    owner.add_pet(dog)
    owner.add_pet(cat)

    all_tasks = owner.get_all_tasks()
    print_tasks("All tasks (insertion order)", all_tasks)
    print_tasks("Sorted by time, shortest first", Scheduler.sort_by_time(all_tasks))
    print_tasks(
        "Sorted by time, longest first",
        Scheduler.sort_by_time(all_tasks, reverse=True),
    )
    print_tasks("Filtered: Mochi only", Scheduler.filter_tasks(owner, pet_name="Mochi"))
    print_tasks("Filtered: completed", Scheduler.filter_tasks(owner, completed=True))
    print_tasks(
        "Filtered + sorted: Luna's incomplete tasks, shortest first",
        Scheduler.sort_by_time(
            Scheduler.filter_tasks(owner, pet_name="Luna", completed=False)
        ),
    )

    # Three tasks pinned to overlapping clock times: two for Mochi, one for Luna.
    dog.add_task(
        Task(
            description="Give medication",
            duration_minutes=5,
            priority="high",
            fixed_time=time(9, 0),
        )
    )
    dog.add_task(
        Task(description="Trim nails", duration_minutes=10, fixed_time=time(9, 0))
    )
    cat.add_task(
        Task(description="Vet video call", duration_minutes=15, fixed_time=time(9, 5))
    )

    print("\nConflict check")
    conflicts = Scheduler.detect_conflicts(owner)
    if not conflicts:
        print("  No conflicts found.")
    for warning in conflicts:
        print(f"  WARNING: {warning}")

    plan = Scheduler().create_plan(owner)
    print("\nToday's Schedule")
    print(plan.summarize())

    print("\nRecurring tasks")
    walk = all_tasks[0]
    next_walk = Scheduler.mark_task_complete(owner, walk)
    print(f"  Completed '{walk.description}' ({walk.frequency}).")
    print(f"  Next occurrence created, due {next_walk.due_date}.")
    bath = Task(description="Bath", duration_minutes=25, frequency="weekly")
    dog.add_task(bath)
    next_bath = Scheduler.mark_task_complete(owner, bath)
    print(f"  Completed '{bath.description}' ({bath.frequency}).")
    print(f"  Next occurrence created, due {next_bath.due_date}.")
    print_tasks("Mochi's tasks now", dog.list_tasks())


if __name__ == "__main__":
    main()

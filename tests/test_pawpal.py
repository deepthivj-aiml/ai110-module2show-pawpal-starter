from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

TODAY = date(2026, 10, 19)


def make_owner(minutes: int, *pets: Pet) -> Owner:
    owner = Owner(name="Jordan", available_minutes=minutes)
    for pet in pets:
        owner.add_pet(pet)
    return owner


def test_mark_complete_updates_task_status() -> None:
    task = Task(description="Feed pet", duration_minutes=10)

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count() -> None:
    pet = Pet(name="Mochi", species="dog")
    task = Task(description="Morning walk", duration_minutes=20)
    initial_task_count = len(pet.list_tasks())

    pet.add_task(task)

    assert len(pet.list_tasks()) == initial_task_count + 1
    assert pet.list_tasks()[0] is task


def test_invalid_priority_is_rejected() -> None:
    with pytest.raises(ValueError):
        Task(description="Brush", duration_minutes=5, priority="urgent")


def test_tasks_that_do_not_fit_are_reported_as_skipped() -> None:
    pet = Pet(name="Mochi", species="dog")
    walk = Task(description="Long walk", duration_minutes=60)
    feed = Task(description="Feed", duration_minutes=10, priority="high")
    pet.add_task(walk)
    pet.add_task(feed)

    plan = Scheduler().create_plan(make_owner(30, pet), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [feed]
    assert [s.task for s in plan.skipped] == [walk]
    assert "only 20 min left" in plan.skipped[0].reason


def test_task_ending_at_midnight_is_skipped_not_crashing() -> None:
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task(description="Late walk", duration_minutes=60))

    plan = Scheduler(start_time=time(23, 0)).create_plan(
        make_owner(120, pet), plan_date=TODAY
    )

    assert not plan.entries
    assert plan.skipped[0].reason == "would run past midnight"


def test_fixed_time_tasks_are_placed_and_entries_sorted() -> None:
    pet = Pet(name="Mochi", species="dog")
    meds = Task(description="Meds", duration_minutes=10, fixed_time=time(8, 10))
    walk = Task(description="Walk", duration_minutes=10, priority="high")
    play = Task(description="Play", duration_minutes=20)
    for task in (meds, walk, play):
        pet.add_task(task)

    plan = Scheduler().create_plan(make_owner(60, pet), plan_date=TODAY)
    ordered = plan.sorted_entries()

    assert [e.task for e in ordered] == [walk, meds, play]
    assert [e.start_time for e in ordered] == [time(8, 0), time(8, 10), time(8, 20)]


def test_overlapping_fixed_times_report_conflict() -> None:
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Luna", species="cat")
    vet = Task(
        description="Vet call", duration_minutes=30,
        priority="high", fixed_time=time(9, 0),
    )
    groom = Task(description="Groom", duration_minutes=15, fixed_time=time(9, 15))
    dog.add_task(vet)
    cat.add_task(groom)

    plan = Scheduler().create_plan(make_owner(120, dog, cat), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [vet]
    assert [s.task for s in plan.skipped] == [groom]
    assert len(plan.conflicts) == 1
    assert "Vet call" in plan.conflicts[0]


def test_detect_conflicts_flags_same_and_different_pets() -> None:
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Luna", species="cat")
    meds = Task(description="Meds", duration_minutes=5, fixed_time=time(9, 0))
    nails = Task(description="Nails", duration_minutes=10, fixed_time=time(9, 0))
    call = Task(description="Vet call", duration_minutes=15, fixed_time=time(9, 5))
    later = Task(description="Walk", duration_minutes=10, fixed_time=time(9, 30))
    for task in (meds, nails, later):
        dog.add_task(task)
    cat.add_task(call)

    warnings = Scheduler.detect_conflicts(make_owner(120, dog, cat), TODAY)

    assert len(warnings) == 2
    assert "'Meds'" in warnings[0] and "'Nails'" in warnings[0]
    assert warnings[0].endswith("[same pet]")
    assert "'Nails'" in warnings[1] and "'Vet call'" in warnings[1]
    assert warnings[1].endswith("[different pets]")


def test_detect_conflicts_ignores_back_to_back_completed_and_flexible() -> None:
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Feed", 10, fixed_time=time(8, 0)))
    pet.add_task(Task("Walk", 20, fixed_time=time(8, 10)))
    pet.add_task(Task("Brush", 10, fixed_time=time(8, 0), completed=True))
    pet.add_task(Task("Play", 15))

    assert Scheduler.detect_conflicts(make_owner(60, pet), TODAY) == []


def test_filter_tasks_by_pet_and_status() -> None:
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Luna", species="cat")
    walk = Task(description="Walk", duration_minutes=20)
    feed = Task(description="Feed", duration_minutes=5, completed=True)
    litter = Task(description="Litter", duration_minutes=5)
    dog.add_task(walk)
    dog.add_task(feed)
    cat.add_task(litter)
    owner = make_owner(60, dog, cat)

    assert [t for _, t in owner.filter_tasks(pet_name="Mochi")] == [walk, feed]
    assert [t for _, t in owner.filter_tasks(completed=False)] == [walk, litter]
    assert [t for _, t in owner.filter_tasks("Mochi", completed=True)] == [feed]


@pytest.mark.parametrize("frequency, days", [("daily", 1), ("weekly", 7)])
def test_completing_recurring_task_queues_next_occurrence(
    frequency: str, days: int
) -> None:
    pet = Pet(name="Mochi", species="dog")
    task = Task(description="Brush", duration_minutes=5, frequency=frequency)
    pet.add_task(task)

    next_task = pet.complete_task(task, TODAY)

    assert task.completed is True
    assert next_task is not None and next_task.completed is False
    assert next_task.due_date == TODAY + timedelta(days=days)
    assert pet.list_tasks() == [task, next_task]


def test_scheduler_mark_task_complete_finds_pet_and_handles_month_end() -> None:
    cat = Pet(name="Luna", species="cat")
    water = Task(description="Refresh water", duration_minutes=5)
    cat.add_task(water)
    owner = make_owner(30, cat)

    next_water = Scheduler.mark_task_complete(owner, water, on=date(2026, 12, 31))

    assert water.completed is True
    assert next_water is not None and next_water.due_date == date(2027, 1, 1)
    assert next_water in cat.list_tasks()
    with pytest.raises(ValueError):
        Scheduler.mark_task_complete(owner, Task("Stray", 5))


def test_complete_task_defaults_to_today() -> None:
    pet = Pet(name="Mochi", species="dog")
    task = Task(description="Walk", duration_minutes=20)
    pet.add_task(task)

    next_task = pet.complete_task(task)

    assert next_task is not None
    assert next_task.due_date == date.today() + timedelta(days=1)


def test_completing_one_time_task_does_not_recur() -> None:
    pet = Pet(name="Mochi", species="dog")
    task = Task(description="Vet visit", duration_minutes=30, frequency="once")
    pet.add_task(task)

    assert pet.complete_task(task, TODAY) is None
    assert pet.list_tasks() == [task]


def test_sort_by_time_orders_shortest_first_without_mutating() -> None:
    walk = Task(description="Walk", duration_minutes=30)
    feed = Task(description="Feed", duration_minutes=5)
    play = Task(description="Play", duration_minutes=15)
    tasks = [walk, feed, play]

    assert Scheduler.sort_by_time(tasks) == [feed, play, walk]
    assert tasks == [walk, feed, play]


def test_sort_by_time_is_stable_and_supports_reverse() -> None:
    brush = Task(description="Brush", duration_minutes=10)
    litter = Task(description="Litter", duration_minutes=10)
    walk = Task(description="Walk", duration_minutes=30)
    tasks = [brush, walk, litter]

    assert Scheduler().sort_by_time(tasks) == [brush, litter, walk]
    assert Scheduler.sort_by_time(tasks, reverse=True) == [walk, brush, litter]
    assert Scheduler.sort_by_time([]) == []


def test_scheduler_filter_tasks_returns_matching_tasks() -> None:
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Luna", species="cat")
    walk = Task(description="Walk", duration_minutes=20)
    feed = Task(description="Feed", duration_minutes=5, completed=True)
    litter = Task(description="Litter", duration_minutes=5)
    dog.add_task(walk)
    dog.add_task(feed)
    cat.add_task(litter)
    owner = make_owner(60, dog, cat)

    assert Scheduler.filter_tasks(owner) == [walk, feed, litter]
    assert Scheduler.filter_tasks(owner, pet_name="Luna") == [litter]
    assert Scheduler.filter_tasks(owner, completed=True) == [feed]
    assert Scheduler.filter_tasks(owner, "Mochi", completed=False) == [walk]
    assert Scheduler.filter_tasks(owner, pet_name="Nobody") == []


def test_tasks_not_yet_due_are_left_out_of_the_plan() -> None:
    pet = Pet(name="Mochi", species="dog")
    bath = Task(description="Bath", duration_minutes=20, frequency="weekly")
    pet.add_task(bath)
    next_bath = pet.complete_task(bath, TODAY)
    owner = make_owner(60, pet)

    assert Scheduler().create_plan(owner, plan_date=TODAY).entries == []
    later = Scheduler().create_plan(owner, plan_date=TODAY + timedelta(days=7))
    assert [e.task for e in later.entries] == [next_bath]

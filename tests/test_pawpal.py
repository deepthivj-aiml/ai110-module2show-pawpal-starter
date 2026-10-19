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


# --- Happy paths -------------------------------------------------------------


def test_flexible_tasks_run_back_to_back_in_priority_order() -> None:
    pet = Pet(name="Mochi", species="dog")
    play = Task(description="Play", duration_minutes=15, priority="low")
    walk = Task(description="Walk", duration_minutes=20, priority="medium")
    meds = Task(description="Meds", duration_minutes=5, priority="high")
    for task in (play, walk, meds):
        pet.add_task(task)

    plan = Scheduler().create_plan(make_owner(60, pet), plan_date=TODAY)
    ordered = plan.sorted_entries()

    assert [e.task for e in ordered] == [meds, walk, play]
    assert [e.start_time for e in ordered] == [time(8, 0), time(8, 5), time(8, 25)]
    assert plan.skipped == [] and plan.conflicts == []
    assert plan.remaining_time() == 20


def test_flexible_tasks_fill_gaps_around_fixed_tasks_across_pets() -> None:
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Luna", species="cat")
    meds = Task(description="Meds", duration_minutes=20, fixed_time=time(8, 10))
    feed = Task(description="Feed", duration_minutes=10)
    brush = Task(description="Brush", duration_minutes=15)
    dog.add_task(meds)
    dog.add_task(feed)
    cat.add_task(brush)

    plan = Scheduler().create_plan(make_owner(60, dog, cat), plan_date=TODAY)
    starts = {e.task.description: e.start_time for e in plan.entries}

    assert starts == {"Meds": time(8, 10), "Feed": time(8, 0), "Brush": time(8, 30)}
    assert [e.pet for e in plan.sorted_entries()] == [dog, dog, cat]


def test_high_priority_task_wins_tight_budget_even_if_added_last() -> None:
    pet = Pet(name="Mochi", species="dog")
    play = Task(description="Play", duration_minutes=20, priority="low")
    meds = Task(description="Meds", duration_minutes=20, priority="high")
    pet.add_task(play)
    pet.add_task(meds)

    plan = Scheduler().create_plan(make_owner(20, pet), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [meds]
    assert [s.task for s in plan.skipped] == [play]


# --- Edge cases --------------------------------------------------------------


def test_pet_with_no_tasks_gives_empty_plan() -> None:
    owner = make_owner(60, Pet(name="Mochi", species="dog"))

    plan = Scheduler().create_plan(owner, plan_date=TODAY)

    assert plan.entries == [] and plan.skipped == [] and plan.conflicts == []
    assert owner.get_all_tasks() == []
    assert plan.summarize().startswith("No incomplete tasks")


def test_owner_with_no_pets_gives_empty_plan() -> None:
    plan = Scheduler().create_plan(make_owner(60), plan_date=TODAY)

    assert plan.entries == [] and plan.remaining_time() == 60


def test_two_pets_at_exact_same_time_higher_priority_keeps_slot() -> None:
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Luna", species="cat")
    walk = Task("Walk", 20, priority="low", fixed_time=time(9, 0))
    feed = Task("Feed", 10, priority="high", fixed_time=time(9, 0))
    dog.add_task(walk)
    cat.add_task(feed)

    plan = Scheduler().create_plan(make_owner(120, dog, cat), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [feed]
    assert [s.task for s in plan.skipped] == [walk]
    assert plan.skipped[0].reason == "conflicts with Feed"
    assert len(plan.conflicts) == 1
    assert plan.conflicts[0].endswith("[different pets]")


def test_same_pet_same_time_same_priority_first_added_wins() -> None:
    pet = Pet(name="Mochi", species="dog")
    pill = Task("Pill", 5, fixed_time=time(9, 0))
    brush = Task("Brush", 5, fixed_time=time(9, 0))
    pet.add_task(pill)
    pet.add_task(brush)

    plan = Scheduler().create_plan(make_owner(60, pet), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [pill]
    assert [s.task for s in plan.skipped] == [brush]
    assert plan.conflicts[0].endswith("[same pet]")


def test_zero_budget_skips_every_task() -> None:
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Walk", 20))
    pet.add_task(Task("Meds", 5, fixed_time=time(9, 0)))

    plan = Scheduler().create_plan(make_owner(0, pet), plan_date=TODAY)

    assert plan.entries == []
    assert len(plan.skipped) == 2
    assert all("only 0 min left" in s.reason for s in plan.skipped)


def test_task_exactly_filling_budget_is_scheduled() -> None:
    pet = Pet(name="Mochi", species="dog")
    walk = Task("Walk", 30)
    pet.add_task(walk)

    plan = Scheduler().create_plan(make_owner(30, pet), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [walk]
    assert plan.remaining_time() == 0


def test_task_ending_one_minute_before_midnight_is_scheduled() -> None:
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Late meds", 9, fixed_time=time(23, 50)))

    plan = Scheduler().create_plan(make_owner(30, pet), plan_date=TODAY)

    assert plan.entries[0].end_time == time(23, 59)


@pytest.mark.parametrize(
    "completed_on, expected",
    [
        (date(2026, 12, 31), date(2027, 1, 1)),
        (date(2028, 2, 28), date(2028, 2, 29)),
        (date(2027, 2, 28), date(2027, 3, 1)),
    ],
)
def test_daily_recurrence_rolls_over_year_end_and_leap_day(
    completed_on: date, expected: date
) -> None:
    task = Task("Feed", 5, frequency="daily")

    assert task.next_occurrence(completed_on).due_date == expected


def test_overdue_task_stays_in_plan_until_done() -> None:
    pet = Pet(name="Mochi", species="dog")
    bath = Task("Bath", 20, due_date=TODAY - timedelta(days=3))
    pet.add_task(bath)

    plan = Scheduler().create_plan(make_owner(60, pet), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [bath]


def test_completing_overdue_task_schedules_from_completion_date() -> None:
    pet = Pet(name="Mochi", species="dog")
    feed = Task("Feed", 5, frequency="daily", due_date=TODAY - timedelta(days=3))
    pet.add_task(feed)

    next_feed = pet.complete_task(feed, TODAY)

    assert next_feed.due_date == TODAY + timedelta(days=1)


def test_sorted_entries_are_chronological_even_when_stored_out_of_order() -> None:
    pet = Pet(name="Mochi", species="dog")
    dinner = Task("Dinner", 10, fixed_time=time(18, 0))
    walk = Task("Walk", 20)
    pet.add_task(dinner)
    pet.add_task(walk)

    plan = Scheduler().create_plan(make_owner(60, pet), plan_date=TODAY)

    assert [e.task for e in plan.entries] == [dinner, walk]  # insertion order
    starts = [e.start_time for e in plan.sorted_entries()]
    assert starts == sorted(starts) == [time(8, 0), time(18, 0)]

# appointments/services.py

from datetime import date, datetime, timedelta
from django.db import transaction
from django.utils import timezone

from doctors.models import Doctor, WeeklySchedule, DayOff
from .models import Appointment


# ── Slot generation ───────────────────────────────────────────────────────────

def _generate_slots_for_day(schedule: WeeklySchedule, target_date: date) -> list[dict]:
    """
    Pure function: given a schedule rule and a date, return a list of
    {start_time, end_time} dicts. No DB access.
    Skips slots overlapping with [break_start, break_end].
    """
    slots = []
    delta = timedelta(minutes=schedule.slot_duration)
    current = datetime.combine(target_date, schedule.start_time)
    end     = datetime.combine(target_date, schedule.end_time)

    b_start = datetime.combine(target_date, schedule.break_start) if schedule.break_start else None
    b_end   = datetime.combine(target_date, schedule.break_end)   if schedule.break_end   else None

    while current + delta <= end:
        s_start = current
        s_end   = current + delta

        # Check if slot overlaps with break
        is_break = False
        if b_start and b_end:
            # Overlap if slot_start < break_end AND slot_end > break_start
            if s_start.time() < b_end.time() and s_end.time() > b_start.time():
                is_break = True

        if not is_break:
            slots.append({
                'start_time': s_start.time(),
                'end_time':   s_end.time(),
            })
        current += delta
    return slots


def get_available_slots(doctor: Doctor, target_date: date) -> list[dict]:
    """
    Return all free time slots for a doctor on a given date.

    Steps:
      1. Check if the date is a day off → return [] immediately
      2. Find the WeeklySchedule for that weekday → return [] if none
      3. Generate all theoretical slots from the schedule
      4. Fetch active appointments on that date (DB hit: 1 query)
      5. Remove any slot that overlaps a booked appointment
    """

    # 1. Day off check
    if DayOff.objects.filter(doctor=doctor, date=target_date).exists():
        return []

    # 2. Schedule lookup (weekday: Mon=0 … Sun=6)
    try:
        schedule = WeeklySchedule.objects.get(
            doctor=doctor,
            day_of_week=target_date.weekday(),
            is_active=True,
        )
    except WeeklySchedule.DoesNotExist:
        return []

    # 3. Generate theoretical slots
    all_slots = _generate_slots_for_day(schedule, target_date)

    # 4. Active appointments on this date (single query)
    booked = Appointment.objects.filter(
        doctor=doctor,
        date=target_date,
        status__in=['pending', 'confirmed'],
    ).values('start_time', 'end_time')

    # 5. Filter out overlapping slots
    booked_ranges = [(b['start_time'], b['end_time']) for b in booked]

    def overlaps(slot) -> bool:
        for b_start, b_end in booked_ranges:
            # Two intervals overlap if one starts before the other ends
            if slot['start_time'] < b_end and slot['end_time'] > b_start:
                return True
        return False

    return [s for s in all_slots if not overlaps(s)]


def get_available_slots_range(doctor: Doctor, from_date: date, to_date: date) -> dict[str, list]:
    """
    Return available slots for a date range.
    Returns: {'2025-06-16': [{start_time, end_time}, ...], ...}
    Only includes dates that have at least one free slot.
    """
    # Batch-fetch all days off and schedules to avoid N+1
    days_off = set(
        DayOff.objects.filter(
            doctor=doctor,
            date__range=(from_date, to_date)
        ).values_list('date', flat=True)
    )
    schedules = {
        s.day_of_week: s
        for s in WeeklySchedule.objects.filter(doctor=doctor, is_active=True)
    }
    booked_by_date = {}
    for appt in Appointment.objects.filter(
        doctor=doctor,
        date__range=(from_date, to_date),
        status__in=['pending', 'confirmed'],
    ).values('date', 'start_time', 'end_time'):
        booked_by_date.setdefault(appt['date'], []).append(
            (appt['start_time'], appt['end_time'])
        )

    result = {}
    current = from_date
    while current <= to_date:
        if current not in days_off:
            schedule = schedules.get(current.weekday())
            if schedule:
                all_slots = _generate_slots_for_day(schedule, current)
                booked_ranges = booked_by_date.get(current, [])

                free = [
                    s for s in all_slots
                    if not any(
                        s['start_time'] < b_end and s['end_time'] > b_start
                        for b_start, b_end in booked_ranges
                    )
                ]
                if free:
                    result[str(current)] = free
        current += timedelta(days=1)

    return result


# ── Booking ───────────────────────────────────────────────────────────────────

def book_appointment(*, patient, doctor: Doctor, date: date,
                     start_time, end_time, motif: str) -> Appointment:
    """
    Atomically validate and create an appointment.
    Raises ValueError with a user-friendly message on any conflict.
    """

    with transaction.atomic():
        # Lock all appointments for this doctor+date to prevent race conditions
        existing = Appointment.objects.select_for_update().filter(
            doctor=doctor,
            date=date,
            status__in=['pending', 'confirmed'],
        )

        # Check overlap against locked rows
        for appt in existing:
            if start_time < appt.end_time and end_time > appt.start_time:
                raise ValueError(
                    f"Ce créneau ({start_time}–{end_time}) est déjà pris."
                )

        # Verify the slot actually exists in the doctor's schedule
        try:
            schedule = WeeklySchedule.objects.get(
                doctor=doctor,
                day_of_week=date.weekday(),
                is_active=True,
            )
        except WeeklySchedule.DoesNotExist:
            raise ValueError("Le médecin ne travaille pas ce jour-là.")

        if DayOff.objects.filter(doctor=doctor, date=date).exists():
            raise ValueError("Le médecin est absent ce jour-là.")

        # Confirm start/end aligns with schedule boundaries and duration
        _validate_slot_alignment(schedule, start_time, end_time)

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date,
            start_time=start_time,
            end_time=end_time,
            motif=motif,
        )


    return appointment


def _validate_slot_alignment(schedule: WeeklySchedule, start_time, end_time):
    """
    Ensure the requested start/end aligns with a real slot in the schedule.
    Prevents clients from submitting arbitrary times like 09:07–09:22.
    """
    from datetime import date as date_class
    dummy_date = date_class.today()
    valid_slots = _generate_slots_for_day(schedule, dummy_date)
    requested = {'start_time': start_time, 'end_time': end_time}

    if requested not in valid_slots:
        raise ValueError(
            f"Le créneau {start_time}–{end_time} ne correspond pas "
            f"au planning du médecin (durée: {schedule.slot_duration} min)."
        )
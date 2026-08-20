from datetime import datetime


def to_minutes(time):
    return datetime.strptime(time, "%H:%M").hour * 60 + \
           datetime.strptime(time, "%H:%M").minute


def validate_schedule(schedule, venues, activities, budget):
    errors = []
    bookings = []
    total_cost = 0

    venue_map = {
        row["Venue"]: row
        for _, row in venues.iterrows()
    }

    activity_map = {
        row["Activity"]: row
        for _, row in activities.iterrows()
    }

    max_budget = budget.iloc[0]["Amount (INR)"]

    for event in schedule:

        activity_name = event.get("activity")
        venue_name = event.get("venue")
        start = event.get("start")
        end = event.get("end")

        if not all([activity_name, venue_name, start, end]):
            errors.append("Incomplete schedule entry.")
            continue

        if activity_name not in activity_map:
            errors.append(f"Unknown activity: {activity_name}")
            continue

        if venue_name not in venue_map:
            errors.append(f"Unknown venue: {venue_name}")
            continue

        activity = activity_map[activity_name]
        venue = venue_map[venue_name]

        start_min = to_minutes(start)
        end_min = to_minutes(end)

        # Capacity
        if venue["Capacity"] < activity["Participants"]:
            errors.append(
                f"{venue_name} cannot accommodate "
                f"{activity_name}."
            )

        # Equipment
        requirement = str(activity["Requirement"])

        if requirement != "None" and requirement != "nan":
            equipment = str(venue["Equipment"])

            if requirement.lower() not in equipment.lower():
                errors.append(
                    f"{venue_name} lacks {requirement} "
                    f"for {activity_name}."
                )

        # Activity duration
        required_duration = activity["Duration (hours)"]
        scheduled_duration = (end_min - start_min) / 60

        if scheduled_duration < required_duration:
            errors.append(
                f"{activity_name} requires "
                f"{required_duration} hours."
            )

        # Venue availability
        venue_start = to_minutes(str(venue["Available From"]))
        venue_end = to_minutes(str(venue["Available To"]))

        if start_min < venue_start or end_min > venue_end:
            errors.append(
                f"{venue_name} is not available "
                f"from {start} to {end}."
            )

        # Fest ends at 6 PM
        if end_min > 18 * 60:
            errors.append(
                f"{activity_name} ends after 6:00 PM."
            )

        # Cost
        total_cost += activity["Cost (INR)"]

        # Double booking
        for booking in bookings:
            if booking["venue"] == venue_name:
                if (
                    start_min < booking["end"] and
                    end_min > booking["start"]
                ):
                    errors.append(
                        f"{venue_name} is double-booked."
                    )

        bookings.append({
            "venue": venue_name,
            "start": start_min,
            "end": end_min
        })

    # Budget
    if total_cost > max_budget:
        errors.append(
            f"Total cost ₹{total_cost} exceeds "
            f"the ₹{max_budget} budget."
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "total_cost": total_cost
    }
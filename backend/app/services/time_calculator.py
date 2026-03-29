"""Berechnung von Arbeitszeiten, Pausen und Zuschlaegen."""

from datetime import datetime, date, time, timedelta
from typing import Optional

# Pausenregelung nach Arbeitszeitgesetz (ArbZG § 4)
# > 6h: 30 Min Pause, > 9h: 45 Min Pause
BREAK_RULES = [
    (6.0, 30),   # Ab 6 Stunden: mindestens 30 Minuten
    (9.0, 45),   # Ab 9 Stunden: mindestens 45 Minuten
]

# Zuschlagssaetze (typisch TVoeD / Haustarif)
SURCHARGE_RATES = {
    "NIGHT": 20.0,       # 20% Nachtzuschlag (20:00-06:00)
    "SUNDAY": 25.0,      # 25% Sonntagszuschlag
    "HOLIDAY": 35.0,     # 35% Feiertagszuschlag
    "SATURDAY": 0.0,     # Samstag oft ohne Zuschlag, konfigurierbar
    "OVERTIME": 30.0,    # 30% Ueberstundenzuschlag
}

# Nachtarbeit-Zeitfenster
NIGHT_START = time(20, 0)
NIGHT_END = time(6, 0)


def calculate_minimum_break(gross_hours: float) -> int:
    """Berechnet die Mindestpause nach ArbZG."""
    required_break = 0
    for threshold, minutes in BREAK_RULES:
        if gross_hours > threshold:
            required_break = minutes
    return required_break


def calculate_net_hours(
    clock_in: datetime, clock_out: datetime, break_minutes: int
) -> float:
    """Berechnet die Netto-Arbeitszeit in Stunden."""
    total_seconds = (clock_out - clock_in).total_seconds()
    net_seconds = total_seconds - (break_minutes * 60)
    return round(max(0, net_seconds / 3600), 2)


def enforce_break_rules(
    clock_in: datetime, clock_out: datetime, break_minutes: int
) -> int:
    """Stellt sicher, dass die Mindestpause eingehalten wird.
    Gibt die tatsaechlich anzurechnende Pausenzeit zurueck.
    """
    gross_hours = (clock_out - clock_in).total_seconds() / 3600
    min_break = calculate_minimum_break(gross_hours)
    return max(break_minutes, min_break)


def calculate_night_hours(clock_in: datetime, clock_out: datetime) -> float:
    """Berechnet die Stunden im Nachtzeitraum (20:00-06:00)."""
    if clock_out <= clock_in:
        return 0.0

    night_hours = 0.0
    current = clock_in

    while current < clock_out:
        current_time = current.time()
        # Pruefen ob aktuelle Zeit im Nachtzeitraum liegt
        is_night = current_time >= NIGHT_START or current_time < NIGHT_END

        if is_night:
            # Naechste Grenze bestimmen
            if current_time >= NIGHT_START:
                # Nacht bis Mitternacht, dann bis 06:00
                next_boundary = datetime.combine(
                    current.date() + timedelta(days=1), NIGHT_END
                )
            else:
                # Vor 06:00
                next_boundary = datetime.combine(current.date(), NIGHT_END)

            end = min(clock_out, next_boundary)
            night_hours += (end - current).total_seconds() / 3600
            current = end
        else:
            # Naechster Nachtzeitraum beginnt
            next_night = datetime.combine(current.date(), NIGHT_START)
            if next_night <= current:
                next_night += timedelta(days=1)
            current = min(clock_out, next_night)

    return round(night_hours, 2)


def is_sunday(entry_date: date) -> bool:
    """Prueft ob der Tag ein Sonntag ist."""
    return entry_date.weekday() == 6


def is_saturday(entry_date: date) -> bool:
    """Prueft ob der Tag ein Samstag ist."""
    return entry_date.weekday() == 5


# Feiertage NRW (beispielhaft, sollte konfigurierbar sein)
def get_holidays(year: int) -> set[date]:
    """Gibt die gesetzlichen Feiertage fuer ein Jahr zurueck (NRW)."""
    holidays = {
        date(year, 1, 1),    # Neujahr
        date(year, 5, 1),    # Tag der Arbeit
        date(year, 10, 3),   # Tag der Deutschen Einheit
        date(year, 11, 1),   # Allerheiligen (NRW)
        date(year, 12, 25),  # 1. Weihnachtstag
        date(year, 12, 26),  # 2. Weihnachtstag
    }

    # Ostersonntag berechnen (Gausssche Osterformel)
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)

    # Bewegliche Feiertage relativ zu Ostern
    holidays.add(easter - timedelta(days=2))   # Karfreitag
    holidays.add(easter)                        # Ostersonntag
    holidays.add(easter + timedelta(days=1))    # Ostermontag
    holidays.add(easter + timedelta(days=39))   # Christi Himmelfahrt
    holidays.add(easter + timedelta(days=49))   # Pfingstsonntag
    holidays.add(easter + timedelta(days=50))   # Pfingstmontag
    holidays.add(easter + timedelta(days=60))   # Fronleichnam (NRW)

    return holidays


def is_holiday(entry_date: date) -> bool:
    """Prueft ob der Tag ein Feiertag ist."""
    return entry_date in get_holidays(entry_date.year)


def calculate_surcharges(
    clock_in: datetime,
    clock_out: datetime,
    entry_date: date,
    net_hours: float,
) -> list[dict]:
    """Berechnet alle anfallenden Zuschlaege fuer einen Zeiteintrag."""
    surcharges = []

    if clock_out is None or net_hours <= 0:
        return surcharges

    # Nachtzuschlag
    night_hours = calculate_night_hours(clock_in, clock_out)
    if night_hours > 0:
        surcharges.append({
            "type": "NIGHT",
            "hours": night_hours,
            "rate_percent": SURCHARGE_RATES["NIGHT"],
        })

    # Sonntagszuschlag
    if is_sunday(entry_date):
        surcharges.append({
            "type": "SUNDAY",
            "hours": net_hours,
            "rate_percent": SURCHARGE_RATES["SUNDAY"],
        })

    # Feiertagszuschlag
    if is_holiday(entry_date):
        surcharges.append({
            "type": "HOLIDAY",
            "hours": net_hours,
            "rate_percent": SURCHARGE_RATES["HOLIDAY"],
        })

    # Samstagszuschlag (falls konfiguriert > 0)
    if is_saturday(entry_date) and SURCHARGE_RATES["SATURDAY"] > 0:
        surcharges.append({
            "type": "SATURDAY",
            "hours": net_hours,
            "rate_percent": SURCHARGE_RATES["SATURDAY"],
        })

    return surcharges


def calculate_monthly_target_hours(
    weekly_hours: float, year: int, month: int
) -> float:
    """Berechnet die Soll-Stunden fuer einen Monat."""
    from calendar import monthrange

    _, days_in_month = monthrange(year, month)
    holidays = get_holidays(year)
    workdays = 0

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        # Montag=0 bis Freitag=4 und kein Feiertag
        if d.weekday() < 5 and d not in holidays:
            workdays += 1

    daily_hours = weekly_hours / 5
    return round(workdays * daily_hours, 2)

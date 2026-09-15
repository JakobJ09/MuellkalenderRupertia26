#!/usr/bin/env python3
"""
Erzeugt einen ICS-Kalender fuer den rotierenden Muelldienst.
Einfach die Namen unten anpassen und das Skript neu ausfuehren.
"""

from datetime import date, datetime, timedelta

# ---------------------------------------------------------------
# HIER ANPASSEN
# ---------------------------------------------------------------
BEWOHNER = [
    "Jakobsen",
    "Laar",
    "Kopp",
    "Götting",
    "Ebenburger",
    "Bala",
    "Schmid",
    "Bartl",
    "Bayer",
]

ERSTE_ABHOLUNG = date(2026, 9, 16)   # Mittwoch
INTERVALL_TAGE = 14                  # alle 14 Tage
RAUSSTELLEN_UHRZEIT = (19, 0)        # am Abend davor
DAUER_MINUTEN = 15
TONNEN = "Hausmuell + Papier"
OUTFILE = "muellplan.ics"

# Serien enden hier (z.B. weil sich die Abholtermine ueber die
# Feiertage verschieben und der Plan danach neu geprueft werden muss).
# None = laeuft unbegrenzt weiter.
ENDDATUM = date(2026, 12, 22)

# Manuelle Ausnahmen fuer Termine, die vom Stadt-Abfuhrkalender abweichen
# (z.B. wegen Feiertagen). Key = Position in BEWOHNER (1 = erste Person),
# Value = tatsaechliches Abholdatum laut Stadt.
AUSNAHMEN = {
    8: date(2026, 12, 22),   # statt errechnetem Mi 23.12. -> tatsaechlich Di 22.12.
}
# ---------------------------------------------------------------

N = len(BEWOHNER)
ZYKLUS_WOCHEN = N * INTERVALL_TAGE // 7   # 9 * 14 / 7 = 18 Wochen


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def dt(d: date, hh: int, mm: int) -> str:
    return datetime(d.year, d.month, d.day, hh, mm).strftime("%Y%m%dT%H%M%S")


VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Muellplan Haus//DE",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Muelldienst Haus",
    "X-WR-TIMEZONE:Europe/Berlin",
    "REFRESH-INTERVAL;VALUE=DURATION:P1D",
] + VTIMEZONE.split("\n")

stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
plan = []

for i, name in enumerate(BEWOHNER):
    position = i + 1
    ausnahme = position in AUSNAHMEN
    abholung = AUSNAHMEN[position] if ausnahme else ERSTE_ABHOLUNG + timedelta(days=INTERVALL_TAGE * i)
    vorabend = abholung - timedelta(days=1)
    plan.append((abholung, name))

    start = dt(vorabend, *RAUSSTELLEN_UHRZEIT)
    ende_dt = datetime(vorabend.year, vorabend.month, vorabend.day,
                       *RAUSSTELLEN_UHRZEIT) + timedelta(minutes=DAUER_MINUTEN)
    ende = ende_dt.strftime("%Y%m%dT%H%M%S")

    hinweis_ausnahme = " (Termin laut Stadt-Abfuhrkalender verschoben)" if ausnahme else ""
    beschreibung = (
        f"{TONNEN} heute Abend an die Strasse stellen. "
        f"Abholung morgen frueh ({abholung.strftime('%d.%m.')}){hinweis_ausnahme}. "
        f"Tonnen danach wieder reinstellen. "
        f"Naechster Dienst: {BEWOHNER[(i + 1) % N]}."
    )

    if ausnahme:
        # Einzeltermin, keine Wiederholung - weicht vom regulaeren
        # 14-Tage-Rhythmus ab (Feiertagsverschiebung), soll sich also
        # nicht automatisch fortsetzen.
        rrule = None
    else:
        rrule = f"RRULE:FREQ=WEEKLY;INTERVAL={ZYKLUS_WOCHEN}"
    if rrule is not None and ENDDATUM is not None:
        # UNTIL muss in UTC angegeben werden (Ende des Tages, damit die
        # lokale Zeitzone/Sommerzeit keine Rolle spielt).
        until = ENDDATUM.strftime("%Y%m%d") + "T235959Z"
        rrule += f";UNTIL={until}"

    lines += [
        "BEGIN:VEVENT",
        f"UID:muelldienst-{i+1}@haus",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID=Europe/Berlin:{start}",
        f"DTEND;TZID=Europe/Berlin:{ende}",
    ]
    if rrule is not None:
        lines.append(rrule)
    lines += [
        f"SUMMARY:Tonnen raus: {esc(name)}",
        f"DESCRIPTION:{esc(beschreibung)}",
        "LOCATION:Haus",
        "TRANSP:TRANSPARENT",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "TRIGGER:-PT60M",
        f"DESCRIPTION:{esc(name)}: Tonnen rausstellen ({TONNEN})",
        "END:VALARM",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "TRIGGER:PT0M",
        f"DESCRIPTION:{esc(name)}: Tonnen jetzt rausstellen",
        "END:VALARM",
        "END:VEVENT",
    ]

lines.append("END:VCALENDAR")

with open(OUTFILE, "w", encoding="utf-8") as f:
    f.write("\r\n".join(lines) + "\r\n")

print(f"{OUTFILE} geschrieben - {N} Serien, Zyklus alle {ZYKLUS_WOCHEN} Wochen\n")
print("Termine (erste Runde):")
uebrig = []
for abholung, name in sorted(plan):
    vorabend = abholung - timedelta(days=1)
    aktiv = ENDDATUM is None or vorabend <= ENDDATUM
    status = "" if aktiv else "  <- faellt weg (nach Enddatum)"
    print(f"  {vorabend.strftime('%a %d.%m.%Y')} abends  ->  {name}"
          f"   (Abholung {abholung.strftime('%d.%m.')}){status}")
    if not aktiv:
        uebrig.append(name)

if ENDDATUM is not None:
    print(f"\nKalender endet nach dem {ENDDATUM.strftime('%d.%m.%Y')}.")
    if uebrig:
        print(f"Noch nicht drangekommen (fuer die naechste Runde vormerken): "
              f"{', '.join(uebrig)}")

"""Verify the demo seed data for Plan 2026.

Run: python scripts/verify_demo_seed.py
Exit code 0 = all checks passed, 1 = failures found.
"""

from __future__ import annotations

import sys
from datetime import date, time

# Add backend to path
sys.path.insert(0, ".")

from app import create_app
from sqlalchemy import func
from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot, AvailabilityRule, HolidayOrBlockedDay, Location
from app.models.tribute_type import TributeType
from app.models.user import AdminUser


def check(description: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {description}"
    if detail and not condition:
        msg += f" -- {detail}"
    print(msg)
    return condition


def main() -> int:
    app = create_app()
    failures = 0

    with app.app_context():
        print("=== Verificación del seed demo Plan 2026 ===\n")

        # --- Tribute types ---
        print("Tributos:")
        tributes = TributeType.query.order_by(TributeType.sort_order).all()
        if not check("Cantidad = 2", len(tributes) == 2, f"obtenido: {len(tributes)}"):
            failures += 1

        names = [t.name for t in tributes]
        if not check("Existe CIU", "Contribución Inmobiliaria Urbana" in names, f"nombres: {names}"):
            failures += 1
        if not check("Existe CIS", "Contribución Inmobiliaria Suburbana" in names, f"nombres: {names}"):
            failures += 1
        if not check("No existe Rural", "Contribución Inmobiliaria Rural" not in names):
            failures += 1
        if not check("No existe Patente", "Patente de rodados" not in names):
            failures += 1
        if not check("No existe Multas", "Multas de tránsito" not in names):
            failures += 1

        for t in tributes:
            if not check(f"  '{t.name}' activo", t.is_active):
                failures += 1
            if not check(f"  '{t.name}' duración=30", t.default_duration_minutes == 30, f"obtenido: {t.default_duration_minutes}"):
                failures += 1
            if not check(f"  '{t.name}' requires_padron", t.requires_padron):
                failures += 1

        # --- Locations ---
        print("\nSedes:")
        locations = Location.query.all()
        if not check("Cantidad = 1", len(locations) == 1, f"obtenido: {len(locations)}"):
            failures += 1

        loc = locations[0] if locations else None
        if loc:
            if not check("Nombre = Palacio Municipal", loc.name == "Palacio Municipal", f"obtenido: {loc.name}"):
                failures += 1
            if not check("Dirección = Palacio Municipal, Minas, Lavalleja", loc.address == "Palacio Municipal, Minas, Lavalleja", f"obtenido: {loc.address}"):
                failures += 1
            if not check("Activa", loc.is_active):
                failures += 1

        # --- Rules ---
        print("\nReglas:")
        rules = AvailabilityRule.query.all()
        if not check("Cantidad = 1", len(rules) == 1, f"obtenido: {len(rules)}"):
            failures += 1

        rule = rules[0] if rules else None
        if rule:
            if not check("Nombre correcto", "Plan 2026" in rule.name, f"obtenido: {rule.name}"):
                failures += 1
            if not check("start_date = 2026-07-24", rule.start_date == date(2026, 7, 24), f"obtenido: {rule.start_date}"):
                failures += 1
            if not check("end_date = 2026-07-31", rule.end_date == date(2026, 7, 31), f"obtenido: {rule.end_date}"):
                failures += 1
            if not check("weekdays = [0, 2, 4]", rule.weekdays == [0, 2, 4], f"obtenido: {rule.weekdays}"):
                failures += 1
            if not check("start_time = 09:00", rule.start_time == time(9, 0), f"obtenido: {rule.start_time}"):
                failures += 1
            if not check("end_time = 12:00", rule.end_time == time(12, 0), f"obtenido: {rule.end_time}"):
                failures += 1
            if not check("duration = 30 min", rule.slot_duration_minutes == 30, f"obtenido: {rule.slot_duration_minutes}"):
                failures += 1
            if not check("capacity = 2", rule.capacity_per_slot == 2, f"obtenido: {rule.capacity_per_slot}"):
                failures += 1
            if not check("applies_to_all = True", rule.applies_to_all):
                failures += 1
            if not check("Activa", rule.is_active):
                failures += 1

        # --- Slots ---
        print("\nSlots:")
        slots = AppointmentSlot.query.all()
        if not check("Cantidad total = 48", len(slots) == 48, f"obtenido: {len(slots)}"):
            failures += 1

        # Check dates
        slot_dates = sorted(set(s.date for s in slots))
        expected_dates = [date(2026, 7, 24), date(2026, 7, 27), date(2026, 7, 29), date(2026, 7, 31)]
        if not check("4 fechas únicas", len(slot_dates) == 4, f"obtenido: {len(slot_dates)} fechas"):
            failures += 1
        if not check("Fechas correctas", slot_dates == expected_dates, f"obtenido: {slot_dates}"):
            failures += 1

        # Check slots per date
        for d in expected_dates:
            count = AppointmentSlot.query.filter_by(date=d).count()
            if not check(f"  {d}: 12 slots", count == 12, f"obtenido: {count}"):
                failures += 1

        # Check slots per tribute
        for t in tributes:
            count = AppointmentSlot.query.filter_by(tribute_type_id=t.id).count()
            if not check(f"  {t.name}: 24 slots", count == 24, f"obtenido: {count}"):
                failures += 1

        # Check times (per tribute, 6 slots each)
        expected_times = [
            time(9, 0), time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30)
        ]
        first_tribute_id = tributes[0].id if tributes else None
        for d in expected_dates:
            day_slots = AppointmentSlot.query.filter_by(
                date=d, tribute_type_id=first_tribute_id
            ).order_by(AppointmentSlot.start_time).all()
            times = [s.start_time for s in day_slots]
            if not check(f"  {d} horarios correctos", times == expected_times, f"obtenido: {times}"):
                failures += 1

        # Check no blocked slots
        blocked = AppointmentSlot.query.filter_by(is_blocked=True).count()
        if not check("Sin slots bloqueados", blocked == 0, f"obtenido: {blocked}"):
            failures += 1

        # Check all slots have location and tribute
        no_loc = AppointmentSlot.query.filter(AppointmentSlot.location_id.is_(None)).count()
        no_trib = AppointmentSlot.query.filter(AppointmentSlot.tribute_type_id.is_(None)).count()
        if not check("Todos los slots tienen sede", no_loc == 0, f"sin sede: {no_loc}"):
            failures += 1
        if not check("Todos los slots tienen tributo", no_trib == 0, f"sin tributo: {no_trib}"):
            failures += 1

        # --- Holidays ---
        print("\nFeriados:")
        holidays = HolidayOrBlockedDay.query.count()
        if not check("Cantidad = 0", holidays == 0, f"obtenido: {holidays}"):
            failures += 1

        # --- Appointments ---
        print("\nReservas demo:")
        appointments = Appointment.query.order_by(Appointment.reservation_code).all()
        if not check("Cantidad = 2", len(appointments) == 2, f"obtenido: {len(appointments)}"):
            failures += 1

        codes = [a.reservation_code for a in appointments]
        if not check("Existe DEMO01", "IDL-AF-2026-DEMO01" in codes, f"códigos: {codes}"):
            failures += 1
        if not check("Existe DEMO02", "IDL-AF-2026-DEMO02" in codes, f"códigos: {codes}"):
            failures += 1

        for a in appointments:
            if not check(f"  {a.reservation_code} status={a.status}", a.status in ("reserved", "confirmed"), f"obtenido: {a.status}"):
                failures += 1
            if not check(f"  {a.reservation_code} tiene slot", a.slot_id is not None):
                failures += 1
            if not check(f"  {a.reservation_code} tiene tributo", a.tribute_type_id is not None):
                failures += 1
            if not check(f"  {a.reservation_code} tiene sede", a.location_id is not None):
                failures += 1

        # Check reserved_count consistency
        total_reserved = db.session.query(func.sum(AppointmentSlot.reserved_count)).scalar() or 0
        if not check("Suma reserved_count = 2", total_reserved == 2, f"obtenido: {total_reserved}"):
            failures += 1

        over_capacity = AppointmentSlot.query.filter(
            AppointmentSlot.reserved_count > AppointmentSlot.capacity
        ).count()
        if not check("Sin overbooking", over_capacity == 0, f"overbooked: {over_capacity}"):
            failures += 1

        # Check specific slots
        slot_urbana = AppointmentSlot.query.filter_by(
            tribute_type_id=[t.id for t in tributes if "Urbana" in t.name][0],
            date=date(2026, 7, 24),
            start_time=time(9, 0),
        ).first()
        if slot_urbana:
            if not check("Slot Urbana 24/07 09:00 reserved_count=1", slot_urbana.reserved_count == 1, f"obtenido: {slot_urbana.reserved_count}"):
                failures += 1
            if not check("Slot Urbana 24/07 09:00 capacity=2", slot_urbana.capacity == 2, f"obtenido: {slot_urbana.capacity}"):
                failures += 1

        slot_suburbana = AppointmentSlot.query.filter_by(
            tribute_type_id=[t.id for t in tributes if "Suburbana" in t.name][0],
            date=date(2026, 7, 27),
            start_time=time(10, 0),
        ).first()
        if slot_suburbana:
            if not check("Slot Suburbana 27/07 10:00 reserved_count=1", slot_suburbana.reserved_count == 1, f"obtenido: {slot_suburbana.reserved_count}"):
                failures += 1
            if not check("Slot Suburbana 27/07 10:00 capacity=2", slot_suburbana.capacity == 2, f"obtenido: {slot_suburbana.capacity}"):
                failures += 1

        # --- Admin ---
        print("\nAdministrador:")
        admin = AdminUser.query.filter_by(username="admin").first()
        if admin:
            if not check("Admin existe", True):
                failures += 1
            if not check("Admin activo", admin.is_active):
                failures += 1
            if not check("Admin superuser", admin.is_superuser):
                failures += 1
        else:
            if not check("Admin existe", False, "no encontrado"):
                failures += 1

        # --- No residual data ---
        print("\nDatos residuales:")
        if not check("Sin datos de seed anterior (Patente)", "Patente de rodados" not in names):
            failures += 1
        if not check("Sin datos de seed anterior (Comercios)", "Comercios" not in names):
            failures += 1

        # --- Summary ---
        print(f"\n{'='*50}")
        if failures == 0:
            print("TODAS LAS VERIFICACIONES PASARON")
            return 0
        else:
            print(f"FALLARON {failures} VERIFICACIONES")
            return 1


if __name__ == "__main__":
    sys.exit(main())

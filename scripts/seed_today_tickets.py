from app import create_app
from app.extensions import db
from app.models.appointment import Appointment
from app.models.availability import AppointmentSlot, Location
from app.models.tribute_type import TributeType
from datetime import date, time

app = create_app()
with app.app_context():
    t = TributeType.query.filter_by(slug="contribucion").first()
    if not t:
        t = TributeType(name="Contribucion", slug="contribucion", is_active=True)
        db.session.add(t)
        db.session.commit()
    loc = Location.query.filter_by(name="Centro").first()
    if not loc:
        loc = Location(name="Centro", is_active=True)
        db.session.add(loc)
        db.session.commit()
    slots = []
    for h in range(9, 16):
        s = AppointmentSlot(tribute_type_id=t.id, location_id=loc.id, date=date.today(), start_time=time(h, 0), end_time=time(h, 30), capacity=5)
        db.session.add(s)
        slots.append(s)
    db.session.commit()
    for i, (code, name, hh) in enumerate(
        [("T-0100", "Ana Perez", 9), ("T-0101", "Bruno Diaz", 9), ("T-0110", "Carla Ruiz", 10), ("T-0111", "Diego Sosa", 10), ("T-0120", "Elena Gomez", 11)]
    ):
        a = Appointment(
            reservation_code=code,
            tribute_type_id=t.id,
            location_id=loc.id,
            slot_id=slots[hh - 9].id,
            citizen_name=name,
            citizen_document=f"4.000.00{i}-8",
            phone="099000000",
            status="reserved",
        )
        db.session.add(a)
    db.session.commit()
    print("seeded 5 tickets for today")

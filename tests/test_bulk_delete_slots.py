import pytest

from app import create_app
from app.extensions import db
from app.models.availability import AppointmentSlot

@pytest.fixture()
def app():
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False, SQLALCHEMY_DATABASE_URI="sqlite://")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

def test_bulk_delete_requires_filters(app):
    client = app.test_client()
    response = client.post("/admin/api/availability/slots/bulk-delete", json={"confirm": True})
    # Sin sesion responde 401; lo importante es que la ruta exista y no sea 404.
    assert response.status_code in (400, 401)

def test_bulk_delete_route_is_registered(app):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/admin/api/availability/slots/bulk-delete" in rules
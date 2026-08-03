from app import create_app
from app.extensions import mail
from app.services.email_service import send_email


def test_send_email_reports_smtp_acceptance(monkeypatch):
    app = create_app()
    sent_messages = []

    def fake_send(message):
        sent_messages.append(message)

    monkeypatch.setattr(mail, "send", fake_send)
    with app.app_context():
        assert send_email("Prueba", ["vecino@example.com"], "<p>Mensaje</p>", "Mensaje") is True

    assert len(sent_messages) == 1
    assert sent_messages[0].recipients == ["vecino@example.com"]


def test_send_email_reports_failure_without_raising(monkeypatch):
    app = create_app()

    def fail_send(_message):
        raise OSError("SMTP no disponible")

    monkeypatch.setattr(mail, "send", fail_send)
    with app.app_context():
        assert send_email("Prueba", ["vecino@example.com"], "<p>Mensaje</p>") is False


def test_send_email_skips_empty_recipients(monkeypatch):
    app = create_app()

    def unexpected_send(_message):
        raise AssertionError("No debe enviar un mensaje sin destinatarios")

    monkeypatch.setattr(mail, "send", unexpected_send)
    with app.app_context():
        assert send_email("Prueba", [], "<p>Mensaje</p>") is False


def test_mail_debug_is_disabled_by_default():
    app = create_app()

    assert app.config["MAIL_DEBUG"] is False
    assert app.config["MAIL_TIMEOUT"] == 20

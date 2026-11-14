import importlib

import pytest


@pytest.fixture
def syncer(monkeypatch):
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    import syncer as mod

    return importlib.reload(mod)


def test_no_credentials_are_hardcoded(syncer):
    assert not [n for n in dir(syncer) if n.startswith("HARDCODED")]
    assert syncer.SMTP_USER == "" and syncer.SMTP_PASS == ""
    assert syncer.smtp_configured() is False


def test_send_email_refuses_without_configuration(syncer, capsys):
    assert syncer.send_email("s", "<p>x</p>", "to@example.com") is False
    assert "SMTP_USER" in capsys.readouterr().out


def test_dispatch_stops_early_without_smtp_settings(syncer, capsys):
    assert syncer.dispatch_emails(dry_run=False) == 0
    assert "SMTP credentials missing" in capsys.readouterr().out


def test_settings_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASS", "app-pass-from-env")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    import syncer as mod

    mod = importlib.reload(mod)
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["server"] = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, msg):
            sent["to"] = msg["To"]

    monkeypatch.setattr(mod.smtplib, "SMTP", FakeSMTP)
    assert mod.send_email("Subject", "<p>hi</p>", "reader@example.com") is True
    assert sent == {"server": ("smtp.example.com", 2525), "tls": True,
                    "login": ("sender@example.com", "app-pass-from-env"), "to": "reader@example.com"}

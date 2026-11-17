"""No actual mail is sent. Ensure encryption before authentication and no secret logs."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
import mail_delivery as mail
import routes_auth as auth


def setup(monkeypatch,security='ssl'):
    for k,v in {'SMTP_HOST':'mail.example.com','SMTP_PORT':'465' if security=='ssl' else '587','SMTP_SECURITY':security,'SMTP_USER':'fixture-user','SMTP_PASSWORD':'fixture-private','SMTP_FROM':'KAOS <support@example.com>'}.items():monkeypatch.setenv(k,v)


def test_ssl_sender_uses_verified_tls_and_sends_message(monkeypatch):
    setup(monkeypatch);client=Mock();client.__enter__=Mock(return_value=client);client.__exit__=Mock(return_value=False);constructor=Mock(return_value=client);monkeypatch.setattr(mail.smtplib,'SMTP_SSL',constructor)
    assert asyncio.run(mail.send_smtp('member@example.com','Account action','<p>Fixture</p>')) is True
    assert constructor.call_args.kwargs['context'].check_hostname is True
    client.login.assert_called_once_with('fixture-user','fixture-private')
    assert client.send_message.call_args.args[0]['Subject']=='Account action'


def test_starttls_precedes_login(monkeypatch):
    setup(monkeypatch,'starttls');calls=[]
    class Client:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def ehlo(self):calls.append('ehlo')
        def starttls(self,**kwargs):calls.append('tls')
        def login(self,*args):calls.append('login')
        def send_message(self,*args):calls.append('send')
    monkeypatch.setattr(mail.smtplib,'SMTP',lambda *a,**k:Client())
    assert asyncio.run(mail.send_smtp('member@example.com','Test','<p>Fixture</p>'))
    assert calls==['ehlo','tls','ehlo','login','send']


def test_plaintext_smtp_is_not_ready(monkeypatch):
    setup(monkeypatch,'none');assert mail.smtp_ready() is False


def test_reset_uses_smtp_without_legacy_proxy_key(monkeypatch):
    from unittest.mock import AsyncMock
    setup(monkeypatch);monkeypatch.setenv('FRONTEND_URL','https://tradingwithkaos.com');monkeypatch.setattr(auth,'EMAIL_KEY','');send=AsyncMock(return_value=True);monkeypatch.setattr(auth,'send_smtp',send)
    assert asyncio.run(auth.send_password_reset_email('member@example.com','fixture-token')) is True
    assert 'reset-password?token=fixture-token' in send.await_args.args[2]

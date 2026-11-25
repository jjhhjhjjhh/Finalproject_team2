"""Offline email tests: isolated database and mocked SMTP, no real delivery."""
import asyncio
import os
import smtplib
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import my_server as server


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = patch.object(server, 'DB_PATH', Path(self.tmp.name) / 'emails.db')
        self.db.start()
        self.addCleanup(self.db.stop)
        env = patch.dict(os.environ, {
            'SMTP_USER': 'sender@example.com', 'SMTP_PASSWORD': 'fake',
            'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': '587',
        })
        env.start()
        self.addCleanup(env.stop)
        smtp = patch.object(server.smtplib, 'SMTP')
        self.smtp = smtp.start().return_value.__enter__.return_value
        self.addCleanup(smtp.stop)

    def rows(self):
        with server._connect() as conn:
            return conn.execute('SELECT * FROM scheduled_emails ORDER BY rowid').fetchall()

    def reserve(self):
        server.send_email('allowed@example.com', 'Test', 'Body', '2099-01-02 12:00')
        return self.rows()[-1]['id']

    def make_due(self):
        with server._connect() as conn:
            conn.execute("UPDATE scheduled_emails SET send_at_utc='2000-01-01T00:00:00+00:00'")

    def test_immediate_and_scheduled(self):
        server.send_email('allowed@example.com', 'Test', 'Body')
        self.smtp.send_message.assert_called_once()
        self.smtp.reset_mock()
        job = self.reserve()
        self.smtp.send_message.assert_not_called()
        self.assertEqual(self.rows()[0]['send_at_utc'], '2099-01-02T03:00:00+00:00')
        self.assertIn(job, server.list_scheduled_emails())
        self.assertEqual(server.send_due_emails(), 0)
        self.make_due()
        self.assertEqual(server.send_due_emails(), 1)
        self.assertEqual(server.send_due_emails(), 0)
        self.assertEqual(self.rows()[0]['status'], 'sent')
        self.smtp.send_message.assert_called_once()

    def test_cancel_and_validation(self):
        job = self.reserve()
        server.cancel_scheduled_email(job)
        self.make_due()
        self.assertEqual(server.send_due_emails(), 0)
        self.assertEqual(self.rows()[0]['status'], 'cancelled')
        for recipient, subject, when in [
            ('invalid-address', 'Test', '2099-01-01'),
            ('allowed@example.com', 'Bad\nHeader', '2099-01-01'),
            ('allowed@example.com', 'Test', '2000-01-01'),
            ('allowed@example.com', 'Test', 'bad-date'),
        ]:
            server.send_email(recipient, subject, 'Body', when)
        self.assertEqual(len(self.rows()), 1)
        self.smtp.send_message.assert_not_called()

    def test_delivery_without_allowed_recipients(self):
        with patch.dict(os.environ, {'EMAIL_ALLOWED_RECIPIENTS': ''}):
            server.send_email('new@example.com', 'Test', 'Body')
        self.smtp.send_message.assert_called_once()
        self.assertEqual(self.smtp.send_message.call_args.args[0]['To'], 'new@example.com')
        self.smtp.reset_mock()
        self.reserve()
        self.make_due()
        with patch.dict(os.environ, {'EMAIL_ALLOWED_RECIPIENTS': ''}):
            server.send_due_emails()
        self.assertEqual(self.rows()[0]['status'], 'sent')
        self.smtp.send_message.assert_called_once()

    def test_smtp_failure(self):
        self.reserve()
        self.make_due()
        self.smtp.send_message.side_effect = smtplib.SMTPException('mock failure')
        server.send_due_emails()
        self.assertEqual(self.rows()[0]['status'], 'failed')
        self.assertIn('mock failure', self.rows()[0]['last_error'])

    def test_competing_workers(self):
        for _ in range(5):
            self.reserve()
        self.make_due()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(lambda _: server.send_due_emails(), range(2))), 5)
        self.assertEqual(self.smtp.send_message.call_count, 5)

    def test_connection_closed(self):
        with server._connect() as conn:
            conn.execute('SELECT 1')
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')

    def test_tools_registered(self):
        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        for name in ('send_email', 'schedule_email', 'list_scheduled_emails', 'cancel_scheduled_email'):
            self.assertIn(name, tools)
        self.assertIn('send_at', tools['send_email'].inputSchema['properties'])

    def test_server_lifecycle(self):
        self.reserve()
        self.make_due()
        import threading
        delivered = threading.Event()
        self.smtp.send_message.side_effect = lambda *_: delivered.set()
        with patch.object(server.mcp, 'run', side_effect=lambda: self.assertTrue(delivered.wait(5))):
            server.run_server()
        self.assertEqual(self.rows()[0]['status'], 'sent')


if __name__ == '__main__':
    unittest.main()

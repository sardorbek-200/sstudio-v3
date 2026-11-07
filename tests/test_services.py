import unittest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from services.quizer.app.main import app as quizer_app
from services.shop.app.main import app as shop_app
from services.admin.app.main import app as admin_app
from models.quizer import Test, Question, TestResult
from models.shop import Wallet, SCoinTransaction, SubscriptionPlan, PaymentReceipt
from models.admin import AuditLog

SERVICES_DIR = Path(__file__).resolve().parent.parent / "services"


class TestEcosystemServices(unittest.TestCase):
    def test_quizer_routes_registered(self):
        paths = [r.path for r in quizer_app.routes]
        self.assertIn("/", paths)
        self.assertIn("/create", paths)
        self.assertIn("/api/ai-generate", paths)
        self.assertIn("/api/verify-pin", paths)
        self.assertIn("/health", paths)

    def test_shop_routes_registered(self):
        paths = [r.path for r in shop_app.routes]
        self.assertIn("/", paths)
        self.assertIn("/wheel", paths)
        self.assertIn("/plans", paths)
        self.assertIn("/topup", paths)
        self.assertIn("/api/transfer", paths)
        self.assertIn("/health", paths)

    def test_admin_routes_registered(self):
        paths = [r.path for r in admin_app.routes]
        self.assertIn("/", paths)
        self.assertIn("/api/receipts/{receipt_id}/action", paths)
        self.assertIn("/health", paths)

    def test_quizer_template_rendering(self):
        env = Environment(loader=FileSystemLoader(str(SERVICES_DIR / "quizer" / "templates")))
        tmpl = env.get_template("quizer_index.html")
        rendered = tmpl.render(domain="sstudio.uz", user=None, tests=[])
        self.assertIn("Quizer", rendered)
        self.assertIn("PIN", rendered)

    def test_shop_template_rendering(self):
        env = Environment(loader=FileSystemLoader(str(SERVICES_DIR / "shop" / "templates")))
        tmpl = env.get_template("wallet.html")
        rendered = tmpl.render(domain="sstudio.uz", user=None, wallet={"scoin_balance": 100}, transactions=[])
        self.assertIn("SCoin", rendered)
        self.assertIn("Komissiya", rendered)

    def test_shop_wheel_template(self):
        env = Environment(loader=FileSystemLoader(str(SERVICES_DIR / "shop" / "templates")))
        tmpl = env.get_template("wheel.html")
        rendered = tmpl.render(domain="sstudio.uz", user=None, can_spin=True, next_spin_hours=0)
        self.assertIn("Omad G'ildiragi", rendered)

    def test_admin_template_rendering(self):
        env = Environment(loader=FileSystemLoader(str(SERVICES_DIR / "admin" / "templates")))
        tmpl = env.get_template("dashboard.html")
        rendered = tmpl.render(domain="sstudio.uz", user=None, metrics={"total_users": 10, "total_scoin": 500, "total_tests": 5}, pending_receipts=[])
        self.assertIn("Boshqaruv", rendered)


if __name__ == "__main__":
    unittest.main()

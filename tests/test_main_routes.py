import unittest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from services.main.app.main import app
from services.quizer.app.main import app as quizer_app

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "services" / "main" / "templates"


class TestMainPortalComponents(unittest.TestCase):
    def setUp(self):
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    def test_routes_registered(self):
        """Barcha asosiy portal marshrutlari ro'yxatdan o'tganini tekshirish"""
        registered_paths = [route.path for route in app.routes]
        self.assertIn("/", registered_paths)
        self.assertIn("/apps", registered_paths)
        self.assertIn("/users", registered_paths)
        self.assertIn("/privacy", registered_paths)
        self.assertIn("/terms", registered_paths)
        self.assertIn("/wallet", registered_paths)
        self.assertIn("/settings", registered_paths)
        self.assertIn("/logout", registered_paths)

    def test_quizer_service_routes(self):
        """Quizer servisi marshrutlari to'g'ri ro'yxatdan o'tganini tekshirish"""
        quizer_paths = [route.path for route in quizer_app.routes]
        self.assertIn("/", quizer_paths)
        self.assertIn("/health", quizer_paths)
        self.assertIn("/my-tests", quizer_paths)
        self.assertIn("/test/{test_id}/monitoring", quizer_paths)
        self.assertIn("/test/{test_id}/edit", quizer_paths)
        self.assertIn("/ws/test/{test_id}/monitoring", quizer_paths)

    def test_index_template_rendering(self):
        """Bosh sahifa shabloni xatosiz render bo'lishi kerak"""
        template = self.env.get_template("index.html")
        rendered = template.render(domain="sstudio.uz", user=None)
        self.assertIn("SStudio", rendered)

    def test_privacy_template_rendering(self):
        """Maxfiylik siyosati shabloni SCoin qoidasini o'z ichiga olishi kerak"""
        template = self.env.get_template("privacy.html")
        rendered = template.render(domain="sstudio.uz", user=None)
        self.assertIn("SCoin", rendered)

    def test_wallet_and_settings_templates(self):
        """Wallet va Settings sahifalari muvaffaqiyatli render bo'lishi kerak"""
        wallet_tpl = self.env.get_template("wallet.html")
        wallet_out = wallet_tpl.render(
            domain="sstudio.uz",
            user={"id": 1, "username": "testuser", "name": "Test", "surname": "User", "status": "freemium"},
            scoin=50.0,
            stats={"total_received": 100.0, "total_sent": 50.0},
            history=[]
        )
        self.assertIn("Hamyon", wallet_out)
        self.assertIn("P2P", wallet_out)

        settings_tpl = self.env.get_template("settings.html")
        settings_out = settings_tpl.render(
            domain="sstudio.uz",
            user={"id": 1, "username": "testuser", "name": "Test", "surname": "User", "status": "freemium"}
        )
        self.assertIn("Sozlamalar", settings_out)


if __name__ == "__main__":
    unittest.main()

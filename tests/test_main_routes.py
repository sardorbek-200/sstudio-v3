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

    def test_quizer_service_routes(self):
        """Quizer servisi marshrutlari to'g'ri ro'yxatdan o'tganini tekshirish"""
        quizer_paths = [route.path for route in quizer_app.routes]
        self.assertIn("/", quizer_paths)
        self.assertIn("/health", quizer_paths)

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


if __name__ == "__main__":
    unittest.main()

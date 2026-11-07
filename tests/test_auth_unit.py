import unittest
from datetime import date
from shared.security import hash_password, verify_password, create_access_token, decode_access_token
from services.auth.app.schemas import RegisterRequest, LoginRequest


class TestAuthCore(unittest.TestCase):
    def test_argon2_password_hashing(self):
        """Argon2 parolni to'g'ri hashlayotgani va tekshirayotganini tekshirish"""
        raw_pass = "SuperSecret123!"
        hashed = hash_password(raw_pass)

        self.assertNotEqual(hashed, raw_pass)
        self.assertTrue(hashed.startswith("$argon2"))
        self.assertTrue(verify_password(raw_pass, hashed))
        self.assertFalse(verify_password("Noto'g'riParol", hashed))

    def test_jwt_token_creation_and_decoding(self):
        """30 kunlik JWT sessiya tokenini yaratish va o'qish"""
        payload = {"sub": "101", "username": "sardorbek"}
        token = create_access_token(payload)

        decoded = decode_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "101")
        self.assertEqual(decoded["username"], "sardorbek")
        self.assertIn("exp", decoded)

    def test_register_schema_validation(self):
        """Foydalanuvchi ma'lumotlari sxemasi to'g'ri validatsiya qilinishini tekshirish"""
        valid_data = {
            "username": "sardor_dev",
            "password": "mypassword123",
            "name": "Sardor",
            "surname": "Karimov",
            "birthday": date(2013, 5, 20),
            "gmail": "sardor@example.com"
        }
        req = RegisterRequest(**valid_data)
        self.assertEqual(req.username, "sardor_dev")
        self.assertEqual(req.birthday.year, 2013)


if __name__ == "__main__":
    unittest.main()

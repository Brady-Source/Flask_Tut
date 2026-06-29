import unittest
import time
from app import create_app, db
from app.models import User, Role, Permission


class TokenExpirationTestCase(unittest.TestCase):
    """Exercise 13 — Token expiration test (Chapter 14)"""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_token_expires(self):
        # Create a test user directly — bypasses Google OAuth
        u = User(username='testuser', email='test@example.com', confirmed=True)
        db.session.add(u)
        db.session.commit()

        # Generate a very short-lived token (5 seconds)
        token = u.generate_auth_token(expiration=5)
        self.assertIsNotNone(token, "Token should be generated successfully")

        # Token should verify immediately
        verified = User.verify_auth_token(token, expiration=5)
        self.assertIsNotNone(verified, "Token should be valid immediately after generation")
        self.assertEqual(verified.id, u.id, "Token should resolve to the correct user")

        print(f"\n--- Exercise 13 ---")
        print(f"Valid token:   {token[:60]}...")

        # Wait for expiration
        time.sleep(6)

        # Token should now be expired
        expired = User.verify_auth_token(token, expiration=5)
        self.assertIsNone(expired, "Token should return None after expiration")

        print(f"Expired token: {token}")
        print(f"verify_auth_token returned: {expired}  (None = correctly expired)")

    def test_token_generates_for_valid_user(self):
        u = User(username='tokenuser', email='token@example.com', confirmed=True)
        db.session.add(u)
        db.session.commit()

        token = u.generate_auth_token(expiration=3600)
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)

    def test_invalid_token_returns_none(self):
        result = User.verify_auth_token('this.is.not.a.real.token')
        self.assertIsNone(result, "A garbage token should return None")


class ApplicantUserTestCase(unittest.TestCase):
    """Exercise 14 — Applicant User account tests (Chapter 15)"""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_applicant_role_exists(self):
        role = Role.query.filter_by(name='Applicant User').first()
        self.assertIsNotNone(role, "Applicant User role must exist after insert_roles()")

    def test_applicant_role_permissions(self):
        role = Role.query.filter_by(name='Applicant User').first()

        # Applicant User should only have FOLLOW
        self.assertTrue(role.has_permission(Permission.FOLLOW))
        self.assertFalse(role.has_permission(Permission.COMMENT))
        self.assertFalse(role.has_permission(Permission.WRITE))
        self.assertFalse(role.has_permission(Permission.MODERATE))
        self.assertFalse(role.has_permission(Permission.ADMIN))

    def test_applicant_user_account(self):
        role = Role.query.filter_by(name='Applicant User').first()
        u = User(
            username='applicant1',
            email='applicant@example.com',
            confirmed=True,
            role=role
        )
        db.session.add(u)
        db.session.commit()

        # Confirm role was assigned
        self.assertEqual(u.role.name, 'Applicant User')

        # Can follow but nothing else
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertFalse(u.can(Permission.COMMENT))
        self.assertFalse(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.is_administrator())

    def test_applicant_is_not_admin(self):
        role = Role.query.filter_by(name='Applicant User').first()
        u = User(
            username='applicant2',
            email='applicant2@example.com',
            confirmed=True,
            role=role
        )
        db.session.add(u)
        db.session.commit()
        self.assertFalse(u.is_administrator())

    def test_applicant_token_generation(self):
        role = Role.query.filter_by(name='Applicant User').first()
        u = User(
            username='applicant3',
            email='applicant3@example.com',
            confirmed=True,
            role=role
        )
        db.session.add(u)
        db.session.commit()

        # Applicant users can still generate API tokens
        token = u.generate_auth_token(expiration=3600)
        self.assertIsNotNone(token)

        verified = User.verify_auth_token(token)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.id, u.id)

    def test_applicant_api_access(self):
        role = Role.query.filter_by(name='Applicant User').first()
        u = User(
            username='applicant4',
            email='applicant4@example.com',
            confirmed=True,
            role=role
        )
        db.session.add(u)
        db.session.commit()

        token = u.generate_auth_token(expiration=3600)
        response = self.client.get(
            f'/api/v1/users/{u.id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        # Should return 200 — reading own profile is allowed
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()

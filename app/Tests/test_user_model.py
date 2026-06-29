import unittest
from app import create_app, db
from app.models import User, AnonymousUser, Role, Permission


class ApplicantUserTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_applicant_user_role(self):
        r = Role.query.filter_by(name='Applicant User').first()
        u = User(email='applicant@example.com', username='applicant1', role=r)
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertFalse(u.can(Permission.COMMENT))
        self.assertFalse(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_applicant_is_not_administrator(self):
        r = Role.query.filter_by(name='Applicant User').first()
        u = User(email='applicant2@example.com', username='applicant2', role=r)
        self.assertFalse(u.is_administrator())

    def test_applicant_role_permissions(self):
        r = Role.query.filter_by(name='Applicant User').first()
        self.assertIsNotNone(r)
        self.assertTrue(r.has_permission(Permission.FOLLOW))
        self.assertFalse(r.has_permission(Permission.COMMENT))
        self.assertFalse(r.has_permission(Permission.WRITE))
        self.assertFalse(r.has_permission(Permission.MODERATE))
        self.assertFalse(r.has_permission(Permission.ADMIN))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.FOLLOW))
        self.assertFalse(u.can(Permission.COMMENT))
        self.assertFalse(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))
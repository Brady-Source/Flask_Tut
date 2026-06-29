import unittest
import json
import time
from app import create_app, db
from app.models import User, Role


class TokenExpirationTestCase(unittest.TestCase):

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

    def get_api_headers(self, token):
        return {
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def test_no_auth(self):
        response = self.client.get(
            '/api/v1/users/1',
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_bad_token(self):
        response = self.client.get(
            '/api/v1/users/1',
            headers=self.get_api_headers('bad-token'))
        self.assertEqual(response.status_code, 401)

    def test_token_auth(self):
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', username='john',
                 confirmed=True, role=r)
        db.session.add(u)
        db.session.commit()

        token = u.generate_auth_token(expiration=3600)
        self.assertIsNotNone(token)
        print(f'\n--- Exercise 13: Valid Token ---')
        print(f'Token: {token}')

        response = self.client.get(
            '/api/v1/users/{}'.format(u.id),
            headers=self.get_api_headers(token))
        self.assertEqual(response.status_code, 200)

        json_response = json.loads(response.get_data(as_text=True))
        self.assertEqual(json_response['username'], 'john')

    def test_expired_token(self):
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u = User(email='expire@example.com', username='expireuser',
                 confirmed=True, role=r)
        db.session.add(u)
        db.session.commit()

        token = u.generate_auth_token(expiration=5)
        self.assertIsNotNone(token)

        verified = User.verify_auth_token(token, expiration=5)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.id, u.id)

        print(f'\n--- Exercise 13: Expired Token ---')
        print(f'Token (valid):   {token}')

        time.sleep(6)

        expired = User.verify_auth_token(token, expiration=5)
        self.assertIsNone(expired)

        print(f'Token (expired): {token}')
        print(f'verify_auth_token returned: {expired}  <- None confirms expiration')
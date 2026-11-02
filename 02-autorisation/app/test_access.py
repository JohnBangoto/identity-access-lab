"""Vérifie la logique d'accès sans Keycloak : la session est simulée.

Lancer depuis ce dossier :  python -m unittest test_access -v
"""
import json
import os
import tempfile
import time
import unittest

from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

import app as webapp


class AccessMatrix(unittest.TestCase):
    def setUp(self):
        self.log = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        self.log.close()
        webapp.LOG_FILE = self.log.name
        webapp.app.config["TESTING"] = True
        self.client = webapp.app.test_client()

    def tearDown(self):
        os.unlink(self.log.name)

    def login_as(self, username, roles):
        with self.client.session_transaction() as sess:
            sess["user"] = {"username": username, "roles": roles}

    def entries(self):
        with open(self.log.name, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_anonyme_redirige_vers_login(self):
        for path in ("/compta", "/serveurs"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.headers["Location"].endswith("/login"))

    def test_alice_finance(self):
        self.login_as("alice", ["default-roles-labiam", "finance-user", "offline_access"])
        self.assertEqual(self.client.get("/compta").status_code, 200)
        self.assertEqual(self.client.get("/serveurs").status_code, 403)

    def test_bob_it(self):
        self.login_as("bob", ["default-roles-labiam", "it-user", "offline_access"])
        self.assertEqual(self.client.get("/compta").status_code, 403)
        self.assertEqual(self.client.get("/serveurs").status_code, 200)

    def test_sans_role_metier_tout_est_refuse(self):
        self.login_as("carol", ["default-roles-labiam"])
        self.assertEqual(self.client.get("/compta").status_code, 403)
        self.assertEqual(self.client.get("/serveurs").status_code, 403)

    def test_journal_des_decisions(self):
        self.login_as("alice", ["finance-user"])
        self.client.get("/compta")
        self.client.get("/serveurs")
        decisions = [(e["user"], e["resource"], e["decision"]) for e in self.entries()]
        self.assertEqual(decisions, [("alice", "compta", "allow"), ("alice", "serveurs", "deny")])

    def test_la_page_refusee_n_affiche_aucun_jeton(self):
        self.login_as("bob", ["it-user"])
        body = self.client.get("/compta").get_data(as_text=True)
        self.assertIn("403", body)
        self.assertIn("finance-user", body)
        self.assertNotIn("eyJ", body)


class TokenVerification(unittest.TestCase):
    """Vérifie le contrôle du jeton avec de vraies signatures RSA, sans Keycloak."""

    def setUp(self):
        self.key = RSAKey.generate_key(2048, parameters={"kid": "test-key"})
        webapp.get_jwks = lambda: KeySet([self.key])

    def make_token(self, key=None, **overrides):
        claims = {
            "iss": webapp.ISSUER,
            "exp": int(time.time()) + 300,
            "preferred_username": "alice",
            "realm_access": {"roles": ["finance-user"]},
        }
        claims.update(overrides)
        return jwt.encode({"alg": "RS256", "kid": "test-key"}, claims, key or self.key)

    def test_jeton_valide(self):
        claims = webapp.read_access_token(self.make_token())
        self.assertEqual(claims["preferred_username"], "alice")
        self.assertEqual(claims["realm_access"]["roles"], ["finance-user"])

    def test_jeton_expire_refuse(self):
        with self.assertRaises(Exception):
            webapp.read_access_token(self.make_token(exp=int(time.time()) - 3600))

    def test_mauvais_emetteur_refuse(self):
        with self.assertRaises(Exception):
            webapp.read_access_token(self.make_token(iss="http://localhost:8080/realms/master"))

    def test_signature_falsifiee_refusee(self):
        autre_cle = RSAKey.generate_key(2048, parameters={"kid": "test-key"})
        with self.assertRaises(Exception):
            webapp.read_access_token(self.make_token(key=autre_cle))


if __name__ == "__main__":
    unittest.main()

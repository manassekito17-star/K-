"""Exécute les cas de tests/conformite/ dans la suite de tests unittest."""

import unittest

from tests import conformite_lanceur


class TestConformite(unittest.TestCase):
    def test_cas(self):
        cas = conformite_lanceur.lister_cas()
        self.assertEqual(len(cas), 48)
        for nom in cas:
            with self.subTest(cas=nom):
                problemes = conformite_lanceur.executer_cas(nom)
                self.assertEqual(problemes, [], "\n".join(problemes))


if __name__ == "__main__":
    unittest.main()

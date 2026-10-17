"""No database required: tests that wrong cohort/package/plan references are rejected."""
from dataclasses import dataclass
import unittest
from app.services.rdp_application_preferences import validate_package_preference


@dataclass
class Package:
    id: int = 10
    programme_version_id: int = 20
    is_active: bool = True


@dataclass
class Plan:
    id: int = 30
    cohort_id: int = 40
    package_id: int = 10
    is_active: bool = True


class PreferenceTests(unittest.TestCase):
    def check(self, **overrides):
        args = dict(cohort_id=40, programme_version_id=20,
                    requested_package_id=10, requested_fee_plan_id=30,
                    package=Package(), plan=Plan())
        args.update(overrides)
        return validate_package_preference(**args)

    def test_valid_preference(self): self.assertIsNone(self.check())
    def test_invalid_cohort(self):
        with self.assertRaises(ValueError): self.check(cohort_id=41)
    def test_invalid_version(self):
        with self.assertRaises(ValueError): self.check(programme_version_id=21)
    def test_legacy_cohort(self):
        with self.assertRaises(ValueError): self.check(programme_version_id=None)
    def test_other_plan(self):
        with self.assertRaises(ValueError): self.check(requested_fee_plan_id=31)
    def test_other_package(self):
        with self.assertRaises(ValueError): self.check(requested_package_id=11)
    def test_missing_plan(self):
        with self.assertRaises(ValueError): self.check(plan=None)
    def test_missing_package(self):
        with self.assertRaises(ValueError): self.check(package=None)
    def test_inactive_plan(self):
        with self.assertRaises(ValueError): self.check(plan=Plan(is_active=False))
    def test_inactive_package(self):
        with self.assertRaises(ValueError): self.check(package=Package(is_active=False))
    def test_plan_package_mismatch(self):
        with self.assertRaises(ValueError): self.check(plan=Plan(package_id=70))
    def test_plan_from_other_cohort(self):
        with self.assertRaises(ValueError): self.check(plan=Plan(cohort_id=44))
    def test_package_from_other_version(self):
        with self.assertRaises(ValueError): self.check(package=Package(programme_version_id=15))
    def test_omitted_package(self):
        with self.assertRaises(ValueError): self.check(requested_package_id=None)


if __name__ == '__main__':
    unittest.main(verbosity=2)

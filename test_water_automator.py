#!/usr/bin/env python3
"""Tests for naming the water-treatment proposal document after the requested product(s)."""

import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, "/home/hermes/developer/JobTread API")
from water_treatment_automator import (
    build_document_name,
    WaterTreatmentAutomator,
    PKGP_WHOLE_HOUSE_FILTRATION_ID,
    PKGP_REVERSE_OSMOSIS_ID,
    PKGP_UV_FILTER_ID,
)


class TestBuildDocumentName(unittest.TestCase):
    """Pure naming logic — no network."""

    def test_single_package_uses_its_label(self):
        self.assertEqual(build_document_name([PKGP_REVERSE_OSMOSIS_ID]), "Reverse Osmosis")
        self.assertEqual(build_document_name([PKGP_WHOLE_HOUSE_FILTRATION_ID]), "Whole House Filtration")
        self.assertEqual(build_document_name([PKGP_UV_FILTER_ID]), "UV Filter")

    def test_multiple_packages_use_generic_bundle_name(self):
        self.assertEqual(
            build_document_name([PKGP_REVERSE_OSMOSIS_ID, PKGP_WHOLE_HOUSE_FILTRATION_ID]),
            "Water Treatment Package",
        )

    def test_no_packages_is_consultation(self):
        self.assertEqual(build_document_name([]), "Water Treatment Consultation")

    def test_unknown_package_falls_back(self):
        self.assertEqual(build_document_name(["not-a-real-id"]), "Water Treatment")


class TestDocumentNamingFollowsResolvedRequest(unittest.TestCase):
    """The document name follows the *resolved* package set, not just the form submitted.
    Note: an RO form always pulls the RO package (ro_opt_selected), so an RO lead who also
    asks for whole-house filtration becomes a bundle ("Water Treatment Package") — crucially
    NOT just "Reverse Osmosis", which is the behavior the request called for."""

    def _run_with(self, origin_page, goals):
        job_id = "mock-job"
        job_response = {
            "currentGrant": {"organization": {"jobs": {"nodes": [{
                "id": job_id, "name": "Mock Job",
                "customFieldValues": {"nodes": [
                    {"value": goals, "customField": {"id": "22PV9iPYXdgk", "name": "What are your goals?"}},
                ]},
                "location": {
                    "id": "loc", "name": "Site",
                    "customFieldValues": {"nodes": [
                        {"value": "Yes", "customField": {"id": "22PV9jLYfUip", "name": "Pre-plumbed softener loop?"}},
                    ]},
                    "account": {
                        "id": "acc", "name": "Jane Doe",
                        "customFieldValues": {"nodes": [
                            {"value": origin_page, "customField": {"id": "22PXggf2y4NV", "name": "originating page"}},
                        ]},
                    },
                },
            }]}}}
        }
        mock_client = MagicMock()
        mock_client.query.return_value = job_response
        mock_client.create_document_from_template.return_value = {
            "id": "doc", "name": "Whatever", "type": "customerOrder"
        }

        automator = WaterTreatmentAutomator()
        automator.client = mock_client
        automator.process_submission(job_id)
        return mock_client, job_id

    def test_ro_form_with_whole_house_goal_is_bundle_not_just_ro(self):
        # RO form (always pulls RO) + whole-house goal (pulls WH) => bundle, not "Reverse Osmosis".
        mock_client, job_id = self._run_with(
            origin_page="reverse-osmosis",
            goals=["I want filtration in the whole house"],
        )
        doc_call = mock_client.create_document_from_template.call_args
        self.assertEqual(
            doc_call[1]["package_template_ids"],
            [PKGP_WHOLE_HOUSE_FILTRATION_ID, PKGP_REVERSE_OSMOSIS_ID],
        )
        self.assertEqual(doc_call[1]["subject"], "Water Treatment Package")
        mock_client.update_job.assert_called_once_with(job_id, name="Water Treatment Package")

    def test_ro_form_drinking_water_goal_named_reverse_osmosis(self):
        mock_client, job_id = self._run_with(
            origin_page="reverse-osmosis",
            goals=["top quality drinkable water"],
        )
        doc_call = mock_client.create_document_from_template.call_args
        self.assertEqual(doc_call[1]["package_template_ids"], [PKGP_REVERSE_OSMOSIS_ID])
        self.assertEqual(doc_call[1]["subject"], "Reverse Osmosis")
        mock_client.update_job.assert_called_once_with(job_id, name="Reverse Osmosis")

    def test_softener_form_named_whole_house_filtration(self):
        # Water-softener form with no special goals resolves to Whole House Filtration only.
        mock_client, job_id = self._run_with(origin_page="water-softener", goals=[])
        doc_call = mock_client.create_document_from_template.call_args
        self.assertEqual(doc_call[1]["package_template_ids"], [PKGP_WHOLE_HOUSE_FILTRATION_ID])
        self.assertEqual(doc_call[1]["subject"], "Whole House Filtration")
        mock_client.update_job.assert_called_once_with(job_id, name="Whole House Filtration")


if __name__ == "__main__":
    unittest.main()

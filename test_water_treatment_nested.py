#!/usr/bin/env python3
"""Simulation test for verifying the recursive, selection-preserving Water Treatment budget copying."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Path setup
sys.path.insert(0, "/home/hermes/developer/JobTread API")
from jobtread import JobTreadClient
from water_treatment_automator import WaterTreatmentAutomator

class TestWaterTreatmentAutomatorDryRun(unittest.TestCase):
    """Test suite executing the entire automator logic with MagicMock dry-run assertions."""

    @patch("jobtread.JobTreadClient")
    def test_simulation(self, MockClientClass):
        print("\nRunning Water Treatment Automator Dry-Run Test (Zero network mutation)...")
        
        # Instantiate mock client
        mock_client = MockClientClass.return_value
        
        # Mock Job Query responses
        job_id = "mock-job-id-123"
        job_response = {
            "currentGrant": {
                "organization": {
                    "jobs": {
                        "nodes": [
                            {
                                "id": job_id,
                                "name": "Mock Active Job",
                                "customFieldValues": {
                                    "nodes": [
                                        {
                                            "value": ["5 Micron Sediment Filter"],
                                            "customField": {
                                                "id": "22PV7qnEkJSj", # Addons
                                                "name": "Water Softener Addons"
                                            }
                                        },
                                        {
                                            "value": ["Soften water"],
                                            "customField": {
                                                "id": "22PV9iPYXdgk", # Goals
                                                "name": "What are your goals?"
                                            }
                                        }
                                    ]
                                },
                                "location": {
                                    "id": "loc-99",
                                    "name": "Gilbert Site",
                                    "customFieldValues": {
                                        "nodes": [
                                            {
                                                "value": "Yes",
                                                "customField": {
                                                    "id": "22PV9jLYfUip", # Loop status
                                                    "name": "Pre-plumbed softener loop?"
                                                }
                                            }
                                        ]
                                    },
                                    "account": {
                                        "id": "acc-44",
                                        "name": "Alex Witkowski (2)",
                                        "customFieldValues": {
                                            "nodes": [
                                                {
                                                    "value": "water-softener",
                                                    "customField": {
                                                        "id": "22PXggf2y4NV", # Originating Page
                                                        "name": "originating page"
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_client.query.return_value = job_response
        
        # Mock template response for recursive copies
        mock_client.add_cost_group_from_template_recursive.return_value = {
            "costGroup": {
                "id": "new-test-group-id",
                "name": "Whole House Filtration"
            },
            "costItems": []
        }
        
        # Run automator with mock client
        automator = WaterTreatmentAutomator()
        automator.client = mock_client
        automator.process_submission(job_id)
        
        # Verify customer reply comment was added
        self.assertTrue(mock_client.query.called)
        comment_calls = [
            call for call in mock_client.query.call_args_list 
            if "createComment" in call[0][0]
        ]
        self.assertEqual(len(comment_calls), 1)
        sent_cmt = comment_calls[0][0][0]["createComment"]["$"]["message"]
        self.assertEqual(
            sent_cmt, 
            "Hi Alex Witkowski! Thank you for filling out Gentry's Water Softener form. We're reviewing your submission and writing your quote now."
        )
        print("--> Reply message asserted perfectly.")

        # Verify recursive add was invoked for selected packages
        self.assertTrue(mock_client.add_cost_group_from_template_recursive.called)
        add_calls = mock_client.add_cost_group_from_template_recursive.call_args_list
        # Whole House Filtration package should be pulled based on origin_page='water-softener'
        self.assertEqual(add_calls[0][1]["template_group_id"], "22PCTaQaFm3e") # PKGP_WHOLE_HOUSE_FILTRATION_ID
        print("--> Budget additions asserted perfectly. Zero dummy jobs written!")

if __name__ == "__main__":
    unittest.main()

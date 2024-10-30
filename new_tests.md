To create unit tests for each class (SheetSelection, Config, FieldSelection, and ResultsView), you’ll want to simulate user actions, check responses, and verify session data or context. Here’s a guide on setting up tests for each class:

Setup

	1.	Create a tests.py file within the same app as your views.
	2.	Import necessary Django testing tools:

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware


	3.	Use Django’s Client to simulate requests, and set up session data where required.

1. Testing SheetSelection

class SheetSelectionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("Analytics:Reconciler:sheet_selection")
        self.session_data = {
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData.xlsx"},
                {"id": 2, "filename": "InventoryReport.xlsx"},
            ]
        }

    def test_get_initial(self):
        session = self.client.session
        session.update(self.session_data)
        session.save()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Reconciler/sheet_selection.html")
        # Verify initial context contains file data
        formset_data = response.context["formset"].initial
        expected_data = [
            {"file_id": 1, "file_name": "SalesData.xlsx"},
            {"file_id": 2, "file_name": "InventoryReport.xlsx"}
        ]
        self.assertEqual(formset_data, expected_data)

    def test_form_submission(self):
        session = self.client.session
        session.update(self.session_data)
        session.save()
        
        form_data = {
            "form-0-sheet": "Sheet1",
            "form-1-sheet": "Summary",
        }
        response = self.client.post(self.url, form_data)
        
        # Check if the sheets are stored in the session
        session = self.client.session
        self.assertEqual(session["reconciler_sheets"], ["Sheet1", "Summary"])
        self.assertRedirects(response, reverse("Analytics:Reconciler:config"))

2. Testing Config

class ConfigTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("Analytics:Reconciler:config")
        self.session_data = {
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData.xlsx"},
                {"id": 2, "filename": "InventoryReport.xlsx"},
            ],
            "reconciler_sheets": ["Sheet1", "Summary"]
        }

    def test_get_initial_context(self):
        session = self.client.session
        session.update(self.session_data)
        session.save()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Reconciler/config.html")
        # Check context for filenames
        self.assertEqual(response.context["file_1_name"], "SalesData.xlsx")
        self.assertEqual(response.context["file_2_name"], "InventoryReport.xlsx")

    def test_form_submission(self):
        session = self.client.session
        session.update(self.session_data)
        session.save()
        
        form_data = {
            "form-0-file_1_fields": "Product ID",
            "form-0-file_2_fields": "Product Code",
            "form-1-file_1_fields": "Quantity",
            "form-1-file_2_fields": "Stock",
        }
        response = self.client.post(self.url, form_data)
        # Check redirect after submission
        self.assertRedirects(response, reverse("Analytics:Reconciler:field_selection"))

3. Testing FieldSelection

class FieldSelectionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("Analytics:Reconciler:field_selection")
        self.session_data = {
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData.xlsx"},
                {"id": 2, "filename": "InventoryReport.xlsx"},
            ],
            "reconciler_sheets": ["Sheet1", "Summary"],
            "fields1": ["Product ID", "Quantity"],
            "fields2": ["Product Code", "Stock"]
        }

    def test_form_submission(self):
        session = self.client.session
        session.update(self.session_data)
        session.save()

        form_data = {
            "file_1_fields": ["Product ID", "Quantity"],
            "file_2_fields": ["Product Code", "Stock"],
        }
        response = self.client.post(self.url, form_data)
        self.assertRedirects(response, reverse("Analytics:Reconciler:final"))
        # Test that a success message is added to the response
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("task_status" in str(m) for m in messages))

4. Testing ResultsView

class ResultsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("Analytics:Reconciler:results")
        self.session_data = {
            "job_id": 12345,  # Example job_id
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData.xlsx"},
                {"id": 2, "filename": "InventoryReport.xlsx"},
            ],
        }

    def test_get_context_data(self):
        session = self.client.session
        session.update(self.session_data)
        session.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Reconciler/results.html")
        # Check for the feedback link and dashboard output
        self.assertIn("feedback_href", response.context)
        self.assertIn("dashboard_output", response.context)
        self.assertEqual(
            response.context["dashboard_output"],
            "This is where the dashboard for K8s Job 12345 should show."
        )

Summary

These tests simulate each step:

	•	SheetSelection: Verifies the initial data for form fields, correct template, and session updates after form submission.
	•	Config: Checks initial file information in the context and the redirection on submission.
	•	FieldSelection: Tests final field selections, form submission, and message handling.
	•	ResultsView: Ensures context data like feedback and dashboard output displays correctly.

This setup should help you confirm each view’s expected behavior. Let me know if you need further adjustments or explanations on specific parts!
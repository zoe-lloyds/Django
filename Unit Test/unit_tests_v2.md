To create unit tests for each class (SheetSelection, Config, FieldSelection, and ResultsView), you’ll want to simulate user actions, check responses, and verify session data or context.  Here’s a guide on setting up tests for each class:

## Setup

* Create a tests. py file within the same app as your views. 
* Import necessary Django testing tools:

```
from django. test import TestCase, Client
from django. urls import reverse
from django. contrib. sessions. middleware import SessionMiddleware
```

Use Django’s Client to simulate requests, and set up session data where required. 

## 1.  Testing SheetSelection

```
class SheetSelectionTest(TestCase):
    def setUp(self):
        self. client = Client()
        self. url = reverse("Analytics:Reconciler:sheet_selection")
        self. session_data = {
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData. xlsx"},
                {"id": 2, "filename": "InventoryReport. xlsx"},
            ]
        }

    def test_get_initial(self):
        session = self. client. session
        session. update(self. session_data)
        session. save()
        
        response = self. client. get(self. url)
        self. assertEqual(response. status_code, 200)
        self. assertTemplateUsed(response, "Reconciler/sheet_selection. html")
        # Verify initial context contains file data
        formset_data = response. context["formset"]. initial
        expected_data = [
            {"file_id": 1, "file_name": "SalesData. xlsx"},
            {"file_id": 2, "file_name": "InventoryReport. xlsx"}
        ]
        self. assertEqual(formset_data, expected_data)

    def test_form_submission(self):
        session = self. client. session
        session. update(self. session_data)
        session. save()
        
        form_data = {
            "form-0-sheet": "Sheet1",
            "form-1-sheet": "Summary",
        }
        response = self. client. post(self. url, form_data)
        
        # Check if the sheets are stored in the session
        session = self. client. session
        self. assertEqual(session["reconciler_sheets"], ["Sheet1", "Summary"])
        self. assertRedirects(response, reverse("Analytics:Reconciler:config"))
```

## 2.  Testing Config

```
class ConfigTest(TestCase):
    def setUp(self):
        self. client = Client()
        self. url = reverse("Analytics:Reconciler:config")
        self. session_data = {
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData. xlsx"},
                {"id": 2, "filename": "InventoryReport. xlsx"},
            ],
            "reconciler_sheets": ["Sheet1", "Summary"]
        }

    def test_get_initial_context(self):
        session = self. client. session
        session. update(self. session_data)
        session. save()
        
        response = self. client. get(self. url)
        self. assertEqual(response. status_code, 200)
        self. assertTemplateUsed(response, "Reconciler/config. html")
        # Check context for filenames
        self. assertEqual(response. context["file_1_name"], "SalesData. xlsx")
        self. assertEqual(response. context["file_2_name"], "InventoryReport. xlsx")

    def test_form_submission(self):
        session = self. client. session
        session. update(self. session_data)
        session. save()
        
        form_data = {
            "form-0-file_1_fields": "Product ID",
            "form-0-file_2_fields": "Product Code",
            "form-1-file_1_fields": "Quantity",
            "form-1-file_2_fields": "Stock",
        }
        response = self. client. post(self. url, form_data)
        # Check redirect after submission
        self. assertRedirects(response, reverse("Analytics:Reconciler:field_selection"))
```

## 3.  Testing FieldSelection

```
class FieldSelectionTest(TestCase):
    def setUp(self):
        self. client = Client()
        self. url = reverse("Analytics:Reconciler:field_selection")
        self. session_data = {
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData. xlsx"},
                {"id": 2, "filename": "InventoryReport. xlsx"},
            ],
            "reconciler_sheets": ["Sheet1", "Summary"],
            "fields1": ["Product ID", "Quantity"],
            "fields2": ["Product Code", "Stock"]
        }

    def test_form_submission(self):
        session = self. client. session
        session. update(self. session_data)
        session. save()

        form_data = {
            "file_1_fields": ["Product ID", "Quantity"],
            "file_2_fields": ["Product Code", "Stock"],
        }
        response = self. client. post(self. url, form_data)
        self. assertRedirects(response, reverse("Analytics:Reconciler:final"))
        # Test that a success message is added to the response
        messages = list(response. wsgi_request. _messages)
        self. assertTrue(any("task_status" in str(m) for m in messages))
```

## 4.  Testing ResultsView

```
class ResultsViewTest(TestCase):
    def setUp(self):
        self. client = Client()
        self. url = reverse("Analytics:Reconciler:results")
        self. session_data = {
            "job_id": 12345,  # Example job_id
            "reconciler_input_selected_files": [
                {"id": 1, "filename": "SalesData. xlsx"},
                {"id": 2, "filename": "InventoryReport. xlsx"},
            ],
        }

    def test_get_context_data(self):
        session = self. client. session
        session. update(self. session_data)
        session. save()

        response = self. client. get(self. url)
        self. assertEqual(response. status_code, 200)
        self. assertTemplateUsed(response, "Reconciler/results. html")
        # Check for the feedback link and dashboard output
        self. assertIn("feedback_href", response. context)
        self. assertIn("dashboard_output", response. context)
        self. assertEqual(
            response. context["dashboard_output"],
            "This is where the dashboard for K8s Job 12345 should show. "
        )
```

## Summary

These tests simulate each step:

* **SheetSelection**: Verifies the initial data for form fields, correct template, and session updates after form submission. 
* **Config**: Checks initial file information in the context and the redirection on submission. 
* **FieldSelection**: Tests final field selections, form submission, and message handling. 
* **ResultsView**: Ensures context data like feedback and dashboard output displays correctly. 

This setup should help you confirm each view’s expected behavior.  Let me know if you need further adjustments or explanations on specific parts!

## 5.Input view
Here’s a unit test setup for the InputView class.  This will cover checking the initial form setup, context, and session updates after form submission. 

```
from django. test import TestCase, Client
from django. urls import reverse
from UserFolder. models import UserChunkedUpload
from django. contrib. auth import get_user_model

User = get_user_model()

class InputViewTest(TestCase):
    def setUp(self):
        # Set up a client and a test user
        self. client = Client()
        self. user = User. objects. create_user(username="testuser", password="password")
        self. client. login(username="testuser", password="password")

        # Create some test files for the user
        self. file1 = UserChunkedUpload. objects. create(user=self. user, status=2, filename="File1. csv")
        self. file2 = UserChunkedUpload. objects. create(user=self. user, status=2, filename="File2. csv")

        # URL for InputView
        self. url = reverse("Analytics:Reconciler:input")

    def test_get_initial_data_in_context(self):
        response = self. client. get(self. url)
        self. assertEqual(response. status_code, 200)
        self. assertTemplateUsed(response, "Reconciler/input. html")

        # Check if "application_name" is set in the initial context
        self. assertIn("application_name", response. context["form"]. initial)
        self. assertEqual(response. context["form"]. initial["application_name"], "reconciler")

    def test_form_file_queryset_filtering(self):
        response = self. client. get(self. url)
        # Check that only files with the correct status for this user are in the queryset
        form_files = response. context["form"]. fields["files_and_folders"]. queryset
        self. assertQuerysetEqual(form_files, UserChunkedUpload. objects. filter(user=self. user, status=2))

    def test_form_submission_saves_files_in_session(self):
        # Simulate form submission with files and folders selected
        form_data = {
            "files_and_folders": [self. file1. id, self. file2. id],
            "application_name": "reconciler",
        }

        response = self. client. post(self. url, form_data)
        
        # Check that the selected files are saved in the session
        session_files = self. client. session["reconciler_input_selected_files"]
        expected_data = [
            {"id": self. file1. id, "filename": "File1. csv"},
            {"id": self. file2. id, "filename": "File2. csv"},
        ]
        self. assertEqual(session_files, expected_data)
        
        # Confirm the redirect after successful form submission
        self. assertRedirects(response, reverse("Analytics:Reconciler:sheet_selection"))

```
Explanation of Each Test
<ul>
<li> test_get_initial_data_in_context: Ensures the InputView loads the correct template and that the initial form context has "application_name" set to "reconciler". 
<li>test_form_file_queryset_filtering: Verifies that the files_and_folders field in the form filters to only include files uploaded by the current user with status=2. 
<li> `test_form_submission_saves_files_in_session`:
<ul>
<li> Simulates a form submission where the user selects specific files. 
<li> Checks if the selected files are correctly serialized and saved in the session under "reconciler_input_selected_files". 
<li> Confirms that after submission, the user is redirected to the sheet_selection page. 
</ul>
</ul>
This setup covers the key functionality of the InputView and should provide a solid test foundation for your form’s handling, context, and session interactions.  Let me know if you need more details on any part!

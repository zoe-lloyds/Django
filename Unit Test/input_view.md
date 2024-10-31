Here’s a comprehensive set of unit tests for the InputView class in Django, covering URL resolution, request handling, and proper functioning of the serializer. These tests ensure that the view behaves as expected in terms of URL routing, request processing, and session storage.

```
from django.test import TestCase, Client
from django.urls import reverse, resolve
from UserFolder.models import UserChunkedUpload, UserChunkedUploadSerialiser
from UserFolder.forms import DataInputForm
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.conf import settings

class InputViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("Analytics:Reconciler:input")

        # Create a test user and log them in
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.login(username="testuser", password="testpass")

        # Create some UserChunkedUpload objects to simulate uploaded files for this user
        self.file1 = UserChunkedUpload.objects.create(
            user_id=self.user.id, status=2, filename="file1.csv"
        )
        self.file2 = UserChunkedUpload.objects.create(
            user_id=self.user.id, status=2, filename="file2.csv"
        )

    def test_input_url_resolves(self):
        # Check that the input URL resolves to the correct view
        view = resolve(self.url)
        self.assertEqual(view.func.__name__, "InputView")

    def test_get_request_renders_correct_template(self):
        # Simulate a GET request to the InputView
        response = self.client.get(self.url)
        
        # Check that the response status is OK
        self.assertEqual(response.status_code, 200)
        # Verify the correct template is used
        self.assertTemplateUsed(response, "Reconciler/input.html")

    def test_form_in_context_on_get_request(self):
        # Simulate a GET request to ensure the form is in context
        response = self.client.get(self.url)
        
        # Check that the form is in the context
        self.assertIn("form", response.context)
        # Verify the form is an instance of DataInputForm
        self.assertIsInstance(response.context["form"], DataInputForm)

    def test_post_request_saves_files_to_session(self):
        # Simulate a POST request with file selection form data
        form_data = {
            "files_and_folders": [self.file1.id, self.file2.id],
            "application_name": "reconciler",
        }
        response = self.client.post(self.url, form_data)

        # Verify that the selected files were serialized and saved in session
        session = self.client.session
        self.assertIn("reconciler_input_selected_files", session)
        
        # Check serialized data in session
        selected_files = session["reconciler_input_selected_files"]
        expected_files = [
            {"id": self.file1.id, "filename": "file1.csv"},
            {"id": self.file2.id, "filename": "file2.csv"},
        ]
        self.assertEqual(selected_files, expected_files)
        # Check redirection to sheet selection
        self.assertRedirects(response, reverse("Analytics:Reconciler:sheet_selection"))

    def test_serialiser_correctly_serializes_data(self):
        # Create form data as expected by the serializer
        form_data = {
            "files_and_folders": [self.file1, self.file2],
        }
        
        # Serialize the form data
        serializer = UserChunkedUploadSerialiser(form_data["files_and_folders"], many=True)
        serialized_data = serializer.data
        
        # Check that serializer produces expected output
        expected_serialized_data = [
            {"id": self.file1.id, "filename": "file1.csv"},
            {"id": self.file2.id, "filename": "file2.csv"},
        ]
        self.assertEqual(serialized_data, expected_serialized_data)

    def test_invalid_file_selection_returns_error(self):
        # Simulate a POST request with empty files selection
        form_data = {
            "files_and_folders": [],
            "application_name": "reconciler",
        }
        response = self.client.post(self.url, form_data)

        # Check that the form is invalid and renders the page with an error
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "files_and_folders", "Input error")

    def test_invalid_application_name_handling(self):
        # Simulate POST with an invalid application name
        form_data = {
            "files_and_folders": [self.file1.id],
            "application_name": "unknown_app",
        }
        response = self.client.post(self.url, form_data)

        # Check for a generic form error due to invalid application name
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")

    def test_user_not_logged_in_redirect(self):
        # Log the user out to test unauthenticated access
        self.client.logout()
        response = self.client.get(self.url)
        
        # Verify redirect to login
        login_url = settings.LOGIN_URL + "?next=" + self.url
        self.assertRedirects(response, login_url)

```
Explanation of Each Test

	1.	test_input_url_resolves:
	•	Checks that the URL for InputView correctly maps to the view function.
	2.	test_get_request_renders_correct_template:
	•	Simulates a GET request to the InputView and verifies the correct template (input.html) is used.
	3.	test_form_in_context_on_get_request:
	•	Confirms that a DataInputForm instance is in the context when rendering the form.
	4.	test_post_request_saves_files_to_session:
	•	Submits a valid POST request and checks that the selected files are serialized and saved in the session. It also verifies redirection to the sheet_selection page.
	5.	test_serialiser_correctly_serializes_data:
	•	Directly tests the UserChunkedUploadSerialiser to ensure it correctly serializes file data, confirming that the serialized output matches the expected format.
	6.	test_invalid_file_selection_returns_error:
	•	Simulates a form submission without any file selection to check
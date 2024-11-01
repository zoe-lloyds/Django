To test the `Config` view, we need to ensure that it behaves correctly in terms of:

1. **Session data access**: Verifying that the view retrieves necessary data from the session.
2. **Context and form setup**: Confirming that `file_1_name`, `file_2_name`, and `formset` are correctly passed to the context.
3. **Form submission and redirection**: Ensuring a valid form submission redirects to the `success_url` and processes data as expected.

Here's a test class for the `Config` view:

```python
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model
from .views import Config
from .forms import ReconciliationFieldsFormset
from myapp.models import UserChunkedUpload

class ConfigViewTests(TestCase):
    """
    Unit tests for the Config view to verify context setup, form behavior,
    and session updates upon form submission.
    """
    databases = {"default", "application-db"}

    def setUp(self):
        """Set up the test environment by initializing the request factory, URL, and required database objects."""
        self.factory = RequestFactory()
        self.url = reverse("Analytics:Reconciler:config")

        # Create a test user and log them in if needed
        self.user = get_user_model().objects.create_user(username="testuser", password="password")
        
        # Create two UserChunkedUpload instances for testing, simulating two files
        self.test_file_1 = UserChunkedUpload.objects.create(
            id=1,
            user=self.user,
            filename="test_file_1.xlsx",
            file_extension=".xlsx",
            ingestion_metadata={"column_headers": {"Header1": [], "Header2": []}},
            status=2
        )
        
        self.test_file_2 = UserChunkedUpload.objects.create(
            id=2,
            user=self.user,
            filename="test_file_2.xlsx",
            file_extension=".xlsx",
            ingestion_metadata={"column_headers": {"HeaderA": [], "HeaderB": []}},
            status=2
        )

    def _setup_request(self, method='get', data=None):
        """
        Helper method to initialize a request with session support and logged-in user.
        """
        request = getattr(self.factory, method)(self.url, data=data)
        request.user = self.user  # Set the user on the request
        # Manually add session support
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        return request

    def test_get_context_data(self):
        """
        Test that context data includes file names and formset when files are in session.
        """
        # Mock session data for two files and selected sheets
        request = self._setup_request()
        request.session["reconciler_input_selected_files"] = [
            {"id": self.test_file_1.id, "filename": "test_file_1.xlsx"},
            {"id": self.test_file_2.id, "filename": "test_file_2.xlsx"},
        ]
        request.session["reconciler_sheets"] = ["Sheet1", "Sheet2"]
        request.session.save()

        # Instantiate the view and call the GET method
        view = Config.as_view()
        response = view(request)

        # Check the response status and context data
        self.assertEqual(response.status_code, 200)
        context = response.context_data
        self.assertEqual(context["file_1_name"], "test_file_1.xlsx")
        self.assertEqual(context["file_2_name"], "test_file_2.xlsx")
        self.assertIn("formset", context)

    def test_form_valid_saves_data_to_session_and_redirects(self):
        """
        Test form submission with valid data and session update.
        Verifies that selected fields are processed and redirects to success_url.
        """
        # Set up request with session data and a valid post payload for two forms in formset
        request = self._setup_request(method='post', data={
            "form-0-file_1_fields": "Header1",
            "form-0-file_2_fields": "HeaderA",
            "form-1-file_1_fields": "Header2",
            "form-1-file_2_fields": "HeaderB",
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "0",
        })
        request.session["reconciler_input_selected_files"] = [
            {"id": self.test_file_1.id, "filename": "test_file_1.xlsx"},
            {"id": self.test_file_2.id, "filename": "test_file_2.xlsx"},
        ]
        request.session["reconciler_sheets"] = ["Sheet1", "Sheet2"]
        request.session.save()

        # Test form_valid functionality by invoking the POST method
        view = Config.as_view()
        response = view(request)
        
        # Check if response is a redirect or not
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("Analytics:Reconciler:field_selection"))

        # Verify the session contains the selected fields data
        file1_cols = [f.cleaned_data["file_1_fields"] for f in response.context_data["form"]]
        file2_cols = [f.cleaned_data["file_2_fields"] for f in response.context_data["form"]]
        self.assertEqual(file1_cols, ["Header1", "Header2"])
        self.assertEqual(file2_cols, ["HeaderA", "HeaderB"])
```

### Explanation of Tests

1. **`test_get_context_data`**:
   - Mocks session data with two files and sheet names.
   - Verifies that the context contains the file names and a valid formset when the view is accessed via GET.
  
2. **`test_form_valid_saves_data_to_session_and_redirects`**:
   - Sets up a POST request with valid form data to simulate form submission.
   - Confirms that a successful submission redirects to `success_url`.
   - Asserts that the fields selected in `file_1_fields` and `file_2_fields` are processed correctly in the session.

These tests ensure the `Config` view behaves as expected under various conditions. Adjust any field names or model attributes if they differ in your actual setup. Let me know if this works for you!

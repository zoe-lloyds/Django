##

class SheetSelectionTest(TestCase):
    databases = {"default", "application-db"}

    def setUp(self):
        """
        Set up a test UserChunkedUpload instance for testing excel sheets.
        """
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="testuser", password="testpass"
        )
        self.upload = UserChunkedUpload.objects.create(
            filename="test_file.xlsx",
            file_extension=".xlsx",
            user=self.user,
            ingestion_metadata={
                "column_headers": {
                    "Sheet1": ["Header1", "Header2"],
                    "Sheet2": ["Header3", "Header4"],
                }
            },
            status=2,
        )
        self.factory = RequestFactory()
        self.session = {
            "reconciler_input_selected_files": [
                {"id": self.upload.id, "filename": self.upload.filename}
            ]
        }
        self.request = self.factory.get(reverse_lazy("Analytics:Reconciler:config"))
        self.request.session = self.session
        self.request.user = self.user  # Ensure the request has a user

    def test_get_initial(self):
        view = SheetSelection()
        view.request = self.request
        initial = view.get_initial()
        expected_initial = [
            {"file_id": self.upload.id, "file_name": self.upload.filename}
        ]
        self.assertEqual(initial, expected_initial)

    def test_get_form_kwargs(self):
        view = SheetSelection()
        view.request = self.request
        form_kwargs = view.get_form_kwargs()
        self.assertIn("form_kwargs", form_kwargs)
        self.assertEqual(form_kwargs["form_kwargs"]["request"], self.request)

    def test_get_context_data(self):
        view = SheetSelection()
        view.request = self.request
        view.object = None  # Required for get_context_data
        context = view.get_context_data()
        self.assertIn("formset", context)

    def test_form_valid(self):
        view = SheetSelection()
        view.request = self.request
        
        # Include management form data
        form_data = {
            'form-0-sheet': 'Sheet1',
        }
        
        # Initial data for the formset
        initial_data = [
            {'file_id': self.upload.id, 'file_name': self.upload.filename}
        ]
        
        # Initialize the formset with the correct form_kwargs and initial data
        form = SheetSelectionFormSet(data=form_data, 
                                     initial=initial_data, 
                                     form_kwargs={'request': self.request})
        print(form)
        self.assertTrue(form.is_valid())
        
        response = view.form_valid(form)
        self.assertEqual(self.request.session["reconciler_sheets"], ["Sheet1"])
        self.assertEqual(response.url, self.success_url)


        class SheetSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        file_qs = UserChunkedUpload.objects.get(pk=self.initial["file_id"])
        ext = file_qs.file_extension
        self.fields["file_id"].queryset = UserChunkedUpload.objects.filter(
            user_id=self.request.user.id
        ).filter(status=2)
        if ext[:4] == ".xls":
            sheets = file_qs.ingestion_metadata["column_headers"].keys()
            choices = [(sheet, sheet) for sheet in sheets]
            self.fields["sheet"] = forms.ChoiceField(choices=choices, required=False)
            self.fields["file_type"].initial = "excel"
        else:
            self.fields["sheet"] = forms.ChoiceField(
                choices=[("NA", "NA")], required=False
            )

    file_type = forms.CharField(widget=forms.HiddenInput(), initial="unkn")
    file_name = forms.CharField(widget=forms.HiddenInput())
    file_id = forms.ModelChoiceField(widget=forms.HiddenInput(), queryset=None)


SheetSelectionFormSet = formset_factory(
    SheetSelectionForm, formset=BaseFormSet, extra=0
)

##
Certainly! Here’s a full example of how to set up a unit test for the `SheetSelection` view, covering the main scenarios like handling `.xls` files, setting up form initial data, and testing form submission.

```python
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.forms import formset_factory
from unittest.mock import patch, MagicMock
from .views import SheetSelection
from .forms import SheetSelectionForm, SheetSelectionFormSet
from myapp.models import UserChunkedUpload  # adjust this import based on your app structure

class SheetSelectionViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse("Analytics:Reconciler:sheet_selection")

    def _setup_request(self, method='get', data=None):
        request = getattr(self.factory, method)(self.url, data=data)
        # Manually add session support
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        return request

    @patch("myapp.models.UserChunkedUpload.objects.get")
    def test_get_initial_with_excel_file(self, mock_get):
        # Mock session data and UserChunkedUpload data for an Excel file
        request = self._setup_request()
        request.session["reconciler_input_selected_files"] = [{"id": 1, "filename": "test_file.xls"}]

        # Mock UserChunkedUpload model response
        mock_file = MagicMock()
        mock_file.file_extension = ".xls"
        mock_file.ingestion_metadata = {"column_headers": {"Sheet1": [], "Sheet2": []}}
        mock_get.return_value = mock_file

        # Instantiate the view
        view = SheetSelection.as_view()
        response = view(request)

        # Check the response status
        self.assertEqual(response.status_code, 200)
        
        # Verify initial data setup in the form
        formset = response.context_data["formset"]
        self.assertEqual(len(formset.forms), 1)
        self.assertIn("Sheet1", dict(formset.forms[0].fields["sheet"].choices))
        self.assertIn("Sheet2", dict(formset.forms[0].fields["sheet"].choices))

    @patch("myapp.models.UserChunkedUpload.objects.get")
    def test_get_initial_with_non_excel_file(self, mock_get):
        # Mock session data and UserChunkedUpload data for a non-Excel file
        request = self._setup_request()
        request.session["reconciler_input_selected_files"] = [{"id": 2, "filename": "test_file.csv"}]

        # Mock UserChunkedUpload model response
        mock_file = MagicMock()
        mock_file.file_extension = ".csv"
        mock_get.return_value = mock_file

        # Instantiate the view
        view = SheetSelection.as_view()
        response = view(request)

        # Check the response status
        self.assertEqual(response.status_code, 200)
        
        # Verify that the form has a "NA" choice for non-Excel files
        formset = response.context_data["formset"]
        self.assertEqual(formset.forms[0].fields["sheet"].choices, [("NA", "NA")])

    @patch("myapp.models.UserChunkedUpload.objects.get")
    def test_form_valid_saves_to_session(self, mock_get):
        # Set up request with session data and a valid post payload
        request = self._setup_request(method='post', data={
            "form-0-sheet": "Sheet1",
            "form-0-file_id": 1,
            "form-0-file_name": "test_file.xls",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
        })
        request.session["reconciler_input_selected_files"] = [{"id": 1, "filename": "test_file.xls"}]
        request.session.save()

        # Mock UserChunkedUpload model response
        mock_file = MagicMock()
        mock_file.file_extension = ".xls"
        mock_file.ingestion_metadata = {"column_headers": {"Sheet1": []}}
        mock_get.return_value = mock_file

        # Test form_valid functionality
        view = SheetSelection.as_view()
        response = view(request)

        # Check redirection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("Analytics:Reconciler:config"))

        # Confirm that selected sheets are saved to session
        self.assertIn("reconciler_sheets", request.session)
        self.assertEqual(request.session["reconciler_sheets"], ["Sheet1"])
```

### Explanation of Each Test Case

1. **`test_get_initial_with_excel_file`**:
   - Sets up session data with an Excel file.
   - Mocks `UserChunkedUpload` to return Excel file metadata with sheet names.
   - Verifies that the formset initializes with sheet choices for Excel files.

2. **`test_get_initial_with_non_excel_file`**:
   - Sets up session data with a non-Excel file.
   - Mocks `UserChunkedUpload` to represent a non-Excel file.
   - Checks that only "NA" is available as a choice for non-Excel files.

3. **`test_form_valid_saves_to_session`**:
   - Mocks a post request with data, ensuring a sheet choice is selected.
   - Mocks `UserChunkedUpload` to represent an Excel file.
   - Verifies redirection to `success_url` and confirms that selected sheets are saved to the session.

Each test case uses the `RequestFactory` for simulating requests and `SessionMiddleware` to enable session handling in the request. The `patch` decorator is used to mock the `UserChunkedUpload` model, ensuring these tests remain isolated from the database.

##
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model
from .views import SheetSelection
from .forms import SheetSelectionFormSet
from myapp.models import UserChunkedUpload  # Adjust the import based on your app structure

class SheetSelectionViewTests(TestCase):
    """
    Unit tests for the SheetSelection view to verify initial data setup,
    form behavior based on file type, and session updates upon form submission.
    """

    def setUp(self):
        """Set up the test environment by initializing the request factory, URL, and required database objects."""
        self.factory = RequestFactory()
        self.url = reverse("Analytics:Reconciler:sheet_selection")

        # Create a test user and log them in if needed
        self.user = get_user_model().objects.create_user(username="testuser", password="password")
        
        # Create a real UserChunkedUpload instance for testing
        self.test_file = UserChunkedUpload.objects.create(
            id=1,
            user=self.user,
            file_extension=".xls",
            ingestion_metadata={"column_headers": {"Sheet1": [], "Sheet2": []}}
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

    def test_get_initial_with_excel_file(self):
        """
        Test that the initial form data includes sheet choices when an Excel file is selected.

        Verifies that the formset is populated with the correct sheet choices based on the file metadata.
        """
        # Mock session data for an Excel file
        request = self._setup_request()
        request.session["reconciler_input_selected_files"] = [{"id": self.test_file.id, "filename": "test_file.xls"}]
        request.session.save()

        # Instantiate the view and call the GET method
        view = SheetSelection.as_view()
        response = view(request)

        # Check the response status and formset content
        self.assertEqual(response.status_code, 200)
        formset = response.context_data["formset"]
        self.assertEqual(len(formset.forms), 1)
        self.assertIn("Sheet1", dict(formset.forms[0].fields["sheet"].choices))
        self.assertIn("Sheet2", dict(formset.forms[0].fields["sheet"].choices))

    def test_get_initial_with_non_excel_file(self):
        """
        Test that the form contains a single 'NA' choice for non-Excel files.

        Verifies that 'NA' is the only option for sheet selection when the file is not an Excel type.
        """
        # Mock session data for a non-Excel file
        request = self._setup_request()
        request.session["reconciler_input_selected_files"] = [{"id": self.test_file.id, "filename": "test_file.csv"}]
        self.test_file.file_extension = ".csv"  # Change file extension to a non-Excel type
        self.test_file.save()
        request.session.save()

        # Instantiate the view and call the GET method
        view = SheetSelection.as_view()
        response = view(request)

        # Check the response status and formset content
        self.assertEqual(response.status_code, 200)
        formset = response.context_data["formset"]
        self.assertEqual(formset.forms[0].fields["sheet"].choices, [("NA", "NA")])

    def test_form_valid_saves_to_session(self):
        """
        Test form submission and session update upon successful form validation.

        Verifies that selected sheets are saved to the session after a valid form submission,
        and checks redirection to the configured success URL.
        """
        # Set up request with session data and a valid post payload
        request = self._setup_request(method='post', data={
            "form-0-sheet": "Sheet1",
            "form-0-file_id": self.test_file.id,  # Match file_id with the actual object
            "form-0-file_name": "test_file.xls",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
        })
        request.session["reconciler_input_selected_files"] = [{"id": self.test_file.id, "filename": "test_file.xls"}]
        request.session.save()

        # Test form_valid functionality by invoking the POST method
        view = SheetSelection.as_view()
        response = view(request)

        # Check if response is a redirect or not
        if hasattr(response, "url"):
            # Verify redirection and session update
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("Analytics:Reconciler:config"))
            self.assertIn("reconciler_sheets", request.session)
            self.assertEqual(request.session["reconciler_sheets"], ["Sheet1"])
        else:
            # Print form errors if response is a TemplateResponse
            print("Form errors:", response.context_data["form"].errors)
            self.fail("Expected a redirect response but got a TemplateResponse. Check form validation.")


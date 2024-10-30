from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from .views import InputView
from .models import UserChunkedUpload
from .forms import DataInputForm

class InputViewTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.url = reverse("Analytics:Reconciler:sheet_selection")
        
        # Mock files for testing
        UserChunkedUpload.objects.create(
            user=self.user,
            file_extension='.csv',
            status=2
        )

    def test_form_renders_correct_template(self):
        response = self.client.get(reverse("input"))  # Assuming 'input' is the name for InputView in urls
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Reconciler/input.html")

    def test_form_submission_success(self):
        # Mock form data
        form_data = {
            "files_and_folders": UserChunkedUpload.objects.filter(user=self.user).values_list('id', flat=True),
            "application_name": "reconciler"
        }
        response = self.client.post(reverse("input"), data=form_data)

        # Check redirection to success_url
        self.assertRedirects(response, self.url)

        # Check if session data is set correctly
        session_data = self.client.session.get("reconciler_input_selected_files")
        self.assertIsNotNone(session_data)

    def test_form_invalid_submission(self):
        # Submit without required files_and_folders field
        form_data = {
            "application_name": "reconciler"
        }
        response = self.client.post(reverse("input"), data=form_data)
        
        # Check that the form errors are returned in response
        self.assertEqual(response.status_code, 200)  # Renders form again with errors
        self.assertFormError(response, 'form', 'files_and_folders', "Input error")
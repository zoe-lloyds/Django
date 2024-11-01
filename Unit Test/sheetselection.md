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

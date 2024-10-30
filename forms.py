import logging
import os

from django import forms
from django.core.exceptions import ValidationError
from django.forms import formsets
from django.forms.formsets import BaseFormSet

from AARP.forms import CheckboxSelectMultipleWithAttrs
from UserFolder.forms import file_headers
from UserFolder.models import UserChunkedUpload

logger = logging.getLogger(__name__)


def file_list(user_folder):
    # initial value is blank
    files_list = [("", "")]
    for path, subdirs, files in os.walk(user_folder):
        for name in files:
            if os.path.splitext(name)[1] in [".csv", ".txt", ".xlsx", ".xls"]:
                display_name = os.path.join(path, name).replace(user_folder, "")
                files_list.append((display_name, display_name))
    return files_list


def excel_sheets(file_id) -> dict:
    file_qs = UserChunkedUpload.objects.get(pk=file_id)

    if file_qs.file_extension[:4] == ".xls":
        return file_qs.ingestion_metadata["column_headers"].keys()


class ReconciliationFieldsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # grab the form data from the session/context
        form_data = kwargs.pop("form_data", None)
        super(ReconciliationFieldsForm, self).__init__(*args, **kwargs)
        if form_data:
            # Set name and choices for the 2 files
            self.fields["file_1_fields"].label = False
            self.fields["file_2_fields"].label = False
            self.fields["file_1_fields"].choices = [
                (header, header)
                for header in file_headers(
                    form_data["file_1_id"], form_data["file_1_sheet"]
                )
            ]
            self.fields["file_2_fields"].choices = [
                (header, header)
                for header in file_headers(
                    form_data["file_2_id"], form_data["file_2_sheet"]
                )
            ]
        super(ReconciliationFieldsForm, self).full_clean()

    file_1_fields = forms.ChoiceField(
        widget=forms.Select(attrs={"class": "custom-select"})
    )
    file_2_fields = forms.ChoiceField(
        widget=forms.Select(attrs={"class": "custom-select"})
    )


class BaseLinkFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return

        file1_cols = []
        file2_cols = []
        duplicates = False

        for form in self.forms:
            if form.cleaned_data and not duplicates:
                file1_field = form.cleaned_data["file_1_fields"]
                file2_field = form.cleaned_data["file_2_fields"]

                # Check that fields have only been entered once
                if file1_field and file2_field:
                    if file1_field in file1_cols:
                        duplicates = True
                        break
                    else:
                        file1_cols.append(file1_field)

                    if file2_field in file2_cols:
                        duplicates = True
                        break
                    else:
                        file2_cols.append(file2_field)

        if duplicates:
            raise ValidationError("Cannot match on a column more than once")


ReconciliationFieldsFormset = formsets.formset_factory(
    ReconciliationFieldsForm, formset=BaseLinkFormSet
)


class FileFieldSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        form_data = kwargs.pop("form_data", None)
        super(FileFieldSelectionForm, self).__init__(*args, **kwargs)

        file_1_rec_fields = form_data.get("file_1_rec_fields", None)
        file_2_rec_fields = form_data.get("file_2_rec_fields", None)
        file_1_headers = file_headers(form_data["file_1_id"], form_data["file_1_sheet"])
        file_2_headers = file_headers(form_data["file_2_id"], form_data["file_2_sheet"])

        self.fields["file_1_fields"].choices = self.build_choices(
            file_1_headers, file_1_rec_fields
        )
        self.fields["file_2_fields"].choices = self.build_choices(
            file_2_headers, file_2_rec_fields
        )

    @staticmethod
    def build_choices(headers, rec_fields):
        # Add the choices to the MultipleChoiceField.
        # Messy loop just in case we want to reconcile >2 files in the future and can use the fields_dict

        choices = []
        for field in headers:
            # add the disabled and checked attributes at the start of the choices so will be at top of list
            if field in rec_fields:
                # Can add extra attributes here and they will be available in the 2nd element of the tuple passed
                # to the template as a dictionary for instance:
                # {% for checkbox in form.file_2_fields.field.choices %} checkbox.1
                choices.insert(
                    0,
                    (
                        (
                            field,
                            {
                                "label": field,
                                "checked": True,
                                "readonly": "readonly",
                            },
                        )
                    ),
                )
            # otherwise append as a regular field if not used for reconciliation
            else:
                choices.append((field, field))
        return choices

    file_1_fields = forms.MultipleChoiceField(
        widget=CheckboxSelectMultipleWithAttrs,
        help_text="Select which fields you wish to retain in the output of the reconciliation. "
        "This should include the field to reconcile the files on.",
    )
    file_2_fields = forms.MultipleChoiceField(
        widget=CheckboxSelectMultipleWithAttrs,
        help_text="Select which fields you wish to retain in the output of the reconciliation. "
        "This should include the field to reconcile the files on.",
    )



class FileSelectForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(FileSelectForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "id-FileSelectForm"
        self.helper.form_method = "post"
        self.helper.form_action = ""
        self.fields[
            "file"
        ].help_text = "You can select multiple files at once. Max file size: 4.2GB"

        self.helper.layout = Layout(
            Field("file", id="id_file", css_class="btn btn-outline-secondary"),
            ButtonHolder(Submit("submit", "Upload Files")),
        )

    # TODO: was this commented line. Check if file input is still being cleared
    # file = forms.FileField(widget=forms.ClearableFileInput(attrs={"multiple": True}))
    file = forms.FileField()


class FileOnlyModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    default_error_messages = {
        "required": "No files selected. Select which files to use using the checkbox."
    }

    def clean(self, value: Any) -> Any:
        """
        Given a list of possible PK values, only pass through the files and drop the folders.
        Raise a ValidationError if the model queryset is not an MPTTModel
        """
        if not issubclass(self.queryset.model, UserChunkedUpload):
            raise forms.ValidationError(
                "Field expects a UserChunkedUpload model to distinguish between files and folders."
            )

        key = self.to_field_name or "pk"
        try:
            value = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise forms.ValidationError(
                self.error_messages["list"],
                code="list",
            )
        # Filter available queryset to given choices from field
        qs = self.queryset.filter(**{"%s__in" % key: value})
        file_instances = list(qs.filter(file_or_folder=1).values_list("id", flat=True))
        return super().clean(file_instances)


application_choices = [
    ("ada", "ada"),
    ("textcomparison", "textcomparison"),
    ("stratified", "stratified"),
    ("reconciler", "reconciler"),
    ("outlier", "outlier"),
]


class DataInputForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["files_and_folders"].queryset = UserChunkedUpload.objects.filter(
            user_id=self.request.user.id
        ).filter(status=2)

    def clean(self):
        super().clean()
        application_name = self.cleaned_data.get("application_name")
        files_and_folders = self.cleaned_data.get("files_and_folders")

        if not files_and_folders:
            raise forms.ValidationError("Input error")

        max_file_choices = {
            "ada": 300,
            "textcomparison": 300,
            "stratified": 1,
            "reconciler": 2,
            "outlier": 1,
        }

        min_file_choices = {
            "ada": 1,
            "textcomparison": 2,
            "stratified": 1,
            "reconciler": 2,
            "outlier": 1,
        }

        valid_file_types_choices = {
            "ada": [
                ".pdf",
                ".docx",
                ".doc",
                ".pptx",
                "ppt",
                ".csv",
                ".txt",
                ".del",
                ".tsv",
                ".xlsx",
                ".xls",
                ".xlsm",
                ".xlsb",
            ],
            "textcomparison": [
                ".csv",
                ".txt",
                ".del",
                ".tsv",
                ".xlsx",
                ".xls",
                ".xlsm",
                ".xlsb",
            ],
            "stratified": [".csv", ".tsv", ".txt", ".xlsx"],
            "reconciler": [".csv", ".tsv", ".txt", ".xlsx"],
            "outlier": [".csv", ".txt", ".xlsx"],
        }

        max_files = max_file_choices[application_name]
        min_files = min_file_choices[application_name]
        valid_file_types = valid_file_types_choices[application_name]

        if len(files_and_folders) > max_files:
            msg = forms.ValidationError(
                "Too many files selected. Maximum number of files is %(max_files)s.",
                code="invalid",
                params={"max_files": max_files},
            )
            self.add_error("files_and_folders", msg)

        if len(files_and_folders) < min_files:
            msg = forms.ValidationError(
                "Not enough files selected. Minimum number of files is %(min_files)s.",
                code="invalid",
                params={"min_files": min_files},
            )
            self.add_error("files_and_folders", msg)

        if not set(files_and_folders.values_list("file_extension", flat=True)).issubset(
            valid_file_types
        ):
            msg = forms.ValidationError(
                "File type not supported. This application can only use files of the following types: %(valid_file_types)s.",
                code="invalid",
                params={"valid_file_types": ", ".join(valid_file_types)},
            )
            self.add_error("files_and_folders", msg)

        if application_name in ["stratified", "reconciler", "outlier"]:
            for f in files_and_folders:
                if f.offset > 250000000:
                    msg = forms.ValidationError(
                        "File is too large. This application is currently limited to 250MB per file."
                    )
                    self.add_error("files_and_folders", msg)
                    break

    files_and_folders = FileOnlyModelMultipleChoiceField(
        queryset=None,
        required=True,
    )
    application_name = forms.ChoiceField(
        choices=application_choices, widget=forms.HiddenInput()
    )
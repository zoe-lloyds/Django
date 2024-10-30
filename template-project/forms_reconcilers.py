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

from typing import Any
from django import forms
from django.forms import BaseFormSet, formset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, Field
from .models import UserChunkedUpload
from django.contrib.admin.widgets import AdminDateWidget


class ColumnChoiceField(forms.fields.ChoiceField):
    def validate(self, value):
        super(forms.fields.ChoiceField, self).validate(value)


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


class DataConfigurationForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        sheet = self.initial.get("sheet")
        file_qs = UserChunkedUpload.objects.get(pk=self.initial["file_id"])
        ext = file_qs.file_extension

        self.fields["id_column"] = ColumnChoiceField(label="ID Column")
        self.fields["data_column"] = ColumnChoiceField(label="Data Column")

        date_cols = [f"date_{x}" for x in [1, 2]]
        additional_cols = [f"additional_details_{x}" for x in [1, 2, 3, 4, 5]]
        additional_data = [f"additional_details_free_{x}" for x in [1, 2, 3, 4, 5]]
        field_choices = []
        if ext in [".tsv", ".csv", ".txt", ".del"]:
            self.fields["structured_file"].initial = True
            headers = file_headers(self.initial["file_id"])
            [field_choices.append((x, x)) for x in headers]
        elif ext[:4] == ".xls":
            self.fields["structured_file"].initial = True
            headers = file_headers(self.initial["file_id"], sheet)
            [field_choices.append((x, x)) for x in headers]
        else:
            self.fields["id_column"].required = False
            self.fields["data_column"].required = False
            self.fields["structured_file"].initial = False

        self.fields["id_column"].choices = field_choices
        self.fields["data_column"].choices = field_choices

        self.fields["date_pick_1"] = forms.DateField(
            widget=AdminDateWidget(), required=False
        )
        self.fields["date_pick_2"] = forms.DateField(
            widget=AdminDateWidget(), required=False
        )

        for x in additional_data:
            self.fields[x] = forms.CharField(required=False, max_length=100)

        for x in date_cols:
            self.fields[x] = ColumnChoiceField(required=False)
            self.fields[x].choices = [("", "---")] + field_choices

        for x in additional_cols:
            self.fields[x] = ColumnChoiceField(required=False)
            self.fields[x].choices = [("", "---")] + field_choices

    file_id = forms.ModelChoiceField(widget=forms.HiddenInput(), queryset=None)
    file_name = forms.CharField(widget=forms.HiddenInput())
    structured_file = forms.BooleanField(widget=forms.HiddenInput, required=False)

    def column_cleaning(self, column):
        if (
            self.cleaned_data["structured_file"]
            and self.cleaned_data["file_type"] == "unkn"
        ):
            headers = file_headers(
                self.cleaned_data["file_id"].pk, self.cleaned_data["sep"]
            )
            choices = headers["headers"]

            if not self.fields[column].required:
                choices.append("")

            if self.cleaned_data[column] not in choices:
                raise forms.ValidationError(
                    f"{self.cleaned_data[column]} is not a valid column name"
                )

        elif self.cleaned_data["structured_file"]:
            super(type(self.fields[column]), self.fields[column]).validate(
                self.cleaned_data[column]
            )

        return self.cleaned_data[column]

    def clean_id_column(self):
        clean = self.column_cleaning("id_column")
        return clean

    def clean_data_column(self):
        clean = self.column_cleaning("data_column")
        return clean

    def clean_date_1(self):
        clean = self.column_cleaning("date_1")
        return clean

    def clean_date_2(self):
        clean = self.column_cleaning("date_2")
        return clean

    def clean_additional_details_1(self):
        clean = self.column_cleaning("additional_details_1")
        return clean

    def clean_additional_details_2(self):
        clean = self.column_cleaning("additional_details_2")
        return clean

    def clean_additional_details_3(self):
        clean = self.column_cleaning("additional_details_3")
        return clean

    def clean_additional_details_4(self):
        clean = self.column_cleaning("additional_details_4")
        return clean

    def clean_additional_details_5(self):
        clean = self.column_cleaning("additional_details_5")
        return clean

    def clean(self):
        """Series of data checks for the inputs of the data headers form"""
        if self.cleaned_data["file_type"] != "excel":
            return self.cleaned_data
        else:
            sheets = []
            for x in (
                ["id_column", "data_column"] + self.date_cols + self.additional_cols
            ):
                if self.cleaned_data[x]:
                    sheets.append(self.cleaned_data[x].split("†")[0])
                    self.cleaned_data[x] = self.cleaned_data[x].split("†")[1]
            if len(set(sheets)) != 1:
                raise ValueError("All selected columns must be from the same sheet")
            else:
                self.cleaned_data["sheet"] = sheets[0]
                return self.cleaned_data


def file_headers(file_id, sheet_name=None):
    file_qs = UserChunkedUpload.objects.get(pk=file_id)

    if file_qs.file_extension[:4] == ".xls":
        if not sheet_name:
            sheet_name = list(file_qs.ingestion_metadata["column_headers"].keys())[0]
        headers = file_qs.ingestion_metadata["column_headers"][sheet_name]

    else:
        headers = file_qs.ingestion_metadata["column_headers"]

    return headers

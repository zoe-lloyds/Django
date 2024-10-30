import logging

import jsonpickle.ext.pandas as jsonpickle_pd
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy, reverse
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView

from Analytics.tasks import analytics_background_task
from Analytics.tasks import get_full_name
from Analytics.views import ResultsFormView
from UserFolder.forms import DataInputForm
from UserFolder.forms import SheetSelectionFormSet
from UserFolder.models import UserChunkedUpload, UserChunkedUploadSerialiser
from UserFolder.views import UserFolderFormView
from .forms import ReconciliationFieldsFormset, FileFieldSelectionForm
from .tasks import reconcile

jsonpickle_pd.register_handlers()
logger = logging.getLogger(__name__)

def index(request):
    return render(request, "Reconciler/index.html")


def interpreting_results(request):
    return render(request, "Reconciler/interpreting_results.html")


class InputView(UserFolderFormView):
    form_class = DataInputForm
    template_name = "Reconciler/input.html"
    success_url = reverse_lazy("Analytics:Reconciler:sheet_selection")

    def get_form_kwargs(self):
        kw = super(InputView, self).get_form_kwargs()
        kw["request"] = self.request
        return kw

    def get_initial(self):
        initial = super(InputView, self).get_initial()
        initial["application_name"] = "reconciler"
        return initial

    def form_valid(self, form) -> HttpResponse:
        # save selected files to session for use later
        self.request.session["reconciler_input_selected_files"] = (
            UserChunkedUploadSerialiser(
                form.cleaned_data["files_and_folders"], many=True
            ).data
        )
        return super().form_valid(form)


class SheetSelection(FormView):
    """
    For excel files, capture which sheet the end user would like to analyse
    For csv / other files, "not required"
    """

    success_url = reverse_lazy("Analytics:Reconciler:config")
    form_class = SheetSelectionFormSet
    template_name = "Reconciler/sheet_selection.html"

    def get_initial(self):
        input_files = self.request.session["reconciler_input_selected_files"]
        initial = [+
            {"file_id": file["id"], "file_name": file["filename"]}
            for file in input_files
        ]
        return initial

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["form_kwargs"] = {"request": self.request}
        return kw

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # formset is used in the template to display the form
        context["formset"] = context["form"]
        return context

    def form_valid(self, form):
        # save the selected sheets to the session for use later
        self.request.session["reconciler_sheets"] = [
            f["sheet"] for f in form.cleaned_data
        ]
        return super().form_valid(form)


class Config(FormView):
    success_url = reverse_lazy("Analytics:Reconciler:field_selection")
    form_class = ReconciliationFieldsFormset
    template_name = "Reconciler/config.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        session = self.request.session
        form_data = {
            "file_1_id": session["reconciler_input_selected_files"][0]["id"],
            "file_2_id": session["reconciler_input_selected_files"][1]["id"],
            "file_1_sheet": session["reconciler_sheets"][0],
            "file_2_sheet": session["reconciler_sheets"][1],
        }
        kw["form_kwargs"] = {"form_data": form_data}
        return kw

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.request.session
        input_files = session["reconciler_input_selected_files"]
        context["file_1_name"] = input_files[0]["filename"]
        context["file_2_name"] = input_files[1]["filename"]
        context["formset"] = context["form"]
        return context

    def form_valid(self, form):
        file1_cols = []
        file2_cols = []
        for f in form:
            file1_cols.append(f.cleaned_data["file_1_fields"])
            file2_cols.append(f.cleaned_data["file_2_fields"])


class FieldSelection(FormView):
    success_url = reverse_lazy("Analytics:Reconciler:final")
    form_class = FileFieldSelectionForm
    template_name = "Reconciler/field_selection.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        session = self.request.session
        form_data = {
            "file_1_id": session["reconciler_input_selected_files"][0]["id"],
            "file_2_id": session["reconciler_input_selected_files"][1]["id"],
            "file_1_sheet": session["reconciler_sheets"][0],
            "file_2_sheet": session["reconciler_sheets"][1],
            "file_1_rec_fields": session.get("fields1", None),
            "file_2_rec_fields": session.get("fields2", None),
        }
        kw["form_data"] = form_data
        return kw

    def form_valid(self, form):
        """
        build job for reconciler
        TODO fix this
        """
        request = self.request
        if request.META.get("REMOTE_USER"):
            file_id = request.META.get("REMOTE_USER").split("\\")[1:][0]
        else:
            file_id = request.META.get("USERNAME")
        if not file_id:
            file_id = request.user.username
        kwargs = {
            "file_id": file_id,
            "email_address": request.user.email,
            "file_1_name": request.session["reconciler_input_selected_files"][0][
                "filename"
            ],
            "file_2_name": request.session["reconciler_input_selected_files"][1][
                "filename"
            ],
            # Fields to reconcile on
            "fields1": request.session["fields1"],
            "fields2": request.session["fields2"],
            # All fields to keep
            "keep_fields1": form.cleaned_data["file_1_fields"],
            "keep_fields2": form.cleaned_data["file_2_fields"],
            "user_folder": settings.MEDIA_ROOT,
            "file_path_1": request.session["reconciler_input_selected_files"][0][
                "file"
            ],
            "file_path_2": request.session["reconciler_input_selected_files"][1][
                "file"
            ],
            "delimiter_1": request.session["sheet_1"],
            "delimiter_2": request.session["sheet_2"],
            "sheet_name_1": request.session["sheet_1"],
            "sheet_name_2": request.session["sheet_2"],
            "full_name": get_full_name(file_id),
            "user_id": request.user.username,
            "extension_1": request.session["reconciler_input_selected_files"][0][
                "file_extension"
            ],
            "extension_2": request.session["reconciler_input_selected_files"][1][
                "file_extension"
            ],
            "file_1_qs": UserChunkedUpload.objects.get(
                pk=request.session["reconciler_input_selected_files"][0]["id"]
            ).file.name,
            "file_2_qs": UserChunkedUpload.objects.get(
                pk=request.session["reconciler_input_selected_files"][1]["id"]
            ).file.name,
        }

        context = analytics_background_task(
            request=request,
            background_function=reconcile,
            kwargs=kwargs,
            task_name="reconciliation",
            result_destination="Once the output is generated it will be available in your user folder.",
        )

        message = context["task_status"]
        messages.success(request=self.request, message=mark_safe(message))
        return super().form_valid(form)


class ResultsView(ResultsFormView):
    """
    The results selector and / or dashboard output page.
    TODO: Results: This is part of the new architecture for utility results pages. Refer to this when refactoring other utilities.
    """

    # Django-specific variables
    template_name = "Reconciler/results.html"

    # ResultsFormView-specific variables
    # TODO: Results: To test the functionality of this, replace this with "ingestion" for now to populate the job list.
    job_type = "reconciler"

    def get_context_data(self, **kwargs: any) -> dict[str, any]:
        context = super().get_context_data(**kwargs)

        # ResultsFormView-specific variables
        context["feedback_href"] = (
            "mailto:$GIA-AARP?subject=AARP%20Reconciler%20Feedback&body="
        )
        # TODO: Results: Implement this.
        # context["download_href"] = reverse("Analytics:Reconciler:download_results")

        # Reconciler-specific output
        if self.job_id:
            output = (
                f"This is where the dashboard for K8s Job {self.job_id} should show."
            )
            context["dashboard_output"] = output

        return context

    def get_success_url(self) -> str:
        self.job_id = self.form.cleaned_data["timestamp"].id
        return reverse(
            "Analytics:Reconciler:dashboard", kwargs={"id": str(self.job_id)}
        )


def final(request):
    return render(request, "Reconciler/final.html")

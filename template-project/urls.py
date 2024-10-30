from django.urls import path

from . import views

app_name = "Reconciler"
urlpatterns = [
    path("", views.index, name="index"),
    path("data_input/", views.InputView.as_view(), name="data_input"),
    path("sheet_selection/", views.SheetSelection.as_view(), name="sheet_selection"),
    path("field_selection/", views.FieldSelection.as_view(), name="field_selection"),
    path("config/", views.Config.as_view(), name="config"),
    # TODO: Results: Merge the contents of interpreting_results into results.
    path("final/", views.final, name="final"),
    path(
        "interpreting_results/", views.interpreting_results, name="interpreting_results"
    ),
    path("results/", views.ResultsView.as_view(), name="results"),
    path("results/<id>", views.ResultsView.as_view(), name="dashboard"),
]

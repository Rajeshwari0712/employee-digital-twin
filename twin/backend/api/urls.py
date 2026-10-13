from django.urls import path
from . import views
urlpatterns = [
    path("health/", views.health), path("schema/", views.schema), path("summary/", views.summary),
    path("employees/", views.employee_list), path("employees/<str:emp_id>/", views.employee_detail),
    path("predict/", views.predict), path("whatif/", views.whatif), path("history/", views.history),
]

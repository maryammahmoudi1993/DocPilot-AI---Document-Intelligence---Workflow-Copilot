from django.urls import path

from apps.analytics.views import AnalyticsOverviewView, DashboardSummaryView

urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("analytics/", AnalyticsOverviewView.as_view(), name="analytics-overview"),
]

import csv
from datetime import date

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .filters import ExpenseFilter
from .models import Category, Expense
from .serializers import (
    CategorySerializer,
    ExpenseSerializer,
    MonthlySummarySerializer,
    MonthQuerySerializer,
    YearlyTrendSerializer,
    YearQuerySerializer,
)


def csv_safe(value) -> str:
    """Neutralise spreadsheet formulas (CSV injection) by prefixing risky cells with a quote."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


class OwnedQuerysetMixin:
    """Restrict every query to the logged-in user's rows and set them as owner on create."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CategoryViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class ExpenseViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.select_related("category")
    serializer_class = ExpenseSerializer
    filterset_class = ExpenseFilter
    search_fields = ["description"]
    ordering_fields = ["date", "amount", "created_at"]

    @extend_schema(
        parameters=[OpenApiParameter("month", str, description="YYYY-MM (default: current month)")],
        responses=MonthlySummarySerializer,
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        params = MonthQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        if "month" in params.validated_data:
            year, month = map(int, params.validated_data["month"].split("-"))
        else:
            year, month = services.current_month()
        summary = services.monthly_summary(request.user, year, month)
        return Response(MonthlySummarySerializer(summary).data)

    @extend_schema(
        parameters=[OpenApiParameter("year", int, description="Year (default: current year)")],
        responses=YearlyTrendSerializer,
    )
    @action(detail=False, methods=["get"])
    def trend(self, request):
        params = YearQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        year = params.validated_data.get("year", date.today().year)
        return Response(YearlyTrendSerializer(services.yearly_trend(request.user, year)).data)

    @extend_schema(responses={(200, "text/csv"): str})
    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        """Download the (filtered) expenses as a CSV file."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="expenses.csv"'
        writer = csv.writer(response)
        writer.writerow(["date", "amount", "category", "description"])
        for e in self.filter_queryset(self.get_queryset()):
            category = e.category.name if e.category else ""
            writer.writerow([e.date, e.amount, csv_safe(category), csv_safe(e.description)])
        return response

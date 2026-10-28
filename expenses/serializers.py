from rest_framework import serializers

from .models import Category, Expense


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "monthly_budget", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        owner = self.context["request"].user
        qs = Category.objects.filter(owner=owner, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a category with this name.")
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Expense
        fields = [
            "id",
            "amount",
            "date",
            "description",
            "category",
            "category_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow choosing categories that belong to the current user.
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["category"].queryset = Category.objects.filter(owner=request.user)


class MonthQuerySerializer(serializers.Serializer):
    month = serializers.RegexField(
        r"^\d{4}-(0[1-9]|1[0-2])$",
        help_text="Month in YYYY-MM format. Defaults to the current month.",
        required=False,
    )


class YearQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=1900, max_value=9999, required=False)


def money():
    return serializers.DecimalField(max_digits=14, decimal_places=2)


class CategoryTotalSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(allow_null=True)
    category = serializers.CharField()
    total = money()
    count = serializers.IntegerField()
    budget = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    over_budget = serializers.BooleanField()


class MonthlySummarySerializer(serializers.Serializer):
    month = serializers.CharField()
    total = money()
    count = serializers.IntegerField()
    by_category = CategoryTotalSerializer(many=True)


class MonthTotalSerializer(serializers.Serializer):
    month = serializers.CharField()
    total = money()


class YearlyTrendSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    total = money()
    months = MonthTotalSerializer(many=True)

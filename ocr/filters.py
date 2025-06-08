import django_filters
from .models import IdCard
from .choices import DocumentTypeChoices, DecisionChoices


class IdCardFilter(django_filters.FilterSet):
    """Filter for ID cards with custom confidence score filtering"""

    document_type = django_filters.ChoiceFilter(choices=DocumentTypeChoices.choices)
    decision = django_filters.ChoiceFilter(choices=DecisionChoices.choices)
    verified = django_filters.BooleanFilter()
    is_confirmed = django_filters.BooleanFilter()
    min_confidence = django_filters.NumberFilter(method="filter_min_confidence")
    max_confidence = django_filters.NumberFilter(method="filter_max_confidence")

    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        model = IdCard
        fields = [
            "document_type",
            "decision",
            "verified",
            "is_confirmed",
            "min_confidence",
            "max_confidence",
            "created_after",
            "created_before",
        ]

    def filter_min_confidence(self, queryset, name, value):
        """Filter by minimum confidence score"""
        if value is not None:
            # Since confidence_score is a property, we need to filter in Python
            # For better performance, consider adding a database field
            filtered_ids = [obj.id for obj in queryset if obj.confidence_score >= value]
            return queryset.filter(id__in=filtered_ids)
        return queryset

    def filter_max_confidence(self, queryset, name, value):
        """Filter by maximum confidence score"""
        if value is not None:
            filtered_ids = [obj.id for obj in queryset if obj.confidence_score <= value]
            return queryset.filter(id__in=filtered_ids)
        return queryset

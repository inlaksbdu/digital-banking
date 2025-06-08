import django_filters
from django.db.models import Case, FloatField, When
from django.db.models.functions import Cast, Coalesce
from .models import IdCard
from .choices import DocumentTypeChoices, DecisionChoices


class IdCardFilter(django_filters.FilterSet):
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

    def _get_confidence_annotation(self):
        confidence_fields = [
            "first_name__confidence",
            "middle_name__confidence",
            "last_name__confidence",
            "date_of_birth__confidence",
            "gender__confidence",
            "id_number__confidence",
            "document_number__confidence",
            "date_of_issue__confidence",
            "date_of_expiry__confidence",
            "country__confidence",
            "state__confidence",
            "nationality__confidence",
            "mrz__confidence",
        ]

        confidence_cases = []
        for field in confidence_fields:
            confidence_cases.append(
                Case(
                    When(**{f"{field}__isnull": False}, then=Cast(field, FloatField())),
                    default=0.0,
                    output_field=FloatField(),
                )
            )
        
        return Coalesce(
            Case(
                When(
                    **{f"{confidence_fields[0]}__isnull": False},
                    then=sum(confidence_cases) / len(confidence_cases),
                ),
                default=0.0,
                output_field=FloatField(),
            ),
            0.0,
        )

    def filter_min_confidence(self, queryset, name, value):
        if value is not None:
            if 'calculated_confidence' not in queryset.query.annotations:
                queryset = queryset.annotate(calculated_confidence=self._get_confidence_annotation())
            return queryset.filter(calculated_confidence__gte=value)
        return queryset

    def filter_max_confidence(self, queryset, name, value):
        if value is not None:
            if 'calculated_confidence' not in queryset.query.annotations:
                queryset = queryset.annotate(calculated_confidence=self._get_confidence_annotation())
            return queryset.filter(calculated_confidence__lte=value)
        return queryset

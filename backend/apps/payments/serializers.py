from decimal import Decimal

from rest_framework import serializers

from .models import LedgerEntry, Payment


def _money_field(**kwargs):
    return serializers.DecimalField(max_digits=14, decimal_places=2,
                                    read_only=True, **kwargs)


class CustomerPaymentSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.display_name",
                                          read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "booking", "provider_name", "method", "status",
                  "provider_recorded_amount", "customer_confirmed_amount",
                  "settled_amount", "settled_at", "created_at"]
        read_only_fields = fields


class ProviderPaymentSerializer(serializers.ModelSerializer):
    net_amount = _money_field(allow_null=True)

    class Meta:
        model = Payment
        fields = ["id", "booking", "method", "status",
                  "provider_recorded_amount", "customer_confirmed_amount",
                  "settled_amount", "commission_rate", "commission_amount",
                  "net_amount", "settled_at", "created_at"]
        read_only_fields = fields


class AdminPaymentSerializer(ProviderPaymentSerializer):
    provider_name = serializers.CharField(source="provider.display_name",
                                          read_only=True)
    customer_phone = serializers.CharField(source="customer.user.phone",
                                           read_only=True)

    class Meta(ProviderPaymentSerializer.Meta):
        fields = ProviderPaymentSerializer.Meta.fields + [
            "provider", "provider_name", "customer_phone", "flagged_at",
            "resolution_note",
        ]
        read_only_fields = fields


class LedgerEntrySerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display",
                                         read_only=True)

    class Meta:
        model = LedgerEntry
        fields = ["id", "kind", "kind_display", "amount", "booking",
                  "description", "reference", "created_at"]
        read_only_fields = fields


class EarningsTotalsSerializer(serializers.Serializer):
    gross = _money_field()
    commission = _money_field()
    net = _money_field()
    jobs = serializers.IntegerField(read_only=True)


class EarningsSummarySerializer(EarningsTotalsSerializer):
    balance = _money_field()
    outstanding_payable = _money_field()
    outstanding_receivable = _money_field()
    flagged_payments = serializers.IntegerField(read_only=True)


class EarningsPeriodSerializer(EarningsTotalsSerializer):
    period = serializers.CharField(read_only=True)


class ResolvePaymentSerializer(serializers.Serializer):
    settled_amount = serializers.DecimalField(max_digits=10,
                                              decimal_places=2,
                                              min_value=Decimal("0"))
    note = serializers.CharField(max_length=1000)


class SettlementSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2,
                                      min_value=Decimal("0.01"))
    reference = serializers.CharField(max_length=120, required=False,
                                      allow_blank=True, default="")

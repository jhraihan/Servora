from rest_framework import serializers

from .models import TrustSnapshot

class TrustSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustSnapshot
        fields = ["id", "score", "tier", "algo_version", "trigger",
                  "created_at"]
        read_only_fields = fields

class TrustAuditSerializer(TrustSnapshotSerializer):
    class Meta(TrustSnapshotSerializer.Meta):
        fields = TrustSnapshotSerializer.Meta.fields + ["factors"]
        read_only_fields = fields

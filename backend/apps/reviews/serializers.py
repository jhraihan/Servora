from rest_framework import serializers

from .models import CustomerRating, ProviderReply, Review


class ProviderReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderReply
        fields = ["id", "body", "created_at"]
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    reply = ProviderReplySerializer(read_only=True)
    was_edited = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "booking", "provider", "customer_name", "rating",
                  "punctuality", "quality", "professionalism",
                  "price_fairness", "comment", "reply", "was_edited",
                  "created_at"]
        read_only_fields = fields

    def get_customer_name(self, obj):
        full = obj.customer.user.full_name or ""
        parts = full.split()
        if not parts:
            return "Customer"
        if len(parts) == 1:
            return parts[0]
        return "%s %s." % (parts[0], parts[-1][0])

    def get_was_edited(self, obj):
        return obj.edit_count > 0


class OwnReviewSerializer(ReviewSerializer):
    is_published = serializers.BooleanField(read_only=True)
    is_editable = serializers.BooleanField(read_only=True)

    class Meta(ReviewSerializer.Meta):
        fields = ReviewSerializer.Meta.fields + [
            "is_published", "is_editable", "reveal_deadline", "is_hidden",
        ]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    booking = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    punctuality = serializers.IntegerField(min_value=1, max_value=5,
                                           required=False, allow_null=True)
    quality = serializers.IntegerField(min_value=1, max_value=5,
                                       required=False, allow_null=True)
    professionalism = serializers.IntegerField(min_value=1, max_value=5,
                                               required=False,
                                               allow_null=True)
    price_fairness = serializers.IntegerField(min_value=1, max_value=5,
                                              required=False,
                                              allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True,
                                    default="", max_length=2000)


class ReviewEditSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5,
                                      required=False)
    comment = serializers.CharField(required=False, allow_blank=True,
                                    max_length=2000)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Provide a rating or a comment to change."
            )
        return attrs


class ReplyCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000)


class CustomerRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRating
        fields = ["id", "booking", "rating", "comment", "created_at"]
        read_only_fields = fields


class CustomerRatingCreateSerializer(serializers.Serializer):
    booking = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True,
                                    default="", max_length=2000)


class HideReviewSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)

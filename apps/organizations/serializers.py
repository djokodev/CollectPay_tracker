from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import serializers

from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole


User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def validate_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom de l'organisation doit contenir au moins 3 caracteres.")
        return value.strip()

    def create(self, validated_data):
        if not validated_data.get("slug"):
            base_slug = slugify(validated_data["name"])
            slug = base_slug
            suffix = 1
            while Organization.objects.filter(slug=slug).exists():
                suffix += 1
                slug = f"{base_slug}-{suffix}"
            validated_data["slug"] = slug
        return super().create(validated_data)


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = (
            "id",
            "organization",
            "user_id",
            "username",
            "email",
            "role",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class AddOrganizationMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=OrganizationRole.choices, default=OrganizationRole.AGENT)

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Utilisateur introuvable.")
        return value


class SwitchActiveOrganizationSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()

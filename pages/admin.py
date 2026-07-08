from django.contrib import admin

from .models import AppointmentRequest, ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "is_processed")
    list_filter = ("is_processed",)
    search_fields = ("name", "email", "message")
    readonly_fields = ("name", "email", "phone", "subject", "message", "created_at")


@admin.register(AppointmentRequest)
class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "mode", "topic", "preferred_datetime", "created_at", "is_processed")
    list_filter = ("is_processed", "mode", "topic")
    search_fields = ("name", "email", "message")
    readonly_fields = (
        "name",
        "email",
        "phone",
        "topic",
        "mode",
        "channel",
        "preferred_datetime",
        "message",
        "consent",
        "created_at",
    )

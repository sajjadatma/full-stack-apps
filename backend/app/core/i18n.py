from collections.abc import Mapping
from contextvars import ContextVar
from typing import Final

DEFAULT_LOCALE: Final[str] = "en"
SUPPORTED_LOCALES: Final[tuple[str, ...]] = ("en", "fa")

_current_locale: ContextVar[str] = ContextVar("current_locale", default=DEFAULT_LOCALE)

MESSAGES: Mapping[str, Mapping[str, str]] = {
    "en": {
        "could_not_validate_credentials": "Could not validate credentials",
        "user_not_found": "User not found",
        "inactive_user": "Inactive user",
        "not_enough_privileges": "The user doesn't have enough privileges",
        "incorrect_email_or_password": "Incorrect email or password",
        "invalid_token": "Invalid token",
        "user_with_username_not_exist": "The user with this username does not exist in the system.",
        "item_not_found": "Item not found",
        "not_enough_permissions": "Not enough permissions",
        "user_with_email_exists_period": "The user with this email already exists in the system.",
        "user_with_email_exists": "The user with this email already exists in the system",
        "user_with_email_already_exists": "User with this email already exists",
        "incorrect_password": "Incorrect password",
        "new_password_same_as_current": "New password cannot be the same as the current one",
        "superuser_cannot_delete_self": "Super users are not allowed to delete themselves",
        "user_with_id_not_exist": "The user with this id does not exist in the system",
        "password_updated_successfully": "Password updated successfully",
        "password_recovery_sent": "If that email is registered, we sent a password recovery link",
        "user_deleted_successfully": "User deleted successfully",
        "user_created_successfully": "User created successfully",
        "user_updated_successfully": "User updated successfully",
        "item_created_successfully": "Item created successfully",
        "item_updated_successfully": "Item updated successfully",
        "item_deleted_successfully": "Item deleted successfully",
        "test_email_sent": "Test email sent",
        "role_not_found": "Role not found",
        "role_name_exists": "A role with this name already exists",
        "role_slug_exists": "A role with this slug already exists",
        "system_role_immutable": "System roles cannot be modified or deleted",
        "role_in_use": "This role is assigned to one or more users and cannot be deleted",
        "role_deleted_successfully": "Role deleted successfully",
        "cannot_change_own_role": "You cannot change your own role",
        "last_superuser": "At least one active superuser must remain",
        "cannot_assign_superuser_role": "You cannot assign the superuser role",
        "cannot_grant_unowned_permissions": "You cannot grant permissions you do not have",
        "unknown_permissions": "Unknown permission(s): {permissions}",
        "duplicate_permissions": "A permission was selected more than once",
        "email_test_subject": "{project_name} - Test email",
        "email_reset_password_subject": "{project_name} - Password recovery for user {email}",
        "email_new_account_subject": "{project_name} - New account for user {username}",
    },
    "fa": {
        "could_not_validate_credentials": "اعتبارنامه‌ها قابل تأیید نیستند",
        "user_not_found": "کاربر یافت نشد",
        "inactive_user": "کاربر غیرفعال است",
        "not_enough_privileges": "کاربر دسترسی کافی ندارد",
        "incorrect_email_or_password": "ایمیل یا رمز عبور نادرست است",
        "invalid_token": "توکن نامعتبر است",
        "user_with_username_not_exist": "کاربری با این نام کاربری در سیستم وجود ندارد.",
        "item_not_found": "آیتم یافت نشد",
        "not_enough_permissions": "دسترسی کافی وجود ندارد",
        "user_with_email_exists_period": "کاربری با این ایمیل از قبل در سیستم وجود دارد.",
        "user_with_email_exists": "کاربری با این ایمیل از قبل در سیستم وجود دارد",
        "user_with_email_already_exists": "کاربری با این ایمیل از قبل وجود دارد",
        "incorrect_password": "رمز عبور نادرست است",
        "new_password_same_as_current": "رمز عبور جدید نمی‌تواند با رمز عبور فعلی یکسان باشد",
        "superuser_cannot_delete_self": "کاربران ارشد مجاز به حذف خود نیستند",
        "user_with_id_not_exist": "کاربری با این شناسه در سیستم وجود ندارد",
        "password_updated_successfully": "رمز عبور با موفقیت به‌روزرسانی شد",
        "password_recovery_sent": "اگر این ایمیل ثبت شده باشد، پیوند بازیابی رمز عبور را ارسال کرده‌ایم",
        "user_deleted_successfully": "کاربر با موفقیت حذف شد",
        "user_created_successfully": "کاربر با موفقیت ایجاد شد",
        "user_updated_successfully": "کاربر با موفقیت به‌روزرسانی شد",
        "item_created_successfully": "آیتم با موفقیت ایجاد شد",
        "item_updated_successfully": "آیتم با موفقیت به‌روزرسانی شد",
        "item_deleted_successfully": "آیتم با موفقیت حذف شد",
        "test_email_sent": "ایمیل آزمایشی ارسال شد",
        "role_not_found": "نقش یافت نشد",
        "role_name_exists": "نقشی با این نام از قبل وجود دارد",
        "role_slug_exists": "نقشی با این شناسه از قبل وجود دارد",
        "system_role_immutable": "نقش‌های سیستمی قابل ویرایش یا حذف نیستند",
        "role_in_use": "این نقش به یک یا چند کاربر اختصاص یافته و قابل حذف نیست",
        "role_deleted_successfully": "نقش با موفقیت حذف شد",
        "cannot_change_own_role": "شما نمی‌توانید نقش خودتان را تغییر دهید",
        "last_superuser": "حداقل یک کاربر ارشد فعال باید باقی بماند",
        "cannot_assign_superuser_role": "شما نمی‌توانید نقش کاربر ارشد را اختصاص دهید",
        "cannot_grant_unowned_permissions": "شما نمی‌توانید دسترسی‌هایی را که ندارید اعطا کنید",
        "unknown_permissions": "دسترسی‌های ناشناخته: {permissions}",
        "duplicate_permissions": "یک دسترسی بیش از یک بار انتخاب شده است",
        "email_test_subject": "{project_name} - ایمیل آزمایشی",
        "email_reset_password_subject": "{project_name} - بازیابی رمز عبور برای کاربر {email}",
        "email_new_account_subject": "{project_name} - حساب کاربری جدید برای {username}",
    },
}


def normalize_locale(locale: str | None) -> str:
    """Return a supported locale code, falling back to the default."""
    if not locale:
        return DEFAULT_LOCALE
    base = locale.split("-")[0].lower()
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE


def preferred_locale(accept_language: str | None) -> str:
    """Pick the best supported locale from an Accept-Language header."""
    if not accept_language:
        return DEFAULT_LOCALE
    for part in accept_language.split(","):
        base = part.split(";")[0].strip().split("-")[0].lower()
        if base in SUPPORTED_LOCALES:
            return base
    return DEFAULT_LOCALE


def set_locale(locale: str | None) -> None:
    _current_locale.set(normalize_locale(locale))


def get_locale() -> str:
    return _current_locale.get()


def t(key: str, locale: str | None = None, **kwargs: str) -> str:
    """Translate a message key, formatting any placeholders."""
    language = normalize_locale(locale) if locale else get_locale()
    catalog = MESSAGES.get(language, MESSAGES[DEFAULT_LOCALE])
    message = catalog.get(key) or MESSAGES[DEFAULT_LOCALE].get(key, key)
    if kwargs:
        return message.format(**kwargs)
    return message

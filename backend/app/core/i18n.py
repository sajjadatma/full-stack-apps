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
        "category_not_found": "Category not found",
        "category_name_or_slug_exists": "A category with this name or slug already exists",
        "category_in_use": "This category is assigned to one or more products and cannot be deleted",
        "category_deleted_successfully": "Category deleted successfully",
        "brand_not_found": "Brand not found",
        "brand_name_or_slug_exists": "A brand with this name or slug already exists",
        "brand_in_use": "This brand is assigned to one or more products and cannot be deleted",
        "brand_deleted_successfully": "Brand deleted successfully",
        "product_not_found": "Product not found",
        "product_category_not_found": "Product category not found or inactive",
        "product_brand_not_found": "Product brand not found or inactive",
        "product_sku_or_slug_exists": "A product with this SKU or slug already exists",
        "product_deleted_successfully": "Product deleted successfully",
        "product_image_not_found": "Product image not found",
        "product_image_upload_failed": "Could not save the product image",
        "product_image_delete_failed": "Could not delete the product image",
        "product_image_storage_delete_failed": "Image storage is unavailable; the image was restored",
        "product_image_order_invalid": "Reorder must include every product image exactly once",
        "product_image_deleted_successfully": "Product image deleted successfully",
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
        "category_not_found": "دسته‌بندی یافت نشد",
        "category_name_or_slug_exists": "دسته‌بندی با این نام یا شناسه از قبل وجود دارد",
        "category_in_use": "این دسته‌بندی به یک یا چند محصول اختصاص یافته و قابل حذف نیست",
        "category_deleted_successfully": "دسته‌بندی با موفقیت حذف شد",
        "brand_not_found": "برند یافت نشد",
        "brand_name_or_slug_exists": "برندی با این نام یا شناسه از قبل وجود دارد",
        "brand_in_use": "این برند به یک یا چند محصول اختصاص یافته و قابل حذف نیست",
        "brand_deleted_successfully": "برند با موفقیت حذف شد",
        "product_not_found": "محصول یافت نشد",
        "product_category_not_found": "دسته‌بندی محصول یافت نشد یا غیرفعال است",
        "product_brand_not_found": "برند محصول یافت نشد یا غیرفعال است",
        "product_sku_or_slug_exists": "محصولی با این شناسه یا نامک از قبل وجود دارد",
        "product_deleted_successfully": "محصول با موفقیت حذف شد",
        "product_image_not_found": "تصویر محصول یافت نشد",
        "product_image_upload_failed": "ذخیره تصویر محصول ناموفق بود",
        "product_image_delete_failed": "حذف تصویر محصول ناموفق بود",
        "product_image_storage_delete_failed": "ذخیره‌سازی تصویر در دسترس نیست؛ تصویر بازیابی شد",
        "product_image_order_invalid": "ترتیب باید همه تصاویر محصول را دقیقاً یک‌بار داشته باشد",
        "product_image_deleted_successfully": "تصویر محصول با موفقیت حذف شد",
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

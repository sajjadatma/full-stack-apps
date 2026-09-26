import type { TFunction } from "i18next"

import type { RolePublic, RoleSummary } from "@/client"

export function roleLabel(
  role: RolePublic | RoleSummary,
  t: TFunction,
): string {
  if (role.is_system) {
    return t(`systemRoles.${role.slug}`, { defaultValue: role.name })
  }
  return role.name
}

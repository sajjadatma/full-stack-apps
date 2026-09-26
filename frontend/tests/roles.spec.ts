import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.describe("Role administration", () => {
  test("lists protected system roles and creates a custom role", async ({
    page,
  }) => {
    await page.goto("/roles")
    await page.getByTestId("language-button").click()
    await page.getByTestId("language-en").click()

    await expect(
      page.getByRole("heading", { name: "Roles & Permissions" }),
    ).toBeVisible()
    await expect(page.getByText("Superuser", { exact: true })).toBeVisible()
    await expect(
      page.getByText("Read-only", { exact: true }).first(),
    ).toBeVisible()

    await page.getByRole("button", { name: "Add Role" }).click()
    await page.getByLabel("Name").fill(`QA ${Date.now()}`)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Role created successfully")).toBeVisible()
  })

  test.describe("for ordinary users", () => {
    test.use({ storageState: { cookies: [], origins: [] } })

    test("redirects away from role administration", async ({ page }) => {
      const email = randomEmail()
      const password = randomPassword()
      await createUser({ email, password })
      await logInUser(page, email, password)

      await page.goto("/roles")
      await expect(page).not.toHaveURL(/\/roles/)
      await expect(
        page.getByRole("heading", { name: "Roles & Permissions" }),
      ).not.toBeVisible()
    })
  })

  test("permission UI is localized in Farsi", async ({ page }) => {
    await page.goto("/roles")
    await page.getByTestId("language-button").click()
    await page.getByTestId("language-en").click()
    await expect(page.getByTestId("language-en")).toBeHidden()

    await page.getByTestId("language-button").click()
    await page.getByTestId("language-fa").click()

    await expect(page.locator("html")).toHaveAttribute("dir", "rtl")
    await expect(
      page.getByRole("heading", { name: "نقش‌ها و دسترسی‌ها" }),
    ).toBeVisible()

    // Restore English and wait for it to persist so later tests are unaffected.
    await expect(page.getByTestId("language-fa")).toBeHidden()
    await Promise.all([
      page.waitForResponse(
        (response) =>
          response.url().includes("/users/me") &&
          response.request().method() === "PATCH",
      ),
      (async () => {
        await page.getByTestId("language-button").click()
        await page.getByTestId("language-en").click()
      })(),
    ])
    await expect(page.locator("html")).toHaveAttribute("lang", "en")
  })
})

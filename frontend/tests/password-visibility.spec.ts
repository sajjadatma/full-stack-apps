import { expect, type Locator, test } from "@playwright/test"
import { randomEmail, randomPassword } from "./utils/random"

async function expectToggleWorks(input: Locator, toggle: Locator) {
  await expect(input).toHaveAttribute("type", "password")
  await toggle.click()
  await expect(input).toHaveAttribute("type", "text")
  await toggle.click()
  await expect(input).toHaveAttribute("type", "password")
}

test.describe("Password visibility toggles", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("login password can be revealed and hidden", async ({ page }) => {
    await page.goto("/login")
    await expectToggleWorks(
      page.getByTestId("password-input"),
      page.getByTestId("password-toggle"),
    )
  })

  test("signup password fields can be revealed and hidden", async ({
    page,
  }) => {
    await page.goto("/signup")
    const toggles = page.getByTestId("password-toggle")
    await expect(toggles).toHaveCount(2)
    await expectToggleWorks(page.getByTestId("password-input"), toggles.first())
    await expectToggleWorks(
      page.getByTestId("confirm-password-input"),
      toggles.nth(1),
    )
  })

  test("admin add and edit user password fields can be revealed and hidden", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.getByTestId("email-input").fill("admin@example.com")
    await page.getByTestId("password-input").fill("changethis")
    await page.getByRole("button", { name: "Log In" }).click()
    await page.waitForURL("/")

    await page.goto("/admin")
    await page.getByRole("button", { name: "Add User" }).click()

    const dialog = page.getByRole("dialog")
    const addToggles = dialog.getByTestId("password-toggle")
    await expect(addToggles).toHaveCount(2)
    await expectToggleWorks(
      dialog.getByPlaceholder("Password").first(),
      addToggles.first(),
    )

    const email = randomEmail()
    const password = randomPassword()
    await dialog.getByPlaceholder("Email").fill(email)
    await dialog.getByPlaceholder("Password").first().fill(password)
    await dialog.getByPlaceholder("Password").last().fill(password)
    await dialog.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("User created successfully")).toBeVisible()

    const userRow = page.getByRole("row").filter({ hasText: email })
    await userRow.getByRole("button").click()
    await page.getByRole("menuitem", { name: "Edit User" }).click()

    const editDialog = page.getByRole("dialog")
    const editToggles = editDialog.getByTestId("password-toggle")
    await expect(editToggles).toHaveCount(2)
    await expectToggleWorks(
      editDialog.getByPlaceholder("Password").first(),
      editToggles.first(),
    )
    await expectToggleWorks(
      editDialog.getByPlaceholder("Password").last(),
      editToggles.nth(1),
    )
  })

  test("change password fields can be revealed and hidden", async ({
    page,
  }) => {
    await page.goto("/login")
    await page.getByTestId("email-input").fill("admin@example.com")
    await page.getByTestId("password-input").fill("changethis")
    await page.getByRole("button", { name: "Log In" }).click()
    await page.waitForURL("/")

    await page.goto("/settings")
    await page.getByRole("tab", { name: "Password" }).click()

    const toggles = page.getByTestId("password-toggle")
    await expect(toggles).toHaveCount(3)
    await expectToggleWorks(
      page.getByTestId("current-password-input"),
      toggles.first(),
    )
    await expectToggleWorks(
      page.getByTestId("new-password-input"),
      toggles.nth(1),
    )
    await expectToggleWorks(
      page.getByTestId("confirm-password-input"),
      toggles.nth(2),
    )
  })
})

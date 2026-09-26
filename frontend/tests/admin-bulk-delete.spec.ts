import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"

test.describe("Admin bulk delete", () => {
  test("deletes multiple selected users", async ({ page }) => {
    const first = await createUser({
      email: randomEmail(),
      password: randomPassword(),
    })
    const second = await createUser({
      email: randomEmail(),
      password: randomPassword(),
    })

    await page.goto("/admin")

    await expect(page.getByTestId("select-all-users")).toBeVisible()

    await page.getByTestId(`select-user-${first.id}`).check()
    await page.getByTestId(`select-user-${second.id}`).check()

    await expect(page.getByTestId("selected-users-count")).toHaveText(
      "2 selected",
    )

    await page.getByTestId("delete-selected-users").click()
    await page.getByTestId("confirm-delete-selected-users").click()

    await expect(page.getByText("2 users deleted successfully")).toBeVisible()
    await expect(
      page.getByRole("row").filter({ hasText: first.email }),
    ).not.toBeVisible()
    await expect(
      page.getByRole("row").filter({ hasText: second.email }),
    ).not.toBeVisible()
  })

  test("cannot select the current user", async ({ page }) => {
    await createUser({ email: randomEmail(), password: randomPassword() })
    await page.goto("/admin")
    await expect(page.getByTestId("select-all-users")).toBeVisible()

    const lastPage = page.getByRole("button", { name: "Go to last page" })
    if (await lastPage.isVisible()) {
      await lastPage.click()
    }

    const currentRow = page
      .getByRole("row")
      .filter({ hasText: "admin@example.com" })
    await expect(currentRow).toBeVisible()
    await expect(currentRow.getByRole("checkbox")).toBeDisabled()
  })

  test("clears the selection", async ({ page }) => {
    const user = await createUser({
      email: randomEmail(),
      password: randomPassword(),
    })
    await page.goto("/admin")

    await page.getByTestId(`select-user-${user.id}`).check()
    await expect(page.getByTestId("selected-users-count")).toHaveText(
      "1 selected",
    )

    await page.getByRole("button", { name: "Clear selection" }).click()
    await expect(page.getByTestId("selected-users-count")).not.toBeVisible()
  })
})

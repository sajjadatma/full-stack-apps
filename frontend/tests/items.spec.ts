import { expect, test } from "@playwright/test"

test("authenticated visits to the retired Items route go to the product catalog", async ({
  page,
}) => {
  await page.goto("/items")

  await expect(page).toHaveURL(/\/products$/)
  await expect(
    page.getByRole("heading", { name: "Product catalog" }),
  ).toBeVisible()
})

test.describe("unauthenticated visits to the retired Items route", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("still require login before redirecting to the product catalog", async ({
    page,
  }) => {
    await page.goto("/items")

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByTestId("email-input")).toBeVisible()
  })
})

import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("switches between English and Farsi with RTL layout", async ({ page }) => {
  await page.goto("/login")

  await expect(page.locator("html")).toHaveAttribute("lang", "en")
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr")
  await expect(
    page.getByRole("heading", { name: "Login to your account" }),
  ).toBeVisible()

  await page.getByTestId("language-button").click()
  await page.getByTestId("language-fa").click()

  await expect(page.locator("html")).toHaveAttribute("lang", "fa")
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl")
  await expect(
    page.getByRole("heading", { name: "ورود به حساب کاربری" }),
  ).toBeVisible()
  await expect(page.locator("html")).toHaveCSS("font-family", /Vazirmatn/)

  // Wait for the menu to finish closing before reopening it.
  await expect(page.getByTestId("language-fa")).toBeHidden()
  await page.getByTestId("language-button").click()
  await page.getByTestId("language-en").click()

  await expect(page.locator("html")).toHaveAttribute("lang", "en")
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr")
})

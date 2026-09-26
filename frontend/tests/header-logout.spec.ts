import { expect, type Page, test } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

const headerLogout = (page: Page) =>
  page.locator("header").getByTestId("logout-button")

const accessToken = (page: Page) =>
  page.evaluate(() => localStorage.getItem("access_token"))

const tabToHeaderLogout = async (page: Page) => {
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur()
    }
  })

  for (let index = 0; index < 25; index += 1) {
    await page.keyboard.press("Tab")
    const focusedTestId = await page.evaluate(
      () =>
        (document.activeElement as HTMLElement | null)?.dataset?.testid ?? null,
    )
    if (focusedTestId === "logout-button") {
      return true
    }
  }

  return false
}

test.describe("Header log out", () => {
  test.beforeEach(async ({ page }) => {
    await logInUser(page, firstSuperuser, firstSuperuserPassword)
  })

  test("Header log out is visible on every authenticated page", async ({
    page,
  }) => {
    await expect(headerLogout(page)).toBeVisible()
    await expect(headerLogout(page)).toHaveAccessibleName("Log Out")

    for (const path of ["/items", "/settings", "/admin"]) {
      await page.goto(path)
      await expect(headerLogout(page)).toBeVisible()
    }
  })

  test("Header log out works at a 375px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto("/")

    await expect(headerLogout(page)).toBeVisible()
    await headerLogout(page).click()
    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
  })

  test("Header log out is a button and does not collide with the sidebar item", async ({
    page,
  }) => {
    await expect(page.getByTestId("logout-button")).toHaveRole("button")

    await page.getByTestId("user-menu").click()
    await expect(page.getByRole("menuitem", { name: "Log out" })).toHaveCount(1)
  })

  test("Header log out ends the session without a confirmation dialog", async ({
    page,
  }) => {
    await headerLogout(page).click()

    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
    await expect(page.getByRole("dialog")).not.toBeVisible()
    expect(await accessToken(page)).toBeNull()
  })

  test("Protected routes stay guarded after header log out", async ({
    page,
  }) => {
    await headerLogout(page).click()
    await page.waitForURL("/login")

    await page.goto("/settings")
    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
  })

  test("Browser back after header log out does not render authenticated content", async ({
    page,
  }) => {
    await headerLogout(page).click()
    await page.waitForURL("/login")

    await page.goBack()
    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
    await expect(
      page.getByText("Welcome back, nice to see you again!"),
    ).not.toBeVisible()
  })

  test("Header log out is keyboard operable with Enter", async ({ page }) => {
    expect(await tabToHeaderLogout(page)).toBe(true)
    await expect(page.getByTestId("logout-button")).toBeFocused()
    expect(
      await page.evaluate(
        () => document.activeElement?.matches(":focus-visible") ?? false,
      ),
    ).toBe(true)

    await page.keyboard.press("Enter")

    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
    expect(await accessToken(page)).toBeNull()
  })

  test("Header log out is keyboard operable with Space", async ({ page }) => {
    expect(await tabToHeaderLogout(page)).toBe(true)
    await expect(page.getByTestId("logout-button")).toBeFocused()

    await page.keyboard.press("Space")

    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
    expect(await accessToken(page)).toBeNull()
  })

  test("Rapid double click on header log out is idempotent", async ({
    page,
  }) => {
    await page.getByTestId("logout-button").evaluate((element) => {
      const button = element as HTMLButtonElement
      button.click()
      button.click()
    })

    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
    await expect(page.locator("[data-sonner-toast]")).toHaveCount(0)
    expect(await accessToken(page)).toBeNull()
  })

  test("Header log out renders and works while the profile request fails", async ({
    page,
  }) => {
    await page.route("**/api/v1/users/me", (route) => route.abort())

    await page.goto("/")

    await expect(headerLogout(page)).toBeVisible()
    await expect(page.getByTestId("user-menu")).not.toBeVisible()

    await headerLogout(page).click()

    await page.waitForURL("/login")
    await expect(page).toHaveURL("/login")
    expect(await accessToken(page)).toBeNull()
  })
})

import { expect, test } from "@playwright/test"

const apiPath = (suffix: string) => `**/api/v1/${suffix}`

test("TileVision dashboard renders aggregate metrics and relevant shortcuts", async ({
  page,
}) => {
  await page.route(apiPath("dashboard/summary/"), (route) =>
    route.fulfill({
      status: 200,
      json: {
        products: {
          total_products: 48,
          active_products: 42,
          low_stock_products: 6,
        },
        generations: {
          total: 31,
          pending: 2,
          processing: 1,
          completed: 25,
          failed: 3,
        },
      },
    }),
  )
  await page.goto("/")

  await expect(page.getByText("Total products")).toBeVisible()
  await expect(page.getByTestId("metric-total-products")).toHaveText("48")
  await expect(page.getByTestId("metric-active-products")).toHaveText("42")
  await expect(page.getByTestId("metric-low-stock-products")).toHaveText("6")
  await expect(page.getByTestId("metric-generations-total")).toHaveText("31")
  await expect(page.getByTestId("metric-generations-completed")).toHaveText(
    "25",
  )
  await expect(
    page.getByRole("link", { name: /Product Management/ }),
  ).toHaveAttribute("href", "/products")
  await expect(
    page.getByRole("link", { name: "Visualizer Preview products" }),
  ).toHaveAttribute("href", "/visualizer")
  await expect(
    page.getByRole("link", { name: "Generation history Review" }),
  ).toHaveAttribute("href", "/generations")
})

test("dashboard hides unauthorized metric families and shortcuts", async ({
  page,
}) => {
  await page.route(apiPath("users/me"), (route) =>
    route.fulfill({
      status: 200,
      json: {
        id: "d3a3be63-c33d-4b6b-b165-39e1e8378916",
        email: "customer@example.com",
        is_active: true,
        is_superuser: false,
        full_name: "Tile Customer",
        locale: "en",
        role: null,
        permissions: ["generations.read_own"],
      },
    }),
  )
  await page.route(apiPath("dashboard/summary/"), (route) =>
    route.fulfill({
      status: 200,
      json: {
        products: null,
        generations: {
          total: 4,
          pending: 0,
          processing: 0,
          completed: 3,
          failed: 1,
        },
      },
    }),
  )
  await page.goto("/")

  await expect(page.getByTestId("metric-generations-total")).toHaveText("4")
  await expect(page.getByTestId("metric-total-products")).toHaveCount(0)
  await expect(
    page.getByRole("link", { name: /Product Management/ }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("link", { name: "Visualizer Preview products" }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("link", { name: "Generation history Review" }),
  ).toBeVisible()
})

test("dashboard keeps shortcuts available and shows an error when metrics fail", async ({
  page,
}) => {
  await page.route(apiPath("dashboard/summary/"), (route) =>
    route.fulfill({ status: 500, json: { detail: "temporary failure" } }),
  )
  await page.goto("/")

  await expect(page.getByRole("alert")).toContainText(
    "Could not load dashboard metrics",
  )
  await expect(
    page.getByRole("link", { name: /Product Management/ }),
  ).toBeVisible()
})

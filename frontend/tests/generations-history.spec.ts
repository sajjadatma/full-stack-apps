import { randomUUID } from "node:crypto"
import { expect, test } from "@playwright/test"

const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/qVQAAAAASUVORK5CYII=",
  "base64",
)

function generation(id: string, status = "COMPLETED") {
  return {
    id,
    project_id: randomUUID(),
    selected_product_id: randomUUID(),
    target_surface: "FLOOR",
    status,
    output_image_url:
      status === "COMPLETED" ? `/api/v1/generations/${id}/result` : null,
    output_image_content_type: status === "COMPLETED" ? "image/png" : null,
    error_code: status === "FAILED" ? "provider_error" : null,
    error_message: status === "FAILED" ? "Safe failure details" : null,
    retry_count: 0,
    created_at: "2026-09-29T12:00:00Z",
    selected_product: {
      id: randomUUID(),
      name: "History tile",
      sku: "HISTORY-1",
      width_mm: 300,
      height_mm: 300,
      thickness_mm: 8,
      finish: "matte",
      material: "porcelain",
      color_family: "grey",
      is_active: false,
      primary_image_id: randomUUID(),
    },
  }
}

async function mockHistory(
  page: import("@playwright/test").Page,
  rows: ReturnType<typeof generation>[],
  count = rows.length,
) {
  await page.route("**/api/v1/generations/**", async (route) => {
    const url = new URL(route.request().url())
    if (
      route.request().method() === "POST" &&
      url.pathname.endsWith("/retry")
    ) {
      const retry = generation(randomUUID(), "PENDING")
      await route.fulfill({ status: 202, json: retry })
      return
    }
    if (
      url.pathname.endsWith("/product-image") ||
      url.pathname.endsWith("/result")
    ) {
      await route.fulfill({ status: 200, contentType: "image/png", body: png })
      return
    }
    if (url.pathname.endsWith("/generations/")) {
      const skip = Number(url.searchParams.get("skip") ?? "0")
      await route.fulfill({
        status: 200,
        json: { data: rows.slice(skip, skip + 20), count },
      })
      return
    }
    const id = url.pathname.split("/").at(-1)
    const row =
      rows.find((item) => item.id === id) ?? generation(id ?? "", "FAILED")
    await route.fulfill({ status: 200, json: row })
  })
  await page.route("**/api/v1/visualization-projects/*/source-image", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: png }),
  )
}

test("history lists generations, supports pagination, and shows generation-scoped images", async ({
  page,
}) => {
  const rows = Array.from({ length: 21 }, (_, index) =>
    generation(`history-${index}`),
  )
  await mockHistory(page, rows)
  const scopedProductImage = page.waitForRequest((request) =>
    request.url().endsWith("/product-image"),
  )
  await page.goto("/generations")
  await expect(page.getByTestId("generation-history-page")).toBeVisible()
  await expect(page.getByText("History tile").first()).toBeVisible()
  await expect(
    page.getByRole("img", { name: "History tile" }).first(),
  ).toHaveAttribute("src", /^blob:/)
  await scopedProductImage
  await expect(page.getByText("Floor").first()).toBeVisible()
  await expect(
    page.getByRole("navigation", { name: "Generation history pages" }),
  ).toContainText("Page 1 of 2")
  await page.getByRole("button", { name: "Next" }).click()
  await expect(
    page.getByRole("navigation", { name: "Generation history pages" }),
  ).toContainText("Page 2 of 2")
  await expect(
    page.getByRole("link", { name: /History tile/ }),
  ).toHaveAttribute("href", /generations\/history-20/)
})

test("empty history state is informative", async ({ page }) => {
  await mockHistory(page, [], 0)
  await page.goto("/generations")
  await expect(page.getByText("No visualizations yet")).toBeVisible()
})

test("history API errors show a recoverable error state", async ({ page }) => {
  await page.route("**/*", (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === "/api/v1/generations/") {
      return route.fulfill({ status: 500, json: { detail: "failed" } })
    }
    return route.continue()
  })
  await page.goto("/generations")
  await expect(page.getByRole("alert")).toContainText("Could not load history")
})

test("detail compares the generation and retries a failed job to a new attempt", async ({
  page,
}) => {
  const id = randomUUID()
  const failed = generation(id, "FAILED")
  await mockHistory(page, [failed])
  await page.goto(`/generations/${id}`)
  await expect(page.getByTestId("generation-detail-page")).toBeVisible()
  await expect(page.getByText("Safe failure details")).toBeVisible()
  await expect(page.getByText("Generation failed")).toBeVisible()
  await expect(page.getByText("History tile")).toBeVisible()
  await expect(page.getByText("Floor")).toBeVisible()
  await page.getByTestId("retry-button").click()
  await expect(page).not.toHaveURL(new RegExp(id))
  await expect(page.getByTestId("generation-detail-page")).toBeVisible()
})

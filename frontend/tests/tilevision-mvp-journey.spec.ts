import { randomUUID } from "node:crypto"
import { expect, test } from "@playwright/test"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser, signUpNewUser } from "./utils/user"

const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/qVQAAAAASUVORK5CYII=",
  "base64",
)
const JOB_ID = "00000000-0000-4000-8000-000000000023"

test("admin product becomes a customer's completed visualizer history item", async ({
  page,
  browser,
}) => {
  const suffix = randomUUID().slice(0, 8)
  const productName = `Journey Tile ${suffix}`
  const sku = `JOURNEY-${suffix}`
  const categoryName = `Journey Category ${suffix}`
  const slug = `journey-tile-${suffix}`
  const apiBase = process.env.VITE_API_URL || "http://localhost:8000"
  await page.goto("/products")
  const adminToken = await page.evaluate(() =>
    localStorage.getItem("access_token"),
  )
  expect(adminToken).toBeTruthy()

  const categoryResponse = await page.request.post(
    `${apiBase}/api/v1/categories/`,
    {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: { name: categoryName, slug: `journey-category-${suffix}` },
    },
  )
  expect(categoryResponse.ok()).toBeTruthy()
  const category = await categoryResponse.json()

  await page.reload()
  await page.getByRole("button", { name: "Add product" }).click()
  const productDialog = page.getByRole("dialog", { name: "Add product" })
  await productDialog.getByLabel("Product name").fill(productName)
  await productDialog.getByLabel("SKU").fill(sku)
  await productDialog.getByLabel("Slug").fill(slug)
  await productDialog
    .getByLabel("Category")
    .selectOption({ label: categoryName })
  await productDialog.getByRole("checkbox", { name: "Floor" }).check()
  await productDialog.locator('input[type="file"]').setInputFiles({
    name: "journey-tile.png",
    mimeType: "image/png",
    buffer: PNG,
  })
  await expect(
    productDialog.getByRole("list", { name: "Upload queue" }),
  ).toBeVisible()
  await productDialog.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Product created successfully")).toBeVisible()
  await expect(productDialog).not.toBeVisible()

  const productResponse = await page.request.get(
    `${apiBase}/api/v1/products/?q=${sku}`,
    { headers: { Authorization: `Bearer ${adminToken}` } },
  )
  expect(productResponse.ok()).toBeTruthy()
  const listedProducts = await productResponse.json()
  const product = listedProducts.data.find(
    (item: { sku: string }) => item.sku === sku,
  )
  expect(product).toBeTruthy()
  expect(product.suitable_surfaces).toEqual(["FLOOR"])
  expect(product.images).toHaveLength(1)
  expect(product.images[0].is_primary).toBe(true)

  const customerContext = await browser.newContext({
    storageState: { cookies: [], origins: [] },
  })
  const customerPage = await customerContext.newPage()
  const customerEmail = randomEmail()
  const customerPassword = randomPassword()
  await signUpNewUser(
    customerPage,
    `Journey Customer ${suffix}`,
    customerEmail,
    customerPassword,
  )
  await logInUser(customerPage, customerEmail, customerPassword)

  const actualProductId = product.id as string
  const requestBody: {
    visualization_project_id?: string
    selected_product_id?: string
    target_surface?: string
  } = {}
  let pollCount = 0
  let historyRows: Record<string, unknown>[] = []
  let createCount = 0
  const job = (status: "PENDING" | "PROCESSING" | "COMPLETED") => ({
    id: JOB_ID,
    project_id: requestBody.visualization_project_id,
    selected_product_id: requestBody.selected_product_id,
    target_surface: requestBody.target_surface,
    status,
    provider: "openai",
    provider_model: "gpt-image-1",
    provider_params: null,
    prompt_version: "tilevision-v1",
    output_image_url:
      status === "COMPLETED" ? `/api/v1/generations/${JOB_ID}/result` : null,
    output_image_content_type: status === "COMPLETED" ? "image/png" : null,
    output_image_width_px: status === "COMPLETED" ? 1 : null,
    output_image_height_px: status === "COMPLETED" ? 1 : null,
    error_code: null,
    error_message: null,
    retry_count: 0,
    retry_of_job_id: null,
    selected_product: {
      id: actualProductId,
      name: productName,
      sku,
      width_mm: 300,
      height_mm: 300,
      thickness_mm: null,
      finish: null,
      material: null,
      color_family: null,
      is_active: true,
      primary_image_id: product.images[0].id,
    },
    created_at: "2026-09-30T12:00:00Z",
    updated_at: "2026-09-30T12:00:00Z",
    started_at: status === "PENDING" ? null : "2026-09-30T12:00:01Z",
    completed_at: status === "COMPLETED" ? "2026-09-30T12:00:02Z" : null,
  })

  await customerPage.route("**/api/v1/generations/**", async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === "/api/v1/generations/" && request.method() === "POST") {
      createCount += 1
      Object.assign(requestBody, request.postDataJSON())
      await route.fulfill({ status: 202, json: job("PENDING") })
      return
    }
    if (
      path === `/api/v1/generations/${JOB_ID}` &&
      request.method() === "GET"
    ) {
      const states = ["PROCESSING", "COMPLETED"] as const
      const state = states[Math.min(pollCount, states.length - 1)]
      pollCount += 1
      await route.fulfill({ status: 200, json: job(state) })
      return
    }
    if (
      path === `/api/v1/generations/${JOB_ID}/result` &&
      request.method() === "GET"
    ) {
      await route.fulfill({ status: 200, contentType: "image/png", body: PNG })
      return
    }
    if (
      path === `/api/v1/generations/${JOB_ID}/product-image` &&
      request.method() === "GET"
    ) {
      await route.fulfill({ status: 200, contentType: "image/png", body: PNG })
      return
    }
    if (path === "/api/v1/generations/" && request.method() === "GET") {
      await route.fulfill({
        status: 200,
        json: { data: historyRows, count: historyRows.length },
      })
      return
    }
    await route.continue()
  })

  try {
    await customerPage.goto("/visualizer")
    await expect(
      customerPage.getByTestId("visualizer-step-upload"),
    ).toBeVisible()
    await customerPage.getByTestId("room-photo-input").setInputFiles({
      name: "customer-room.png",
      mimeType: "image/png",
      buffer: PNG,
    })
    await customerPage.getByTestId("room-photo-continue").click()
    await expect(
      customerPage.getByTestId("visualizer-step-surface"),
    ).toBeVisible()
    await customerPage.getByTestId("surface-floor").click()
    await customerPage.getByTestId("surface-next").click()
    await expect(
      customerPage.getByTestId("visualizer-step-product"),
    ).toBeVisible()
    await customerPage.getByTestId("product-search").fill(sku)
    await expect(
      customerPage.getByTestId(`product-option-${actualProductId}`),
    ).toBeVisible()
    await customerPage.getByTestId(`product-option-${actualProductId}`).click()
    await customerPage.getByTestId("product-next").click()
    await expect(
      customerPage.getByTestId("visualizer-step-review"),
    ).toBeVisible()
    await expect(
      customerPage.getByRole("img", { name: "Room photo" }),
    ).toBeVisible()

    const projectId = new URL(customerPage.url()).searchParams.get("project")
    expect(projectId).toBeTruthy()
    await customerPage.getByTestId("generate-button").click()
    await expect(
      customerPage.getByTestId("generation-result-image"),
    ).toBeVisible({
      timeout: 15_000,
    })
    await expect
      .poll(() =>
        customerPage
          .getByTestId("generation-result-image")
          .evaluate((image: HTMLImageElement) => image.naturalWidth),
      )
      .toBeGreaterThan(0)
    await expect(
      customerPage.getByRole("img", { name: "Original room photo" }),
    ).toBeVisible()
    await expect(
      customerPage.getByRole("link", { name: "Download" }),
    ).toBeVisible()
    expect(createCount).toBe(1)
    expect(requestBody).toEqual({
      visualization_project_id: projectId,
      selected_product_id: actualProductId,
      target_surface: "FLOOR",
    })

    historyRows = [job("COMPLETED")]
    await customerPage.goto("/generations")
    await expect(
      customerPage.getByTestId("generation-history-page"),
    ).toBeVisible()
    const historyItem = customerPage.getByRole("link", {
      name: new RegExp(productName),
    })
    await expect(historyItem).toBeVisible()
    await historyItem.click()
    await expect(customerPage).toHaveURL(new RegExp(`/generations/${JOB_ID}$`))
    await expect(
      customerPage.getByTestId("generation-detail-page"),
    ).toBeVisible()
    await expect(
      customerPage.getByTestId("generation-result-image"),
    ).toBeVisible()
  } finally {
    await customerContext.close()
    await page.request.delete(`${apiBase}/api/v1/products/${actualProductId}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    })
    await page.request.delete(`${apiBase}/api/v1/categories/${category.id}`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    })
  }
})

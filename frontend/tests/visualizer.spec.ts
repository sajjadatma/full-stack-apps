import { randomUUID } from "node:crypto"
import { expect, type Page, test } from "@playwright/test"

const PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/qVQAAAAASUVORK5CYII="
const PNG_BUFFER = Buffer.from(PNG_BASE64, "base64")

type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"

type GenerationMock = {
  createdJobIds: string[]
  retriedJobIds: string[]
}

/**
 * Intercept the generation endpoints so the flow can reach a terminal state
 * without a configured AI provider. Upload, projects, and products stay real.
 */
async function mockGenerations(
  page: Page,
  options: {
    statusSequence: JobStatus[]
    retryStatusSequence?: JobStatus[]
  },
): Promise<GenerationMock> {
  const createdJobIds: string[] = []
  const retriedJobIds: string[] = []
  const statusByJob = new Map<string, number>()
  const generationParams = new Map<
    string,
    {
      visualization_project_id?: string
      selected_product_id?: string
      target_surface?: string
    }
  >()
  const firstJobId = randomUUID()
  const retryJobId = randomUUID()

  const jobBody = (
    id: string,
    status: JobStatus,
    body?: {
      visualization_project_id?: string
      selected_product_id?: string
      target_surface?: string
    },
  ) => ({
    id,
    project_id: body?.visualization_project_id ?? randomUUID(),
    selected_product_id: body?.selected_product_id ?? randomUUID(),
    target_surface: body?.target_surface ?? "FLOOR",
    status,
    provider: "fake-provider",
    provider_model: "fake-model",
    provider_params: null,
    prompt_version: "tilevision-v1",
    output_image_url:
      status === "COMPLETED" ? `/api/v1/generations/${id}/result` : null,
    output_image_content_type: status === "COMPLETED" ? "image/png" : null,
    output_image_width_px: status === "COMPLETED" ? 1 : null,
    output_image_height_px: status === "COMPLETED" ? 1 : null,
    error_code: status === "FAILED" ? "provider_error" : null,
    error_message: status === "FAILED" ? "The provider failed safely." : null,
    retry_count: 0,
    retry_of_job_id: null,
    selected_product: {
      id: body?.selected_product_id ?? randomUUID(),
      name: "History product",
      sku: "HISTORY-1",
      width_mm: 300,
      height_mm: 300,
      thickness_mm: null,
      finish: "matte",
      material: "porcelain",
      color_family: "grey",
      is_active: true,
      primary_image_id: randomUUID(),
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    started_at: null,
    completed_at: null,
  })

  await page.route(/\/api\/v1\/generations(\/.*)?$/, async (route) => {
    const request = route.request()
    const method = request.method()
    const path = new URL(request.url()).pathname

    if (method === "POST" && path.endsWith("/generations/")) {
      const id = firstJobId
      createdJobIds.push(id)
      const body = request.postDataJSON() as {
        visualization_project_id?: string
        selected_product_id?: string
        target_surface?: string
      }
      generationParams.set(id, body)
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify(jobBody(id, "PENDING", body)),
      })
      return
    }

    if (method === "POST" && path.endsWith("/retry")) {
      retriedJobIds.push(retryJobId)
      const sourceId = path.split("/").at(-2) ?? firstJobId
      generationParams.set(retryJobId, generationParams.get(sourceId) ?? {})
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify(jobBody(retryJobId, "PENDING")),
      })
      return
    }

    if (method === "GET" && path.endsWith("/result")) {
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        body: PNG_BUFFER,
      })
      return
    }

    if (method === "GET" && path.endsWith("/product-image")) {
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        body: PNG_BUFFER,
      })
      return
    }

    if (method === "GET") {
      const jobId = path.split("/").pop() ?? firstJobId
      const callIndex = statusByJob.get(jobId) ?? 0
      statusByJob.set(jobId, callIndex + 1)
      const sequence =
        jobId === retryJobId
          ? (options.retryStatusSequence ?? ["COMPLETED"])
          : options.statusSequence
      const status = sequence[Math.min(callIndex, sequence.length - 1)]
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          jobBody(jobId, status, generationParams.get(jobId)),
        ),
      })
      return
    }

    await route.continue()
  })

  return { createdJobIds, retriedJobIds }
}

async function createEligibleProduct(
  page: Page,
  token: string,
  apiBase: string,
  suffix: string,
) {
  const categoryResponse = await page.request.post(
    `${apiBase}/api/v1/categories/`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name: `Visualizer Category ${suffix}`,
        slug: `vis-cat-${suffix}`,
      },
    },
  )
  expect(categoryResponse.ok()).toBeTruthy()
  const category = await categoryResponse.json()

  const productResponse = await page.request.post(
    `${apiBase}/api/v1/products/`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name: `Visualizer Porcelain ${suffix}`,
        sku: `VIS-${suffix}`,
        slug: `visualizer-tile-${suffix}`,
        category_id: category.id,
        product_type: "floor_tile",
        material: "porcelain",
        finish: "matte",
        color_family: "grey",
        width_mm: 600,
        height_mm: 600,
        suitable_surfaces: ["FLOOR"],
        is_active: true,
      },
    },
  )
  expect(productResponse.ok()).toBeTruthy()
  const product = await productResponse.json()

  const imageResponse = await page.request.post(
    `${apiBase}/api/v1/products/${product.id}/images/`,
    {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: "tile.png",
          mimeType: "image/png",
          buffer: PNG_BUFFER,
        },
      },
    },
  )
  expect(imageResponse.ok()).toBeTruthy()

  return { category, product }
}

async function cleanup(
  page: Page,
  token: string,
  apiBase: string,
  categoryId: string,
  productId: string,
) {
  await page.request.delete(`${apiBase}/api/v1/products/${productId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  await page.request.delete(`${apiBase}/api/v1/categories/${categoryId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

async function uploadRoomPhoto(page: Page) {
  await page.getByTestId("room-photo-input").setInputFiles({
    name: "room.png",
    mimeType: "image/png",
    buffer: PNG_BUFFER,
  })
  await page.getByTestId("room-photo-continue").click()
  await expect(page.getByTestId("visualizer-step-surface")).toBeVisible()
}

async function selectProduct(page: Page, sku: string, productId: string) {
  await page.getByTestId("product-search").fill(sku)
  await expect(page.getByTestId(`product-option-${productId}`)).toBeVisible()
  await page.getByTestId(`product-option-${productId}`).click()
  await page.getByTestId("product-next").click()
  await expect(page.getByTestId("visualizer-step-review")).toBeVisible()
}

test("customer completes the visualizer flow to a generated result", async ({
  page,
}) => {
  const suffix = randomUUID().slice(0, 8)
  const apiBase = process.env.VITE_API_URL || "http://localhost:8000"
  await page.goto("/visualizer")
  await expect(page.getByTestId("visualizer-step-upload")).toBeVisible()
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()
  const { category, product } = await createEligibleProduct(
    page,
    token as string,
    apiBase,
    suffix,
  )
  const mock = await mockGenerations(page, {
    statusSequence: ["PROCESSING", "COMPLETED"],
  })

  await uploadRoomPhoto(page)
  await page.getByTestId("surface-floor").click()
  await page.getByTestId("surface-next").click()
  await expect(page.getByTestId("visualizer-step-product")).toBeVisible()
  await selectProduct(page, `VIS-${suffix}`, product.id)

  await page.getByTestId("generate-button").click()
  await expect(page.getByTestId("visualizer-step-result")).toBeVisible({
    timeout: 15_000,
  })
  await expect(page.getByTestId("generation-result-image")).toBeVisible()
  await expect(
    page.getByRole("img", { name: "Original room photo" }),
  ).toBeVisible()
  const selectedProductImage = page.getByRole("img", {
    name: "History product",
  })
  await expect(selectedProductImage).toBeVisible()
  await expect(selectedProductImage).toHaveAttribute("src", /^blob:/)
  await expect(page.getByRole("link", { name: "Download" })).toBeVisible()
  expect(mock.createdJobIds).toHaveLength(1)

  await page.getByTestId("start-new-visualization").click()
  await expect(page.getByTestId("visualizer-step-upload")).toBeVisible()

  await cleanup(page, token as string, apiBase, category.id, product.id)
})

test("failed generation can be retried into a new completed attempt", async ({
  page,
}) => {
  const suffix = randomUUID().slice(0, 8)
  const apiBase = process.env.VITE_API_URL || "http://localhost:8000"
  await page.goto("/visualizer")
  await expect(page.getByTestId("visualizer-step-upload")).toBeVisible()
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  const { category, product } = await createEligibleProduct(
    page,
    token as string,
    apiBase,
    suffix,
  )
  const mock = await mockGenerations(page, {
    statusSequence: ["FAILED"],
    retryStatusSequence: ["PROCESSING", "COMPLETED"],
  })

  await uploadRoomPhoto(page)
  await page.getByTestId("surface-floor").click()
  await page.getByTestId("surface-next").click()
  await selectProduct(page, `VIS-${suffix}`, product.id)

  await page.getByTestId("generate-button").click()
  await expect(page.getByTestId("retry-button")).toBeVisible({
    timeout: 15_000,
  })
  await expect(page.getByText("The provider failed safely.")).toBeVisible()

  await page.getByTestId("retry-button").click()
  await expect(page.getByTestId("generation-result-image")).toBeVisible({
    timeout: 15_000,
  })
  expect(mock.createdJobIds).toHaveLength(1)
  expect(mock.retriedJobIds).toHaveLength(1)

  await cleanup(page, token as string, apiBase, category.id, product.id)
})

test("a step whose prerequisites are missing redirects to the earliest valid step", async ({
  page,
}) => {
  await page.goto("/visualizer?step=product")
  await expect(page).toHaveURL(/step=upload/)
  await expect(page.getByTestId("visualizer-step-upload")).toBeVisible()
})

test.describe("mobile visualizer", () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test("the flow is usable on a mobile viewport", async ({ page }) => {
    const suffix = randomUUID().slice(0, 8)
    const apiBase = process.env.VITE_API_URL || "http://localhost:8000"
    await page.goto("/visualizer")
    await expect(page.getByTestId("visualizer-step-upload")).toBeVisible()
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token"),
    )
    const { category, product } = await createEligibleProduct(
      page,
      token as string,
      apiBase,
      suffix,
    )

    await uploadRoomPhoto(page)
    await page.getByTestId("surface-floor").click()
    await page.getByTestId("surface-next").click()
    await expect(page.getByTestId("visualizer-step-product")).toBeVisible()
    await page.getByTestId("product-search").fill(`VIS-${suffix}`)
    await expect(page.getByTestId(`product-option-${product.id}`)).toBeVisible()
    await page.getByTestId(`product-option-${product.id}`).click()
    await page.getByTestId("product-next").click()
    await expect(page.getByTestId("visualizer-step-review")).toBeVisible()

    await cleanup(page, token as string, apiBase, category.id, product.id)
  })
})

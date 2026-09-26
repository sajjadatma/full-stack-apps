import { randomUUID } from "node:crypto"
import { expect, test } from "@playwright/test"

const apiBase = process.env.VITE_API_URL || "http://localhost:8000"

test("catalog reference page opens and switches between categories and brands", async ({
  page,
}) => {
  await page.goto("/catalog-references")

  await expect(
    page.getByRole("heading", { name: "Catalog references" }),
  ).toBeVisible()
  await expect(page.getByRole("tab", { name: "Categories" })).toHaveAttribute(
    "data-state",
    "active",
  )
  await page.getByRole("tab", { name: "Brands" }).click()
  await expect(page.getByRole("tab", { name: "Brands" })).toHaveAttribute(
    "data-state",
    "active",
  )
  await expect(page.getByRole("button", { name: "Add brand" })).toBeVisible()
})

test("all brand records remain searchable and paginated beyond the API page size", async ({
  page,
}) => {
  test.setTimeout(90_000)
  const suffix = randomUUID().slice(0, 8)
  await page.goto("/catalog-references")
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()
  const headers = { Authorization: `Bearer ${token}` }
  const createdIds: string[] = []
  const namePrefix = `E2E Brand ${suffix}`

  try {
    for (let index = 1; index <= 101; index += 1) {
      const response = await page.request.post(`${apiBase}/api/v1/brands/`, {
        headers,
        data: {
          name: `${namePrefix} ${index}`,
          slug: `e2e-brand-${suffix}-${index}`,
        },
      })
      expect(response.ok()).toBeTruthy()
      createdIds.push((await response.json()).id)
    }

    await page.goto("/catalog-references")
    await page.getByRole("tab", { name: "Brands" }).click()
    // Filter to just this run's records so the total is deterministic even
    // when other catalog tests create records concurrently.
    await page.getByLabel("Search brand").fill(suffix)
    await expect(
      page.getByRole("row").filter({ hasText: `${namePrefix} 101` }),
    ).toBeVisible()
    await page.getByRole("button", { name: "Next" }).click()
    await expect(page.getByText(/Showing 21–40 of \d+/)).toBeVisible()
    await expect(page.getByRole("button", { name: "Previous" })).toBeEnabled()
  } finally {
    for (let index = 0; index < createdIds.length; index += 10) {
      const batch = createdIds.slice(index, index + 10)
      await Promise.all(
        batch.map((id) =>
          page.request.delete(`${apiBase}/api/v1/brands/${id}`, { headers }),
        ),
      )
    }
  }
})

test("staff can create, edit, deactivate, reactivate, and delete categories and brands", async ({
  page,
}) => {
  const suffix = randomUUID().slice(0, 8)
  await page.goto("/catalog-references")
  // Scope the table to this run's records so row actions stay deterministic
  // while other catalog tests create records in parallel.
  await page.getByLabel("Search category").fill(suffix)

  await page.getByRole("button", { name: "Add category" }).click()
  let dialog = page.getByRole("dialog", { name: "Add category" })
  await dialog.getByLabel("Name").fill(`E2E Category ${suffix}`)
  await dialog.getByLabel("Slug").fill(`e2e-category-${suffix}`)
  await dialog.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Category created successfully")).toBeVisible()

  let row = page.getByRole("row").filter({ hasText: `E2E Category ${suffix}` })
  await expect(row).toBeVisible()
  await row.getByRole("button", { name: "Edit" }).click()
  dialog = page.getByRole("dialog", { name: "Edit category" })
  await dialog.getByLabel("Name").fill(`E2E Category Edited ${suffix}`)
  await dialog.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Category updated successfully")).toBeVisible()

  row = page
    .getByRole("row")
    .filter({ hasText: `E2E Category Edited ${suffix}` })
  await row.getByRole("button", { name: "Deactivate" }).click()
  await expect(row.getByText("Inactive")).toBeVisible()
  await row.getByRole("button", { name: "Reactivate" }).click()
  await expect(row.getByText("Active")).toBeVisible()
  await row.getByRole("button", { name: "Delete" }).click()
  await page
    .getByRole("dialog", { name: "Delete category" })
    .getByRole("button", { name: "Delete" })
    .click()
  await expect(page.getByText("Category deleted successfully")).toBeVisible()
  await expect(row).not.toBeVisible()

  await page.getByRole("tab", { name: "Brands" }).click()
  await page.getByLabel("Search brand").fill(suffix)
  await page.getByRole("button", { name: "Add brand" }).click()
  dialog = page.getByRole("dialog", { name: "Add brand" })
  await dialog.getByLabel("Name").fill(`E2E Brand ${suffix}`)
  await dialog.getByLabel("Slug").fill(`e2e-brand-${suffix}`)
  await dialog.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Brand created successfully")).toBeVisible()

  row = page.getByRole("row").filter({ hasText: `E2E Brand ${suffix}` })
  await row.getByRole("button", { name: "Edit" }).click()
  dialog = page.getByRole("dialog", { name: "Edit brand" })
  await dialog.getByLabel("Name").fill(`E2E Brand Edited ${suffix}`)
  await dialog.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Brand updated successfully")).toBeVisible()

  row = page.getByRole("row").filter({ hasText: `E2E Brand Edited ${suffix}` })
  await row.getByRole("button", { name: "Deactivate" }).click()
  await expect(row.getByText("Inactive")).toBeVisible()
  await row.getByRole("button", { name: "Reactivate" }).click()
  await expect(row.getByText("Active")).toBeVisible()
  await row.getByRole("button", { name: "Delete" }).click()
  await page
    .getByRole("dialog", { name: "Delete brand" })
    .getByRole("button", { name: "Delete" })
    .click()
  await expect(page.getByText("Brand deleted successfully")).toBeVisible()
  await expect(row).not.toBeVisible()
})

test("deleting category and brand referenced by a product shows the backend conflict", async ({
  page,
}) => {
  const suffix = randomUUID().slice(0, 8)
  await page.goto("/catalog-references")
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()
  const headers = { Authorization: `Bearer ${token}` }
  const categoryResponse = await page.request.post(
    `${apiBase}/api/v1/categories/`,
    {
      headers,
      data: {
        name: `Conflict Category ${suffix}`,
        slug: `conflict-category-${suffix}`,
      },
    },
  )
  expect(categoryResponse.ok()).toBeTruthy()
  const category = await categoryResponse.json()
  const brandResponse = await page.request.post(`${apiBase}/api/v1/brands/`, {
    headers,
    data: {
      name: `Conflict Brand ${suffix}`,
      slug: `conflict-brand-${suffix}`,
    },
  })
  expect(brandResponse.ok()).toBeTruthy()
  const brand = await brandResponse.json()
  const productResponse = await page.request.post(
    `${apiBase}/api/v1/products/`,
    {
      headers,
      data: {
        name: `Conflict Product ${suffix}`,
        sku: `CONFLICT-${suffix}`,
        slug: `conflict-product-${suffix}`,
        category_id: category.id,
        brand_id: brand.id,
      },
    },
  )
  expect(productResponse.ok()).toBeTruthy()
  const product = await productResponse.json()

  try {
    await page.reload()
    await expect(
      page.getByRole("heading", { name: "Catalog references" }),
    ).toBeVisible()
    await page.getByLabel("Search category").fill(suffix)

    await page
      .getByRole("row")
      .filter({ hasText: category.name })
      .getByRole("button", { name: "Delete" })
      .click()
    await page
      .getByRole("dialog", { name: "Delete category" })
      .getByRole("button", { name: "Delete" })
      .click()
    await expect(
      page.getByText(
        "This category is assigned to one or more products and cannot be deleted",
      ),
    ).toBeVisible()
    await page
      .getByRole("dialog", { name: "Delete category" })
      .getByRole("button", { name: "Cancel" })
      .click()

    await page.getByRole("tab", { name: "Brands" }).click()
    await page.getByLabel("Search brand").fill(suffix)
    await page
      .getByRole("row")
      .filter({ hasText: brand.name })
      .getByRole("button", { name: "Delete" })
      .click()
    await page
      .getByRole("dialog", { name: "Delete brand" })
      .getByRole("button", { name: "Delete" })
      .click()
    await expect(
      page.getByText(
        "This brand is assigned to one or more products and cannot be deleted",
      ),
    ).toBeVisible()
    await page
      .getByRole("dialog", { name: "Delete brand" })
      .getByRole("button", { name: "Cancel" })
      .click()
  } finally {
    await page.request.delete(`${apiBase}/api/v1/products/${product.id}`, {
      headers,
    })
    await page.request.delete(`${apiBase}/api/v1/categories/${category.id}`, {
      headers,
    })
    await page.request.delete(`${apiBase}/api/v1/brands/${brand.id}`, {
      headers,
    })
  }
})

test.describe("catalog references permission visibility", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("users without catalog permissions do not see or access the management page", async ({
    page,
  }) => {
    const email = `catalog-ref-${randomUUID()}@example.com`
    const password = `Qa-${randomUUID()}-pass`
    const { createUser } = await import("./utils/privateApi")
    const { logInUser } = await import("./utils/user")
    await createUser({ email, password })
    await logInUser(page, email, password)

    await expect(
      page.getByRole("link", { name: "Catalog references" }),
    ).toHaveCount(0)
    await page.goto("/catalog-references")
    await expect(page).not.toHaveURL(/\/catalog-references/)
  })
})

import { randomUUID } from "node:crypto"
import { expect, test } from "@playwright/test"

test("product management page shows the catalog and create action", async ({
  page,
}) => {
  await page.goto("/products")

  await expect(
    page.getByRole("heading", { name: "Product catalog" }),
  ).toBeVisible()
  await expect(page.getByRole("button", { name: "Add product" })).toBeVisible()
  await expect(page.getByLabel("Search products")).toBeVisible()
})

test("staff can create, edit, search, and deactivate a product", async ({
  page,
}) => {
  const suffix = randomUUID().slice(0, 8)
  const categoryName = `E2E Category ${suffix}`
  const apiBase = process.env.VITE_API_URL || "http://localhost:8000"
  await page.goto("/products")
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()

  const categoryResponse = await page.request.post(
    `${apiBase}/api/v1/categories/`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { name: categoryName, slug: `e2e-${suffix}` },
    },
  )
  expect(categoryResponse.ok()).toBeTruthy()
  const category = await categoryResponse.json()
  await page.reload()
  await expect(
    page.getByRole("heading", { name: "Product catalog" }),
  ).toBeVisible()

  const productName = `E2E Porcelain ${suffix}`
  const sku = `E2E-${suffix}`
  const slug = `e2e-tile-${suffix}`
  await page.getByRole("button", { name: "Add product" }).click()
  await page.getByLabel("Product name").fill(productName)
  await page.getByLabel("SKU").fill(sku)
  await page.getByLabel("Slug").fill(slug)
  const formDialog = page.getByRole("dialog", { name: "Add product" })
  await formDialog.getByLabel("Category").selectOption({ label: categoryName })
  await formDialog.getByLabel("Material").fill("porcelain")
  await formDialog.getByLabel("Finish").fill("matte")
  await formDialog.getByLabel("Price").fill("29.95")
  await page.getByRole("button", { name: "Save" }).click()

  await expect(page.getByText("Product created successfully")).toBeVisible()
  const row = page.getByRole("row").filter({ hasText: productName })
  await expect(row).toBeVisible()
  await expect(row).toContainText(sku)
  await expect(row).toContainText("Matte")
  await expect(
    page.getByRole("button", { name: "Product / SKU" }),
  ).toHaveAttribute("aria-description", "Sorting applies to this page only")

  await row.getByRole("button", { name: "Edit" }).click()
  const updatedName = `${productName} Updated`
  await page.getByLabel("Product name").fill(updatedName)
  await page.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Product updated successfully")).toBeVisible()
  await expect(
    page.getByRole("row").filter({ hasText: updatedName }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Close toast" }).last().click()

  await page.getByLabel("Search products").fill(sku)
  const updatedRow = page.getByRole("row").filter({ hasText: updatedName })
  await expect(updatedRow).toBeVisible()
  await updatedRow.getByRole("button", { name: "Deactivate" }).click()
  await expect(page.getByText("Product deactivated successfully")).toBeVisible()
  await expect(updatedRow).not.toBeVisible()

  const productsResponse = await page.request.get(
    `${apiBase}/api/v1/products/?q=${sku}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  const products = await productsResponse.json()
  await page.request.delete(
    `${apiBase}/api/v1/products/${products.data[0].id}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  )
  await page.request.delete(`${apiBase}/api/v1/categories/${category.id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
})

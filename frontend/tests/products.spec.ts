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

test("product suitable surfaces can be created, edited, and reopened", async ({
  page,
}) => {
  const suffix = randomUUID().slice(0, 8)
  const categoryName = `Surface Category ${suffix}`
  const apiBase = process.env.VITE_API_URL || "http://localhost:8000"
  await page.goto("/products")
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()

  const categoryResponse = await page.request.post(
    `${apiBase}/api/v1/categories/`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { name: categoryName, slug: `surface-${suffix}` },
    },
  )
  expect(categoryResponse.ok()).toBeTruthy()
  const category = await categoryResponse.json()
  await page.reload()

  const createProduct = async (
    name: string,
    surfaceValues: { floor: boolean; wall: boolean },
  ) => {
    await page.getByRole("button", { name: "Add product" }).click()
    const dialog = page.getByRole("dialog", { name: "Add product" })
    await dialog.getByLabel("Product name").fill(name)
    const identifier = name.toLowerCase().replaceAll(" ", "-")
    await dialog.getByLabel("SKU").fill(`SUR-${identifier}`)
    await dialog.getByLabel("Slug").fill(`surface-${identifier}`)
    await dialog.getByLabel("Category").selectOption({ label: categoryName })

    const floor = dialog.getByRole("checkbox", { name: "Floor" })
    const wall = dialog.getByRole("checkbox", { name: "Wall" })
    await expect(floor).not.toBeChecked()
    await expect(wall).not.toBeChecked()
    if (surfaceValues.floor) await floor.check()
    if (surfaceValues.wall) await wall.check()

    await dialog.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("Product created successfully")).toBeVisible()
    await expect(dialog).not.toBeVisible()
    await page.getByRole("button", { name: "Close toast" }).last().click()
  }

  const openProduct = async (name: string) => {
    const row = page
      .getByTestId("products-page")
      .locator("tbody tr")
      .filter({ hasText: name })
    await expect(row).toBeVisible()
    await row.getByRole("button", { name: "Edit" }).click()
    return page.getByRole("dialog", { name: "Edit product" })
  }

  const floorName = `Floor tile ${suffix}`
  await createProduct(floorName, { floor: true, wall: false })
  let editDialog = await openProduct(floorName)
  await expect(
    editDialog.getByRole("checkbox", { name: "Floor" }),
  ).toBeChecked()
  await expect(
    editDialog.getByRole("checkbox", { name: "Wall" }),
  ).not.toBeChecked()
  await editDialog.getByRole("checkbox", { name: "Wall" }).check()
  await editDialog.getByRole("button", { name: "Save" }).click()
  await expect(page.getByText("Product updated successfully")).toBeVisible()

  editDialog = await openProduct(floorName)
  await expect(
    editDialog.getByRole("checkbox", { name: "Floor" }),
  ).toBeChecked()
  await expect(editDialog.getByRole("checkbox", { name: "Wall" })).toBeChecked()
  await editDialog.getByRole("button", { name: "Cancel" }).click()

  const wallName = `Wall tile ${suffix}`
  await createProduct(wallName, { floor: false, wall: true })
  editDialog = await openProduct(wallName)
  await expect(
    editDialog.getByRole("checkbox", { name: "Floor" }),
  ).not.toBeChecked()
  await expect(editDialog.getByRole("checkbox", { name: "Wall" })).toBeChecked()
  await editDialog.getByRole("button", { name: "Cancel" }).click()

  const bothName = `Dual surface ${suffix}`
  await createProduct(bothName, { floor: true, wall: true })
  editDialog = await openProduct(bothName)
  await expect(
    editDialog.getByRole("checkbox", { name: "Floor" }),
  ).toBeChecked()
  await expect(editDialog.getByRole("checkbox", { name: "Wall" })).toBeChecked()
  await editDialog.getByRole("button", { name: "Cancel" }).click()

  const emptyName = `No surface ${suffix}`
  await createProduct(emptyName, { floor: false, wall: false })
  editDialog = await openProduct(emptyName)
  await expect(
    editDialog.getByRole("checkbox", { name: "Floor" }),
  ).not.toBeChecked()
  await expect(
    editDialog.getByRole("checkbox", { name: "Wall" }),
  ).not.toBeChecked()
  await editDialog.getByRole("button", { name: "Cancel" }).click()

  for (const name of [floorName, wallName, bothName, emptyName]) {
    const response = await page.request.get(
      `${apiBase}/api/v1/products/?q=SUR-${name.toLowerCase().replaceAll(" ", "-")}`,
      { headers: { Authorization: `Bearer ${token}` } },
    )
    const products = await response.json()
    const created = products.data.find(
      (product: { name: string }) => product.name === name,
    )
    expect(created).toBeTruthy()
    await page.request.delete(`${apiBase}/api/v1/products/${created.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  }
  await page.request.delete(`${apiBase}/api/v1/categories/${category.id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
})

test("staff can recover image uploads and manage primary, order, and deletion", async ({
  page,
}) => {
  const suffix = randomUUID().slice(0, 8)
  const categoryName = `Image Category ${suffix}`
  const apiBase = process.env.VITE_API_URL || "http://localhost:8000"
  await page.goto("/products")
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()

  const categoryResponse = await page.request.post(
    `${apiBase}/api/v1/categories/`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { name: categoryName, slug: `image-e2e-${suffix}` },
    },
  )
  expect(categoryResponse.ok()).toBeTruthy()
  const category = await categoryResponse.json()
  await page.reload()

  let uploadRequests = 0
  await page.route("**/api/v1/products/*/images/", async (route) => {
    if (route.request().method() !== "POST") return route.continue()
    uploadRequests += 1
    if (uploadRequests === 2) {
      await route.fulfill({ status: 503, body: "temporary upload failure" })
      return
    }
    await route.continue()
  })

  const productName = `Image Tile ${suffix}`
  await page.getByRole("button", { name: "Add product" }).click()
  const dialog = page.getByRole("dialog", { name: "Add product" })
  await dialog.getByLabel("Product name").fill(productName)
  await dialog.getByLabel("SKU").fill(`IMG-${suffix}`)
  await dialog.getByLabel("Slug").fill(`image-tile-${suffix}`)
  await dialog.getByLabel("Category").selectOption({ label: categoryName })
  await dialog.locator('input[type="file"]').setInputFiles([
    {
      name: "first.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/qVQAAAAASUVORK5CYII=",
        "base64",
      ),
    },
    {
      name: "retry.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/qVQAAAAASUVORK5CYII=",
        "base64",
      ),
    },
    {
      name: "third.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/qVQAAAAASUVORK5CYII=",
        "base64",
      ),
    },
  ])
  const uploadQueue = dialog.getByRole("list", { name: "Image upload queue" })
  await expect(uploadQueue.getByRole("listitem")).toHaveCount(3)
  await dialog.getByRole("button", { name: "Save" }).click()

  const savedDialog = page.getByRole("dialog", { name: "Edit product" })
  const savedQueue = savedDialog.getByRole("list", {
    name: "Image upload queue",
  })
  await expect(
    savedQueue.getByRole("listitem").filter({ hasText: "Failed" }),
  ).toHaveCount(1)
  await expect(
    savedQueue.getByRole("listitem").filter({ hasText: "Success" }),
  ).toHaveCount(2)
  await savedDialog.getByRole("button", { name: "Retry retry.png" }).click()
  await expect(savedDialog).not.toBeVisible()
  expect(uploadRequests).toBe(4)

  const productListAfterRetry = await page.request.get(
    `${apiBase}/api/v1/products/?q=IMG-${suffix}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  const productAfterRetry = (await productListAfterRetry.json()).data[0]
  const productDetailAfterRetry = await page.request.get(
    `${apiBase}/api/v1/products/${productAfterRetry.id}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  expect((await productDetailAfterRetry.json()).images).toHaveLength(3)

  await page.getByLabel("Search products").fill(`IMG-${suffix}`)
  // Wait for the debounced search to settle so the products query key stops
  // changing; otherwise the list refetch unmounts the row and closes the dialog.
  const productRows = page.getByTestId("products-page").locator("tbody tr")
  await expect(productRows).toHaveCount(1)
  // Radix marks the page background aria-hidden while the modal is open, so
  // role-based locators cannot see the catalog table. Use a DOM-based locator.
  const productRow = productRows.filter({ hasText: productName })
  await expect(productRow).toBeVisible()
  await productRow.getByRole("button", { name: "Edit" }).click()
  const editDialog = page.getByRole("dialog", { name: "Edit product" })
  const images = editDialog.getByTestId("product-image-item")
  await expect(images).toHaveCount(3)
  await expect(images.nth(0)).toContainText("first.png")
  await expect(images.nth(0)).toContainText("Primary")
  await expect(images.nth(1)).toContainText("third.png")
  await expect(images.nth(1)).toContainText("Additional")
  await expect(images.nth(2)).toContainText("retry.png")

  const fetchImages = async () => {
    const response = await page.request.get(
      `${apiBase}/api/v1/products/${productAfterRetry.id}`,
      { headers: { Authorization: `Bearer ${token}` } },
    )
    return (await response.json()).images as {
      id: string
      alt_text: string
      is_primary: boolean
    }[]
  }

  // First upload is the primary and its authenticated content renders as a blob.
  await expect(productRow.locator("img")).toHaveAttribute("src", /^blob:/)
  const firstPrimaryThumbnail = await productRow
    .locator("img")
    .getAttribute("src")
  expect(await fetchImages()).toHaveLength(3)
  expect(
    (await fetchImages()).find((image) => image.is_primary)?.alt_text,
  ).toBe("first.png")

  // Reorder: move retry.png above third.png. Order becomes [first, retry, third].
  const reorderResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/images/order") &&
      response.request().method() === "PUT",
  )
  await images
    .nth(2)
    .getByRole("button", { name: /Move .* up/ })
    .click()
  expect((await reorderResponse).ok()).toBeTruthy()
  await expect(images.nth(1)).toContainText("retry.png")
  await expect(images.nth(2)).toContainText("third.png")

  // Set primary: third.png becomes primary while staying in last position.
  const thirdImageId = (await fetchImages()).find(
    (image) => image.alt_text === "third.png",
  )!.id
  const primaryResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/primary") &&
      response.request().method() === "PUT",
  )
  await images
    .nth(2)
    .getByRole("button", { name: /Set as primary/ })
    .click()
  expect((await primaryResponse).ok()).toBeTruthy()
  await expect(images.nth(2)).toContainText("Primary")
  expect((await fetchImages()).find((image) => image.is_primary)?.id).toBe(
    thirdImageId,
  )

  // Catalog row reflects the new primary through a freshly fetched blob.
  await expect
    .poll(() => productRow.locator("img").getAttribute("src"))
    .not.toBe(firstPrimaryThumbnail)
  const primaryThumbnail = await productRow.locator("img").getAttribute("src")

  // Delete a non-primary image (retry.png at index 1) with confirmation.
  let nonPrimaryDialogType = ""
  page.once("dialog", (dialog) => {
    nonPrimaryDialogType = dialog.type()
    void dialog.accept()
  })
  await images
    .nth(1)
    .getByRole("button", { name: /Delete/ })
    .click()
  expect(nonPrimaryDialogType).toBe("confirm")
  await expect(images).toHaveCount(2)
  await expect(images.nth(0)).toContainText("first.png")
  await expect(images.nth(1)).toContainText("third.png")
  await expect(editDialog.getByText("retry.png")).toHaveCount(0)

  // Delete the primary image and observe backend-promoted primary.
  let primaryDialogType = ""
  page.once("dialog", (dialog) => {
    primaryDialogType = dialog.type()
    void dialog.accept()
  })
  await images
    .nth(1)
    .getByRole("button", { name: /Delete/ })
    .click()
  expect(primaryDialogType).toBe("confirm")
  await expect(images).toHaveCount(1)
  await expect(images.first()).toContainText("first.png")
  await expect(images.first()).toContainText("Primary")
  expect(
    (await fetchImages()).find((image) => image.is_primary)?.alt_text,
  ).toBe("first.png")
  await expect
    .poll(() => productRow.locator("img").getAttribute("src"))
    .not.toBe(primaryThumbnail)

  await editDialog.getByRole("button", { name: "Close" }).click()

  const product = await page.request.get(
    `${apiBase}/api/v1/products/?q=IMG-${suffix}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  const productId = (await product.json()).data[0].id as string
  const remainingImageId = (
    await page.request
      .get(`${apiBase}/api/v1/products/${productId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((response) => response.json())
  ).images[0].id as string
  await page.request.delete(
    `${apiBase}/api/v1/products/${productId}/images/${remainingImageId}`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  await page.request.delete(`${apiBase}/api/v1/products/${productId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  await page.request.delete(`${apiBase}/api/v1/categories/${category.id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
})

test("image controls require products.manage_images", async ({ page }) => {
  await page.route("**/api/v1/users/me", async (route) => {
    const response = await route.fetch()
    const user = await response.json()
    user.permissions = user.permissions.filter(
      (permission: string) => permission !== "products.manage_images",
    )
    await route.fulfill({ response, json: user })
  })

  await page.goto("/products")
  await page.getByRole("button", { name: "Add product" }).click()
  const dialog = page.getByRole("dialog", { name: "Add product" })
  await expect(dialog.getByLabel("Product images")).toHaveCount(0)
})

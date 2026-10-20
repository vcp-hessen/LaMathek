/// <reference lib="dom" />
// Journey 5: a Materialwartin sets up new material — type with a variant,
// three pieces in a new Set, a photo.
import type { Page } from '@playwright/test'

import { expect, test } from './support/fixtures.ts'

const DONNERSKOPF = 1

/** A small JPEG drawn by the browser, as a phone camera would deliver one. */
async function jpeg(page: Page): Promise<Buffer> {
  const dataUrl = await page.evaluate(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 48
    const context = canvas.getContext('2d')!
    context.fillStyle = '#ffcc00'
    context.fillRect(0, 0, 64, 48)
    return canvas.toDataURL('image/jpeg')
  })
  return Buffer.from(dataUrl.split(',')[1]!, 'base64')
}

test('Material: Materialart mit Variante, drei Kohten in einem neuen Set, ein Foto', async ({ page, as }) => {
  await as('manager')

  await test.step('Materialart „Kohte“ mit Variante Farbe', async () => {
    await page.goto(`/inventories/${DONNERSKOPF}/material-types`)
    await page.getByRole('button', { name: 'Neue Materialart' }).click()
    await page.getByLabel('Name der Materialart').fill('Kohte')
    await page.getByLabel('Kürzel').fill('KO')
    await page.getByRole('button', { name: 'Variante hinzufügen' }).click()
    await page.getByLabel('Bezeichnung').fill('Farbe')
    for (const value of ['schwarz', 'weiß']) {
      await page.getByPlaceholder('z. B. 35 cm').fill(value)
      await page.getByRole('button', { name: 'Hinzufügen', exact: true }).click()
    }
    await page.getByRole('button', { name: 'Materialart anlegen' }).click()
    await expect(page.getByRole('button', { name: /^KO · Kohte Einzelteil/ })).toBeVisible()
  })

  await test.step('drei schwarze Kohten in ein neues Set', async () => {
    await page.goto(`/inventories/${DONNERSKOPF}/material`)
    await page.getByRole('button', { name: 'Anlegen' }).click()
    await page.getByRole('menuitem', { name: 'Mehrere Einzelteile' }).click()
    await page.getByLabel('Materialart wählen').selectOption({ label: 'Kohte' })
    await page.getByLabel('Farbe').selectOption('schwarz')
    await page.getByRole('radio', { name: 'Neues Set' }).check()
    await page.getByRole('textbox', { name: 'Name des Sets' }).fill('Kohten schwarz')
    await page.getByRole('spinbutton', { name: 'Anzahl' }).fill('3')
    await page.getByLabel('Namensmuster').fill('Kohte {n}')
    const form = page.getByRole('heading', { name: 'Mehrere Einzelteile anlegen' }).locator('..')
    await form.getByRole('button', { name: 'Anlegen', exact: true }).click()
    for (const name of ['Kohte 1', 'Kohte 2', 'Kohte 3']) {
      await expect(page.getByRole('cell', { name, exact: true })).toBeVisible()
    }
  })

  await test.step('das Set führt die drei Kohten', async () => {
    await page.goto(`/inventories/${DONNERSKOPF}/sets`)
    await page.getByRole('cell', { name: 'Kohten schwarz', exact: true }).click()
    await expect(page.getByRole('textbox', { name: 'Name des Sets' })).toHaveValue('Kohten schwarz')
    for (const name of ['Kohte 1', 'Kohte 2', 'Kohte 3']) {
      await expect(page.getByRole('listitem').filter({ hasText: `${name} · Kohte` })).toBeVisible()
    }
  })

  await test.step('Foto an Kohte 1', async () => {
    await page.goto(`/inventories/${DONNERSKOPF}/material`)
    await page.getByRole('cell', { name: 'Kohte 1', exact: true }).click()
    await expect(page.getByRole('textbox', { name: 'Bezeichnung' })).toHaveValue('Kohte 1')
    await expect(page.getByLabel('Farbe')).toHaveValue('schwarz')
    const uploaded = page.waitForResponse((r) => r.request().method() === 'POST' && r.url().includes('/photos'))
    await page.getByLabel('Foto hinzufügen').setInputFiles({ name: 'kohte.jpg', mimeType: 'image/jpeg', buffer: await jpeg(page) })
    expect((await uploaded).status()).toBe(201)
    const photo = page.locator('img[src*="/api/photos/"]').first()
    await expect(photo).toBeVisible()
    const response = await page.request.get((await photo.getAttribute('src'))!)
    expect(response.headers()['content-type']).toBe('image/webp')
  })
})

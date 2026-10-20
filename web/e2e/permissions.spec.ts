// Journey 4: Leserecht means seeing and requesting, not managing; contact data
// of a person with a login is theirs alone.
import { Api } from './support/api.ts'
import { CSRF, expect, isoDay, test } from './support/fixtures.ts'

const LANDESBUERO = 2

test('Leserecht: Lea fragt im Landesbüro an, verwalten darf sie nichts', async ({ page, as, mails }) => {
  const api = new Api(page)
  await as('admin')
  const leaId = await api.userId('Lea Leiterin')
  // Arrange: Lea has no phone yet, so the request asks for it.
  await api.send('patch', `/api/users/${leaId}`, { phone: '' })

  await test.step('sieht Material, aber keine Verwaltung', async () => {
    await as('borrower')
    await page.goto(`/inventories/${LANDESBUERO}/material-types`)
    await expect(page.getByRole('button', { name: 'Beamer Einzelteil Technik' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Neue Materialart' })).toHaveCount(0)
    await page.goto(`/inventories/${LANDESBUERO}/material`)
    await expect(page.getByRole('cell', { name: 'Beamer 1' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Anlegen' })).toHaveCount(0)

    await page.goto('/users')
    await expect(page.getByText('Nur Superuser*innen und Materialwart*innen können die Nutzerliste öffnen.')).toBeVisible()
    const forbidden = await page.request.post(`/api/inventories/${LANDESBUERO}/material-types`, {
      data: { name: 'Zelt', tracking: 'piece' },
      headers: CSRF,
    })
    expect(forbidden.status()).toBe(403)
  })

  await test.step('legt eine Box an und fragt an, mit eigener Telefonnummer', async () => {
    await page.goto(`/inventories/${LANDESBUERO}/material`)
    await page.getByRole('banner').locator('summary').click()
    await page.getByRole('button', { name: 'Neuer Verleih' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Verleih' })).toBeVisible()
    const loanUrl = page.url()

    await page.goto(`/inventories/${LANDESBUERO}/material`)
    // Material rows are links to the item; find Beamer 1 by its cell.
    const beamer = page.getByRole('link').filter({ has: page.getByRole('cell', { name: 'Beamer 1', exact: true }) })
    await beamer.getByRole('button', { name: 'In die Box' }).click()
    await expect(page.getByRole('banner').locator('summary')).toContainText('1')

    await page.goto(loanUrl)
    await page.getByLabel('Titel').fill('Infoabend')
    await page.getByRole('combobox', { name: 'Name der Gruppe' }).fill('Landesleitung')
    await page.getByLabel('Abholung (Wunsch)').fill(isoDay(14))
    await page.getByLabel('Rückgabe (Wunsch)').fill(isoDay(15))
    await page.getByRole('button', { name: 'Speichern' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Infoabend' })).toBeVisible()

    await page.getByRole('textbox', { name: /Deine Telefonnummer/ }).fill('+49 6421 123456')
    await page.getByRole('button', { name: 'Anfrage senden' }).click()
    await expect(page.getByText('Wartet auf Freigabe durch Materialwart*innen.')).toBeVisible()
    await mails.waitFor('mara@example.org', /Infoabend/)
    expect(await api.get<{ phone: string }>('/api/me')).toMatchObject({ phone: '+49 6421 123456' })
  })

  await test.step('die Materialwartin darf Leas Kontaktdaten nicht ändern', async () => {
    await as('manager')
    const response = await page.request.patch(`/api/users/${leaId}`, {
      data: { phone: '0000' },
      headers: CSRF,
    })
    expect(response.status()).toBe(403)
  })
})

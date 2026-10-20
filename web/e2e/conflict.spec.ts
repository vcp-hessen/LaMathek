// Journey 2: an overlapping request is warned about and refused, a free period goes through.
import { Api } from './support/api.ts'
import { expect, isoDay, test } from './support/fixtures.ts'

const DONNERSKOPF = 1

test('Konflikt: Zursula ist schon vergeben, ein anderer Zeitraum geht', async ({ page, as }) => {
  // Seed: „Herbstfahrt“ (confirmed, days 7–10) and „Hajk“ (requested, days 9–12), both the Jurte.
  await as('manager')
  const api = new Api(page)
  const loans = await api.get<{ id: number; eventName: string | null }[]>(`/api/inventories/${DONNERSKOPF}/loans`)
  const hajk = loans.find((loan) => loan.eventName === 'Hajk')!
  await page.goto(`/inventories/${DONNERSKOPF}/loans/${hajk.id}`)

  await test.step('die Warnung nennt den anderen Verleih', async () => {
    const hints = page.getByRole('status').filter({ hasText: 'Hinweise zur Belegung' })
    await expect(hints.getByText('Zursula: im Zeitraum schon vergeben an')).toBeVisible()
    await expect(hints.getByRole('link', { name: '„Herbstfahrt“' }).first()).toHaveAttribute(
      'href',
      new RegExp(`/inventories/${DONNERSKOPF}/loans/\\d+$`),
    )
  })

  await test.step('Bestätigen wird mit den Konflikten abgelehnt', async () => {
    const saved = page.waitForResponse((r) => r.request().method() === 'PATCH' && r.url().includes('/api/loans/'))
    await page.getByLabel('Zuständige*r Materialwart*in').selectOption({ label: 'Mara Matwart' })
    await saved
    await page.getByRole('checkbox', { name: 'Alle auswählen' }).check()
    await page.getByRole('button', { name: /^15 bestätigen$/ }).click()
    const error = page.getByRole('alert').filter({ hasText: 'Zursula' })
    // Every conflicting position at once, each with its name.
    await expect(error).toContainText('Zursula: im Zeitraum schon vergeben an „Herbstfahrt“')
    await expect(error).toContainText('12 × Seil (3 m): nur 8 von 20 frei im Zeitraum, 12 gewünscht')
    await expect(page.getByRole('row').filter({ hasText: 'Zursula' })).toContainText('Angefragt')
  })

  await test.step('in einem freien Zeitraum geht es', async () => {
    await page.getByLabel('Abholung (Termin)').fill(isoDay(20))
    await page.getByLabel('Rückgabe (Termin)').fill(isoDay(22))
    const saved = page.waitForResponse((r) => r.request().method() === 'PATCH' && r.url().includes('/api/loans/'))
    await page.getByRole('button', { name: 'Speichern' }).click()
    expect((await saved).status()).toBe(200)
    await expect(page.getByRole('status').filter({ hasText: 'Hinweise zur Belegung' })).toBeHidden()

    await page.getByRole('checkbox', { name: 'Alle auswählen' }).check()
    await page.getByRole('button', { name: /^15 bestätigen$/ }).click()
    await expect(page.getByRole('row').filter({ hasText: 'Angefragt' })).toHaveCount(0)
    await expect(page.getByRole('row').filter({ hasText: 'Bestätigt' })).toHaveCount(15)
  })
})

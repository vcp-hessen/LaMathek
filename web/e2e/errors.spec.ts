// Journey 6: what people see when something is missing, not theirs, or their session ended.
import { Api } from './support/api.ts'
import { expect, test } from './support/fixtures.ts'

const DONNERSKOPF = 1

test('Fehler: unbekannte Seite, gelöschter und fremder Verleih', async ({ page, as }) => {
  await as('admin')
  const api = new Api(page)
  const own = await api.send<{ id: number }>('post', `/api/inventories/${DONNERSKOPF}/loans`, {
    groupName: 'Landesleitung',
  })

  await test.step('eine Seite, die es nicht gibt', async () => {
    await page.goto('/gibt-es-nicht')
    await expect(page.getByRole('heading', { name: 'Seite nicht gefunden' })).toBeVisible()
    await page.getByRole('link', { name: 'Zur Startseite' }).click()
    await expect(page).toHaveURL(/\/$/)
  })

  await test.step('ein Verleih, den es nicht gibt', async () => {
    await page.goto(`/inventories/${DONNERSKOPF}/loans/999999`)
    await expect(page.getByRole('alert')).toContainText('Das gibt es nicht (mehr)')
  })

  await test.step('ein fremder Verleih', async () => {
    await as('borrower')
    await page.goto(`/inventories/${DONNERSKOPF}/loans/${own.id}`)
    await expect(page.getByRole('alert')).toContainText('Dafür fehlt dir die Berechtigung.')
  })
})

test('Fehler: abgelaufene Sitzung führt zur Startseite mit Hinweis', async ({ page, as }) => {
  await as('manager')
  await page.goto(`/inventories/${DONNERSKOPF}/loans`)
  await expect(page.getByRole('heading', { name: /Verleih/ }).first()).toBeVisible()
  await page.waitForLoadState('networkidle')

  await page.context().clearCookies()
  // Navigate inside the app (no reload) to a page that loads fresh data.
  await page.getByRole('complementary').getByRole('link', { name: 'Kalender', exact: true }).click()
  await expect(page.getByText('Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Anmelden' }).or(page.getByRole('link', { name: 'Anmelden' })).first()).toBeVisible()
})

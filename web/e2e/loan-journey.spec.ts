// Journey 1: a Verleih from the box to the end, clicked by both sides.
import type { Page } from '@playwright/test'

import { expect, isoDay, test } from './support/fixtures.ts'

const DONNERSKOPF = 1
const JURTE = 1

async function selectAllLines(page: Page) {
  await page.getByRole('checkbox', { name: 'Alle auswählen' }).check()
}

/** Run a line action on every position, then close the phase. */
async function finishStep(page: Page, action: RegExp, closeLabel: string) {
  // The phase button shows once the loan is reloaded; selecting earlier would be reset.
  const close = page.getByRole('button', { name: closeLabel })
  await expect(close).toBeDisabled()
  await selectAllLines(page)
  await page.getByRole('button', { name: action }).click()
  await expect(close).toBeEnabled()
  await close.click()
  await expect(page.getByRole('button', { name: closeLabel })).toBeHidden()
}

test('Verleih: Jurte anfragen, freigeben, packen, abholen, zurückgeben, übernehmen', async ({
  page,
  as,
  mails,
}) => {
  let loanUrl = ''

  await test.step('Ausleihende legt die Jurte in die Box und fragt an', async () => {
    await as('borrower')
    await page.goto(`/inventories/${DONNERSKOPF}/sets/${JURTE}`)
    await page.getByRole('button', { name: 'In die Box (Zuordnung)' }).click()
    await expect(page.getByRole('button', { name: 'Aus der Box nehmen (Zuordnung)' })).toBeVisible()

    await page.getByRole('banner').locator('summary').click()
    await page.getByRole('link', { name: /^Sommerlager/ }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Sommerlager' })).toBeVisible()
    loanUrl = page.url()
    // 2 DV from the seed plus the 15 positions of the Jurte.
    await expect(page.getByRole('row').filter({ hasText: 'Entwurf' })).toHaveCount(17)

    await page.getByLabel('Abholung (Wunsch)').fill(isoDay(30))
    await page.getByLabel('Rückgabe (Wunsch)').fill(isoDay(33))
    await page.getByRole('button', { name: 'Speichern' }).click()
    await page.getByRole('button', { name: 'Anfrage senden' }).click()
    await expect(page.getByText('Wartet auf Freigabe durch Materialwart*innen.')).toBeVisible()
  })

  await test.step('Materialwartin sagt alles zu und schließt die Freigabe ab', async () => {
    await mails.waitFor('mara@example.org', /Sommerlager/)
    await mails.clear()
    await as('manager')
    await page.goto(loanUrl)
    const saved = page.waitForResponse((r) => r.request().method() === 'PATCH' && r.url().includes('/api/loans/'))
    await page.getByLabel('Zuständige*r Materialwart*in').selectOption({ label: 'Mara Matwart' })
    expect((await saved).status()).toBe(200)
    await expect(page.getByLabel('Abholung (Termin)')).toHaveValue(isoDay(30))
    await finishStep(page, /^17 bestätigen$/, 'Freigabe abschließen')

    const toBorrower = await mails.waitFor('lea@example.org', /Sommerlager/)
    expect(toBorrower.flatMap((mail) => mail.attachments)).toEqual([])
    const toManager = await mails.waitFor('mara@example.org', /Sommerlager/)
    expect(toManager.flatMap((mail) => mail.attachments)).toContainEqual(expect.stringMatching(/\.pdf$/))
  })

  await test.step('Packen, Abholung, Rückgabe, Übernahme', async () => {
    await finishStep(page, /^17 als gepackt markieren$/, 'Packen abschließen')
    await finishStep(page, /^17 als abgeholt markieren$/, 'Abholung abschließen')
    await finishStep(page, /^17 Rückgabe melden$/, 'Rückgabe abschließen')
    // Taking back the last position closes the Verleih; the receipt goes out on request.
    await expect(page.getByRole('button', { name: 'Übernahme abschließen' })).toBeDisabled()
    await selectAllLines(page)
    await mails.clear()
    await page.getByRole('button', { name: /^17 übernehmen$/ }).click()
    await expect(page.getByRole('main').getByText('Abgeschlossen', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Änderungen mitteilen' }).click()
    await expect(page.getByRole('button', { name: 'Änderungen mitteilen' })).toBeHidden()
    await mails.waitFor('lea@example.org', /Sommerlager/)
  })

  await test.step('Journal und Mails', async () => {
    const journal = page.getByRole('heading', { name: 'Journal' }).locator('xpath=following-sibling::ul[1]')
    for (const entry of ['Verleih angelegt', 'Set hinzugefügt', 'Angefragt', 'Rückgabe gemeldet']) {
      await expect(journal.getByText(entry, { exact: true })).toBeVisible()
    }
    // Impersonated steps name both people (D0005 journal actors).
    await expect(journal.getByText('Mara Matwart (durch Erika Admin)').first()).toBeVisible()
    // Ausleihende never get a PDF (D0012).
    const toBorrower = (await mails.list()).filter((mail) => mail.to.includes('lea@example.org'))
    expect(toBorrower.flatMap((mail) => mail.attachments)).toEqual([])
  })
})

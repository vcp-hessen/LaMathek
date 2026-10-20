// Journey 3: Mengen with variants — a partial loss of one length, found again, written off.
import { Api, arrangeLoan } from './support/api.ts'
import { expect, test } from './support/fixtures.ts'

const DONNERSKOPF = 1

type StockRow = {
  materialTypeId: number
  lots: { id: number; variant: Record<string, string>; quantity: number; lostQuantity: number }[]
}

async function seilLots(api: Api, seilId: number) {
  const rows = await api.get<StockRow[]>(`/api/inventories/${DONNERSKOPF}/stocks`)
  const lots = rows.find((row) => row.materialTypeId === seilId)!.lots
  return Object.fromEntries(lots.map((lot) => [lot.variant['Länge'], lot]))
}

test('Mengen: Seil 4 m kommt nur teilweise zurück, wird wiedergefunden und ausgebucht', async ({ page, as }) => {
  const api = new Api(page)
  await as('admin')
  const seil = await api.materialTypeId(DONNERSKOPF, 'Seil')
  const before = await seilLots(api, seil)
  const loanId = await arrangeLoan(page, {
    inventoryId: DONNERSKOPF,
    title: 'Seilkurs',
    lines: [
      { materialTypeId: seil, quantity: 3, variant: { Länge: '4 m' } },
      { materialTypeId: seil, quantity: 5, variant: { Länge: '3 m' } },
    ],
    start: -4,
    end: -1,
    until: 'restock',
  })

  await test.step('Übernahme: von 3 Seilen 4 m ist nur 1 zurück', async () => {
    await as('manager')
    await page.goto(`/inventories/${DONNERSKOPF}/loans/${loanId}`)
    await page.getByRole('row').filter({ hasText: 'Seil (4 m)' }).getByRole('checkbox').check()
    await page.getByLabel('zurück von 3').fill('1')
    await page.getByLabel('Grund').fill('Zwei Seile im Wald geblieben')
    await page.getByRole('button', { name: /^1 übernehmen$/ }).click()
    await expect(page.getByRole('row').filter({ hasText: 'Seil (4 m)' }).filter({ hasText: 'Übernommen' })).toHaveCount(1)
    await expect(page.getByRole('row').filter({ hasText: 'Seil (3 m)' })).toContainText('Zurückgemeldet')
  })

  const lot4m = before['4 m']!
  await test.step('nur die Länge 4 m hat jetzt 2 verloren', async () => {
    const after = await seilLots(api, seil)
    expect(after['4 m']).toMatchObject({ quantity: lot4m.quantity, lostQuantity: 2 })
    expect(after['3 m']!.lostQuantity).toBe(before['3 m']!.lostQuantity)
  })

  await test.step('am Mengenposten: 1 wiedergefunden, 1 ausgebucht', async () => {
    await page.goto(`/inventories/${DONNERSKOPF}/stock-lots/${lot4m.id}`)
    await expect(page.getByText('davon 2 verloren')).toBeVisible()
    const losses = page.getByRole('heading', { name: 'Verluste und Verbrauch' }).locator('..')
    const open = losses.getByRole('listitem').filter({ hasText: '2 × Verlust' })
    await open.getByLabel('Anzahl gefunden').fill('1')
    await open.getByLabel('Grund').fill('Im Materialbus gefunden')
    await open.getByRole('button', { name: 'Wiedergefunden' }).click()
    await expect(page.getByText('davon 1 verloren')).toBeVisible()

    const rest = losses.getByRole('listitem').filter({ hasText: 'offen' })
    await rest.getByLabel('Grund').fill('Bleibt verschwunden')
    await rest.getByRole('button', { name: 'Ausbuchen' }).click()
    await expect(page.getByText(/davon \d+ verloren/)).toBeHidden()

    // Written off for good: the Soll-Anzahl drops by one, nothing is open any more.
    const after = await seilLots(api, seil)
    expect(after['4 m']).toMatchObject({ quantity: lot4m.quantity - 1, lostQuantity: 0 })
  })
})

// Shared setup for the end-to-end journeys: people, the mail sink, and a guard
// that fails a test on page errors, console errors and any 5xx (which includes
// API answers that break their contract, API_CONTRACT_CHECK=1).
import { expect, test as base, type Page } from '@playwright/test'

/** People from scripts/seed_demo.py (admin is the dev-bypass superuser). */
export const PEOPLE = {
  admin: 'Erika Admin',
  manager: 'Mara Matwart',
  borrower: 'Lea Leiterin',
} as const
export type Persona = keyof typeof PEOPLE

export const CSRF = { 'X-Requested-With': 'lamathek' }
const SINK = `http://127.0.0.1:${process.env.E2E_SMTP_HTTP_PORT ?? 2526}/messages`

export type Mail = { to: string[]; subject: string; attachments: string[]; raw: string }

/** ISO date `offset` days from today in the instance time zone. */
export function isoDay(offset: number): string {
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Berlin' }).format(new Date())
  const date = new Date(`${today}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + offset)
  return date.toISOString().slice(0, 10)
}

function decodeWords(value: string): string {
  return value.replace(/=\?([^?]+)\?([bqBQ])\?([^?]*)\?=\s*/g, (_m, _charset, encoding, text) => {
    if (encoding.toLowerCase() === 'b') return Buffer.from(text, 'base64').toString('utf8')
    const bytes = text
      .replace(/_/g, ' ')
      .replace(/=([0-9A-Fa-f]{2})/g, (_x: string, hex: string) => String.fromCharCode(parseInt(hex, 16)))
    return Buffer.from(bytes, 'latin1').toString('utf8')
  })
}

function parseMail(message: { to: string[]; raw: string }): Mail {
  const unfolded = message.raw.replace(/\r\n[ \t]+/g, ' ')
  const subject = decodeWords(/^Subject: (.*)$/im.exec(unfolded)?.[1] ?? '')
  const attachments = [...unfolded.matchAll(/Content-Disposition: attachment;\s*filename\*?=([^\r\n]+)/gi)].map(
    ([, name]) => {
      const raw = name!.trim().replace(/^"|"$/g, '')
      return raw.startsWith("utf-8''") ? decodeURIComponent(raw.slice(7)) : decodeWords(raw)
    },
  )
  return { to: message.to, subject, attachments, raw: message.raw }
}

export class Mailbox {
  async clear(): Promise<void> {
    await fetch(SINK, { method: 'DELETE' })
  }

  async list(): Promise<Mail[]> {
    const messages = (await (await fetch(SINK)).json()) as { to: string[]; raw: string }[]
    return messages.map(parseMail)
  }

  /** Mails to `address` once the outbox sent at least one matching `subject`. */
  async waitFor(address: string, subject: RegExp): Promise<Mail[]> {
    let found: Mail[] = []
    await expect
      .poll(
        async () => {
          found = (await this.list()).filter((m) => m.to.includes(address) && subject.test(m.subject))
          return found.length
        },
        { message: `mail to ${address} matching ${subject}`, timeout: 20_000 },
      )
      .toBeGreaterThan(0)
    return found
  }
}

/** Sign in through the dev bypass, then act as `persona` via the real impersonation. */
export async function signInAs(page: Page, persona: Persona): Promise<void> {
  await page.goto('/login')
  if (persona === 'admin') return
  const users = (await (await page.request.get('/api/users')).json()) as { id: number; name: string }[]
  const person = users.find((user) => user.name === PEOPLE[persona])
  expect(person, `seeded user ${PEOPLE[persona]}`).toBeTruthy()
  const started = await page.request.post('/api/impersonation', {
    data: { userId: person!.id, reason: 'E2E' },
    headers: CSRF,
  })
  expect(started.status()).toBe(204)
}

const IGNORED = [
  /WebGL/, // maps need a GPU; headless Chrome may not have one
  /Failed to load resource: the server responded with a status of 4\d\d/, // expected refusals
]

export const test = base.extend<{ as: (persona: Persona) => Promise<void>; mails: Mailbox; guard: void }>({
  as: async ({ page }, use) => {
    await use((persona) => signInAs(page, persona))
  },
  mails: async ({}, use) => {
    const mailbox = new Mailbox()
    await mailbox.clear()
    await use(mailbox)
  },
  guard: [
    async ({ page }, use) => {
      const problems: string[] = []
      page.on('pageerror', (error) => {
        if (!IGNORED.some((re) => re.test(error.message))) problems.push(`page error: ${error.message}`)
      })
      page.on('console', (message) => {
        if (message.type() === 'error' && !IGNORED.some((re) => re.test(message.text()))) {
          problems.push(`console: ${message.text()}`)
        }
      })
      page.on('response', (response) => {
        if (response.status() >= 500) problems.push(`${response.status()} ${response.url()}`)
      })
      await use()
      expect(problems, 'errors in the browser or 5xx from the API').toEqual([])
    },
    { auto: true },
  ],
})

export { expect }

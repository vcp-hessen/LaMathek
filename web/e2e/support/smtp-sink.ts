// A minimal SMTP server that keeps every mail in memory, for the end-to-end tests.
// SMTP on E2E_SMTP_PORT (2525); GET /messages lists them, DELETE /messages clears.
import { createServer as createHttpServer } from 'node:http'
import { createServer } from 'node:net'

type Message = { from: string; to: string[]; raw: string }

const smtpPort = Number(process.env.E2E_SMTP_PORT ?? 2525)
const httpPort = Number(process.env.E2E_SMTP_HTTP_PORT ?? 2526)
let messages: Message[] = []

createServer((socket) => {
  socket.setEncoding('utf8')
  let buffer = ''
  let inData = false
  let current: Message = { from: '', to: [], raw: '' }
  const reply = (line: string) => socket.write(`${line}\r\n`)
  reply('220 e2e-sink ESMTP')
  socket.on('data', (chunk: string) => {
    buffer += chunk
    for (;;) {
      if (inData) {
        const end = buffer.indexOf('\r\n.\r\n')
        if (end === -1) return
        current.raw = buffer.slice(0, end).replace(/\r\n\.\./g, '\r\n.')
        buffer = buffer.slice(end + 5)
        inData = false
        messages.push(current)
        current = { from: '', to: [], raw: '' }
        reply('250 OK')
        continue
      }
      const newline = buffer.indexOf('\r\n')
      if (newline === -1) return
      const line = buffer.slice(0, newline)
      buffer = buffer.slice(newline + 2)
      const command = line.slice(0, 4).toUpperCase()
      if (command === 'EHLO' || command === 'HELO') reply('250 e2e-sink')
      else if (command === 'MAIL') {
        current.from = /<(.*)>/.exec(line)?.[1] ?? ''
        reply('250 OK')
      } else if (command === 'RCPT') {
        current.to.push(/<(.*)>/.exec(line)?.[1] ?? '')
        reply('250 OK')
      } else if (command === 'DATA') {
        inData = true
        reply('354 End data with <CR><LF>.<CR><LF>')
      } else if (command === 'QUIT') {
        reply('221 Bye')
        socket.end()
        return
      } else reply('250 OK')
    }
  })
}).listen(smtpPort, '127.0.0.1')

createHttpServer((request, response) => {
  if (request.url !== '/messages') {
    response.writeHead(404).end()
    return
  }
  if (request.method === 'DELETE') messages = []
  response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify(messages))
}).listen(httpPort, '127.0.0.1')

console.log(`SMTP sink on ${smtpPort}, messages on http://127.0.0.1:${httpPort}/messages`)

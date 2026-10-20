---
status: accepted
---

# PDF lists with WeasyPrint

Pack, handover and return lists are PDFs rendered on the server from Jinja templates (`templates/pdf/`) with WeasyPrint, plus a QR code (`qrcode`) linking the Verleih. The same templates serve the download and the mail attachment, so both always match. Fonts (Roboto) ship inside the Python package.

WeasyPrint needs Cairo and Pango from the operating system; the Dockerfile installs them, local development needs them too (see README). Rendering in the browser (print CSS) was rejected because mails need the file without a browser; a PDF library with a drawing API (ReportLab) was rejected because HTML templates are easier to keep in line with the app's wording.

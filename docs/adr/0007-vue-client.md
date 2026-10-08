---
status: accepted
---

# Vue 3 client, with the data stack from an existing project

The UI is a Vue 3 application, built with Vite, routed with Vue Router, and using Pinia for client state. Server data is fetched with Axios and TanStack Query. Forms use VeeValidate and Zod.

This is the same client shape as another project that already performs well. The Python API still validates every request; Zod does not replace that.

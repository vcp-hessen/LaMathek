import axios from 'axios'

export const api = axios.create({
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    // Required by the API on every state-changing request (CSRF guard): a
    // cross-site form cannot set custom headers.
    'X-Requested-With': 'lamathek',
  },
})

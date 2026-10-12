// Same-origin by default (backend serves this folder). When the page is opened as a file or from a
// separate static server on :3000, talk to the local backend instead. For production on a different
// domain, set the URL here and add that domain to ALLOWED_ORIGINS in .env.
window.ITI_MITRA_API_URL =
  location.protocol === "file:" || location.port === "3000" ? "http://localhost:8000" : "";

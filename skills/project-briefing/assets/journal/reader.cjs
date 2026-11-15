const fs = require("node:fs/promises");
const path = require("node:path");
const posthtml = require("posthtml");

// Bundle the existing pages for a dashboard: no separate server or reader layout.
async function buildReader(root) {
  const files = [];
  async function visit(directory) {
    for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
      const file = path.join(directory, entry.name);
      if (entry.isDirectory()) await visit(file);
      else if (entry.name.endsWith(".html") && entry.name !== "reader.html") files.push(file);
    }
  }
  await visit(root);
  const pages = {};
  const assets = new Map();
  const mime = { ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif" };
  let styles = "";
  for (const file of files) {
    const page = "/" + path.relative(root, file).split(path.sep).join("/");
    let body, title;
    const tree = (await posthtml().process(await fs.readFile(file, "utf8"))).tree;
    const pending = [];
    tree.walk((node) => {
      if (node.tag === "body") body = node.content;
      if (node.tag === "title") title = node.content.join("");
      if (page === "/index.html" && node.tag === "style") styles += node.content.join("");
      for (const key of ["href", "src"]) {
        const ref = node.attrs?.[key];
        if (!ref || /^(?:\/\/|[a-z][a-z0-9+.-]*:)/i.test(ref)) continue;
        const url = new URL(ref, "https://journal.invalid" + page);
        const target = decodeURIComponent(url.pathname);
        if (key === "href" && target.endsWith(".html")) {
          node.attrs.href = "#" + url.pathname + url.hash;
        } else {
          const asset = path.resolve(root, "." + target);
          if (!asset.startsWith(root + path.sep)) throw new Error(`Asset escapes journal: ${ref}`);
          if (!assets.has(asset)) assets.set(asset, fs.readFile(asset).then((bytes) =>
            `data:${mime[path.extname(asset)] || "application/octet-stream"};base64,${bytes.toString("base64")}`));
          pending.push(assets.get(asset).then((data) => { node.attrs[key] = data; }));
        }
      }
      if (node.tag === "a" && /^https?:/i.test(node.attrs?.href || "")) {
        node.attrs.target = "_blank";
        node.attrs.rel = "noopener noreferrer";
      }
      return node;
    });
    await Promise.all(pending);
    pages[page] = { title, html: posthtml().render(body) };
  }
  const data = JSON.stringify(pages).replace(/</g, "\\u003c");
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Journal</title>
<style>${styles}</style></head><body><div id="journal-reader"></div>
<script type="application/json" id="journal-pages">${data}</script>
<script>
(() => {
  const pages = JSON.parse(document.getElementById("journal-pages").textContent);
  const reader = document.getElementById("journal-reader");
  reader.addEventListener("click", (event) => {
    const link = event.target.closest("a[href^='#/']");
    if (!link) return;
    event.preventDefault();
    // srcdoc inherits the host's base URL; update this frame's fragment directly.
    const route = link.getAttribute("href");
    if (location.hash === route) render();
    else location.hash = route;
  });
  function render() {
    const [path, heading] = location.hash.slice(1).split("#");
    const page = pages[path] || pages["/index.html"];
    reader.innerHTML = page.html;
    document.title = page.title;
    if (heading) document.getElementById(decodeURIComponent(heading))?.scrollIntoView();
    else window.scrollTo(0, 0);
  }
  addEventListener("hashchange", render);
  render();
})();
</script></body></html>`;
  await fs.writeFile(path.join(root, "reader.html"), html);
}

buildReader(path.resolve(process.argv[2])).catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});

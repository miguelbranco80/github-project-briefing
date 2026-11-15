const fs = require("node:fs");
const path = require("node:path");
const posthtml = require("posthtml");

module.exports = function (eleventyConfig) {
  const stylesheet = fs.readFileSync("src/assets/style.css", "utf8");
  eleventyConfig.addTransform("relative-links", async function (content) {
    if (!this.page.outputPath.endsWith(".html")) return content;
    const current = this.page.url.endsWith("/") ? this.page.url + "index.html" : this.page.url;
    return (await posthtml().use((tree) => tree.walk((node) => {
      if (node.tag === "link" && node.attrs?.rel === "stylesheet" && node.attrs.href === "/assets/style.css") {
        return { tag: "style", content: [stylesheet] };
      }
      for (const key of ["href", "src"]) {
        const ref = node.attrs?.[key];
        if (!ref || /^(?:#|\/\/|[a-z][a-z0-9+.-]*:)/i.test(ref)) continue;
        const url = new URL(ref, "https://journal.invalid" + current);
        const target = url.pathname.endsWith("/") ? url.pathname + "index.html" : url.pathname;
        node.attrs[key] = path.posix.relative(path.posix.dirname(current), target) + url.search + url.hash;
      }
      return node;
    })).process(content)).html;
  });
  eleventyConfig.addPreprocessor("literal-articles", "md", function (data) {
    if (data.tags?.includes("posts")) data.templateEngineOverride = "md";
  });
  eleventyConfig.addGlobalData("eleventyComputed", {
    permalink: (data) => data.tags?.includes("posts")
      ? `/posts/${path.basename(data.page.inputPath, ".md")}/index.html`
      : data.permalink,
  });
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  eleventyConfig.addCollection("posts", function (collectionApi) {
    const posts = collectionApi.getFilteredByTag("posts");
    for (const post of posts) {
      const data = post.data;
      const required = ["title", "description", "issue", "window"];
      if (data.cover != null) required.push("cover", "coverAlt");
      for (const key of required) {
        if (typeof data[key] !== "string" || !data[key].trim() || data[key].startsWith("TODO:")) {
          throw new Error(`${post.inputPath}: missing ${key}`);
        }
      }
      if (Number.isNaN(new Date(data.date).getTime())) {
        throw new Error(`${post.inputPath}: missing or invalid date`);
      }
      if (data.cover != null) {
        const cover = path.resolve(process.cwd(), "src", data.cover.slice(1));
        const assets = path.resolve(process.cwd(), "src/assets") + path.sep;
        if (!data.cover.startsWith("/assets/") || !cover.startsWith(assets) || !fs.existsSync(cover) || !fs.statSync(cover).isFile()) {
          throw new Error(`${post.inputPath}: cover must be a saved local asset`);
        }
      }
    }
    return posts.sort((a, b) => a.date - b.date || Number(a.data.run || a.data.issue || 0) - Number(b.data.run || b.data.issue || 0));
  });
  eleventyConfig.amendLibrary("md", function (md) {
    md.use(require("markdown-it-anchor"), {
      slugify: function (title) {
        return title.toLowerCase().trim().replace(/[^\p{L}\p{N}\s-]/gu, "").replace(/\s+/g, "-");
      }
    });
  });
  eleventyConfig.addFilter("dateLabel", function (date) {
    return new Intl.DateTimeFormat("en-GB", {
      day: "numeric", month: "long", year: "numeric", timeZone: "UTC"
    }).format(new Date(date));
  });
  eleventyConfig.addFilter("isoDate", function (date) {
    return new Date(date).toISOString().slice(0, 10);
  });
  eleventyConfig.addFilter("readingTime", function (content) {
    const words = content.replace(/<[^>]*>/g, " ").trim().split(/\s+/).length;
    return Math.max(1, Math.ceil(words / 220));
  });
  eleventyConfig.addFilter("olderPosts", function (posts) {
    return posts.slice(0, -1).reverse();
  });
  eleventyConfig.addFilter("byMonth", function (posts) {
    const groups = [];
    for (const post of posts.slice().reverse()) {
      const label = new Intl.DateTimeFormat("en-GB", {
        month: "long", year: "numeric", timeZone: "UTC"
      }).format(post.date);
      let group = groups.at(-1);
      if (!group || group.label !== label) {
        group = { label: label, posts: [] };
        groups.push(group);
      }
      group.posts.push(post);
    }
    return groups;
  });
  return { markdownTemplateEngine: "njk", dir: { input: "src", output: "_site", includes: "_includes", data: "_data" } };
};

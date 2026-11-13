const fs = require("node:fs");
const path = require("node:path");

module.exports = function (eleventyConfig) {
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
        const cover = path.resolve(__dirname, "src", data.cover.slice(1));
        const assets = path.resolve(__dirname, "src/assets") + path.sep;
        if (!data.cover.startsWith("/assets/") || !cover.startsWith(assets) || !fs.existsSync(cover) || !fs.statSync(cover).isFile()) {
          throw new Error(`${post.inputPath}: cover must be a saved local asset`);
        }
      }
      if (!Array.isArray(data.topics) || !data.topics.length || data.topics.some(topic => !topic.label || !topic.id)) {
        throw new Error(`${post.inputPath}: topics need labels and heading ids`);
      }
    }
    return posts;
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
  return { dir: { input: "src", output: "_site", includes: "_includes", data: "_data" } };
};

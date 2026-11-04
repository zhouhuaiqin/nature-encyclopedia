# 部署到 GitHub Pages（让别人搜到你的网站）

## 0. 先改站点地址
打开 `site.config.json`，把 `siteUrl` 改成你的实际地址，例如：

```json
{
  "siteUrl": "https://你的GitHub用户名.github.io/nature-encyclopedia",
  "siteName": "自然图鉴"
}
```

> 仓库名不是 `nature-encyclopedia` 时，路径要相应修改；绑定自定义域名后改成 `https://你的域名`。

改完运行一次，重新生成静态页、sitemap、canonical：

```bash
node scripts/build_static.cjs
```

## 1. 创建 GitHub 仓库并推送
在 GitHub 新建一个空仓库（不要勾选 README），然后在本目录执行：

```bash
git init -b main
git add .
git commit -m "自然图鉴：2658 物种静态站 + 搜索"
git remote add origin https://github.com/你的用户名/nature-encyclopedia.git
git push -u origin main
```

> 仓库约 315 MB，首次推送较慢；若嫌大，先把 `assets/images` 转 WebP 再推。

## 2. 开启 Pages
1. 仓库 **Settings → Pages**
2. **Build and deployment → Source** 选 **GitHub Actions**
3. 等 Actions 里的 “Deploy to GitHub Pages” 跑完
4. 访问 `https://你的用户名.github.io/nature-encyclopedia/`

工作流会自动重新生成 `species/*.html`、`sitemap.xml`、`search-index.js` 并部署。

## 3. 让搜索引擎收录
部署成功后，把 sitemap 提交给搜索引擎：

| 平台 | 地址 | 操作 |
|---|---|---|
| Google Search Console | https://search.google.com/search-console | 添加资源 → 验证 → Sitemaps 提交 `sitemap.xml` |
| Bing Webmaster Tools | https://www.bing.com/webmasters | 添加站点 → 提交 sitemap |
| 百度搜索资源平台 | https://ziyuan.baidu.com | 添加站点 → 普通收录 → sitemap |

收录通常需要 **1–4 周**；期间保持更新、增加外链（公众号/知乎/小红书/B站简介放链接）会更快。

## 4. 站点结构（已生成）
- `index.html`：交互式图鉴首页
- `species/<id>.html`：2658 个物种独立页（含 title/description/canonical/OG/JSON-LD）
- `species/index.html`：全部物种索引（爬虫入口）
- `search.html` + `search-index.js`：站内搜索（中文名/别名/学名/标签）
- `sitemap.xml` / `robots.txt`：提交给搜索引擎

## 5. 可选：Pagefind
如果之后想要更专业的站内搜索，可以安装 Pagefind：

```bash
npx pagefind --site .
```

它会生成 `_pagefind/`，再把 UI 接到 `search.html` 即可；当前的无依赖搜索已可用，不影响部署。

## 6. 国内访问说明
GitHub Pages 在中国大陆访问不稳定，百度收录也偏慢。面向国内用户建议：
- Cloudflare Pages + 自定义域名（免费、快），或
- 阿里云 OSS + CDN + ICP 备案（需域名与备案）。

## 7. 检查清单
- [ ] `site.config.json` 的 `siteUrl` 已改
- [ ] `node scripts/build_static.cjs` 已运行
- [ ] GitHub Pages 部署成功
- [ ] 打开 `/species/index.html` 能看到 2658 个链接
- [ ] `/sitemap.xml` 可访问且包含 2661 条 URL
- [ ] 已向 Google/Bing/百度提交 sitemap

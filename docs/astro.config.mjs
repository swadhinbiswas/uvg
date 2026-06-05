// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	site: 'https://uvg.dev',
	base: '/',
	trailingSlash: 'always',
	sitemap: {
		lastmod: new Date().toISOString(),
		priority: 0.7,
		changefreq: 'weekly',
	},
	integrations: [
		starlight({
			title: 'UVG',
			logo: {
				src: './src/assets/logo.svg',
			},
			favicon: '/favicon.svg',
			description: 'UV Global Runtime — Deterministic, reproducible, and isolated Python environments with content-addressable storage and workspace-scale dependency management.',
			tagline: 'Global runtime construction for UV',
			social: [
				{ icon: 'github', href: 'https://github.com/swadhin/uvg', label: 'GitHub' },
			],
			editLink: {
				baseUrl: 'https://github.com/swadhin/uvg/edit/main/docs/src/content/docs/',
			},
			lastUpdated: true,
			tableOfContents: {
				minHeadingLevel: 2,
				maxHeadingLevel: 3,
			},
			customCss: ['./src/assets/custom.css'],
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'Introduction', slug: 'getting-started/introduction' },
						{ label: 'Installation', slug: 'getting-started/installation' },
						{ label: 'Quick Start', slug: 'getting-started/quick-start' },
						{ label: 'Why UVG?', slug: 'getting-started/why-uvg' },
					],
				},
				{
					label: 'Core Concepts',
					items: [
						{ label: 'Package Identity', slug: 'concepts/package-identity' },
						{ label: 'Content-Addressable Store', slug: 'concepts/store' },
						{ label: 'Runtime Construction', slug: 'concepts/runtime' },
						{ label: 'Fingerprinting', slug: 'concepts/fingerprinting' },
						{ label: 'Dependency Isolation', slug: 'concepts/isolation' },
					],
				},
				{
					label: 'CLI Reference',
					items: [
						{ label: 'Overview', slug: 'cli/overview' },
						{ label: 'uvg init', slug: 'cli/init' },
						{ label: 'uvg add', slug: 'cli/add' },
						{ label: 'uvg remove', slug: 'cli/remove' },
						{ label: 'uvg sync', slug: 'cli/sync' },
						{ label: 'uvg run', slug: 'cli/run' },
						{ label: 'uvg doctor', slug: 'cli/doctor' },
						{ label: 'uvg scan', slug: 'cli/scan' },
						{ label: 'uvg verify', slug: 'cli/verify' },
						{ label: 'uvg stats', slug: 'cli/stats' },
						{ label: 'uvg info', slug: 'cli/info' },
						{ label: 'uvg store', slug: 'cli/store' },
						{ label: 'uvg workspace', slug: 'cli/workspace' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'Migrating from UV', slug: 'guides/migration' },
						{ label: 'Workspace Setup', slug: 'guides/workspace' },
						{ label: 'CI/CD Integration', slug: 'guides/ci-cd' },
						{ label: 'Custom Registries', slug: 'guides/registries' },
						{ label: 'Offline Mode', slug: 'guides/offline' },
						{ label: 'Performance Tuning', slug: 'guides/performance' },
						{ label: 'Tool Execution & Scripts', slug: 'guides/tools-scripts' },
					],
				},
				{
					label: 'Use Cases',
					items: [
						{ label: 'Monorepo Management', slug: 'use-cases/monorepo' },
						{ label: 'Multi-Python Projects', slug: 'use-cases/multi-python' },
						{ label: 'Reproducible Builds', slug: 'use-cases/reproducible-builds' },
						{ label: 'Data Science Workflows', slug: 'use-cases/data-science' },
						{ label: 'Microservices', slug: 'use-cases/microservices' },
						{ label: 'Edge Deployment', slug: 'use-cases/edge' },
					],
				},
				{
					label: 'Architecture',
					items: [
						{ label: 'Overview', slug: 'architecture/overview' },
						{ label: 'Store Architecture', slug: 'architecture/store' },
						{ label: 'Runtime Architecture', slug: 'architecture/runtime' },
						{ label: 'Database Design', slug: 'architecture/database' },
						{ label: 'Security Model', slug: 'architecture/security' },
						{ label: 'UV Integration', slug: 'architecture/uv-integration' },
					],
				},
				{
					label: 'Configuration',
					items: [
						{ label: 'Configuration File', slug: 'config/file' },
						{ label: 'Environment Variables', slug: 'config/env' },
						{ label: 'Store Location', slug: 'config/store-location' },
						{ label: 'UV Configuration', slug: 'config/uv-config' },
					],
				},
				{
					label: 'Contributing',
					items: [{ autogenerate: { directory: 'contributing' } }],
				},
			],
		}),
	],
});

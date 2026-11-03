import { defineCollection } from 'astro:content';
import { file } from 'astro/loaders';
import { z } from 'astro/zod';
import { parse } from 'yaml';

// Every project lives in one file: src/content/projects.yaml
const projects = defineCollection({
	loader: file('src/content/projects.yaml', {
		// Number each project as it's read, so the Projects page can keep the file's order.
		parser: (text) => parse(text).map((project: object, order: number) => ({ ...project, order })),
	}),
	schema: ({ image }) =>
		z.object({
			order: z.number(),
			title: z.string(),
			description: z.string(), // Projects page card only
			icon: image(),
			site: z.url().optional(),
			github: z.url().optional(),
			about: z.string().default(''),
			stack: z.array(z.string()).default([]),
			images: z.array(image()).default([]),
		}),
});

export const collections = { projects };

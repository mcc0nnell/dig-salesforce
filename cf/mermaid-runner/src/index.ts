import puppeteer from "@cloudflare/puppeteer";
import type { Fetcher } from "@cloudflare/workers-types";

const MAX_MERMAID_BYTES = 200 * 1024;
let renderCounter = 0;

interface Env {
	GEARY_KEY: string;
	MYBROWSER: Fetcher;
}

interface MermaidRequest {
	mermaid?: string;
	format?: string;
	id?: string;
}

interface BasicAst {
	kind: string;
	nodes?: string[];
	edges?: Array<{ from: string; to: string }>;
	participants?: string[];
	messages?: Array<{ from: string; to: string; message: string }>;
	classes?: string[];
	relations?: Array<{ from: string; to: string; type: string }>;
	raw?: string;
}

function jsonResponse(body: unknown, status = 200, extraHeaders: HeadersInit = {}): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: {
			"content-type": "application/json; charset=utf-8",
			...corsHeaders(),
			...extraHeaders,
		},
	});
}

function jsonResponseWithRequestId(body: Record<string, unknown>, requestId: string, status = 200): Response {
	return jsonResponse({ ...body, requestId }, status);
}

function errorResponse(status: number, message: string, requestId: string): Response {
	return jsonResponseWithRequestId({ ok: false, error: message }, requestId, status);
}

function corsHeaders(): HeadersInit {
	return {
		"access-control-allow-origin": "*",
		"access-control-allow-methods": "POST, OPTIONS",
		"access-control-allow-headers": "Content-Type, X-Geary-Key",
		"access-control-max-age": "86400",
	};
}

function verifyAuth(request: Request, env: Env): boolean {
	const key = request.headers.get("X-Geary-Key");
	return Boolean(key && env.GEARY_KEY && key === env.GEARY_KEY);
}

function sanitizeSvg(svg: string): string {
	if (!svg.includes("<svg")) {
		throw new Error("missing_svg");
	}
	if (/<script[\s>]/i.test(svg)) {
		throw new Error("embedded_script");
	}
	return svg;
}

function basicMermaidParse(mermaid: string): BasicAst {
	const trimmed = mermaid.trim();
	const lines = trimmed.split(/\r?\n/).map((line) => line.trim());

	if (/^\s*(flowchart|graph)\b/i.test(trimmed)) {
		const nodes = new Set<string>();
		const edges: Array<{ from: string; to: string }> = [];

		for (const line of lines) {
			const edgeMatch = line.match(/([A-Za-z0-9_]+)\s*[-.]+>\s*\|?.*?\|?\s*([A-Za-z0-9_]+)/);
			if (edgeMatch) {
				nodes.add(edgeMatch[1]);
				nodes.add(edgeMatch[2]);
				edges.push({ from: edgeMatch[1], to: edgeMatch[2] });
			}
		}

		return {
			kind: "flowchart",
			nodes: normalizeNodes(nodes),
			edges,
		};
	}

	if (/^\s*sequenceDiagram\b/i.test(trimmed)) {
		const participants = new Set<string>();
		const messages: Array<{ from: string; to: string; message: string }> = [];

		for (const line of lines) {
			const participantMatch = line.match(/^participant\s+([A-Za-z0-9_]+)/i);
			if (participantMatch) {
				participants.add(participantMatch[1]);
			}

			const msgMatch = line.match(/([A-Za-z0-9_]+)\s*[-=]+>\s*([A-Za-z0-9_]+)\s*:\s*(.+)$/);
			if (msgMatch) {
				participants.add(msgMatch[1]);
				participants.add(msgMatch[2]);
				messages.push({ from: msgMatch[1], to: msgMatch[2], message: msgMatch[3] });
			}
		}

		return {
			kind: "sequenceDiagram",
			participants: normalizeNodes(participants),
			messages,
		};
	}

	if (/^\s*stateDiagram\b/i.test(trimmed)) {
		const nodes = new Set<string>();
		const edges: Array<{ from: string; to: string }> = [];

		for (const line of lines) {
			const edgeMatch = line.match(/([A-Za-z0-9_]+)\s*-->\s*([A-Za-z0-9_]+)/);
			if (edgeMatch) {
				nodes.add(edgeMatch[1]);
				nodes.add(edgeMatch[2]);
				edges.push({ from: edgeMatch[1], to: edgeMatch[2] });
			}
		}

		return {
			kind: "stateDiagram",
			nodes: normalizeNodes(nodes),
			edges,
		};
	}

	if (/^\s*classDiagram\b/i.test(trimmed)) {
		const classes = new Set<string>();
		const relations: Array<{ from: string; to: string; type: string }> = [];

		for (const line of lines) {
			const classMatch = line.match(/^class\s+([A-Za-z0-9_]+)/i);
			if (classMatch) {
				classes.add(classMatch[1]);
			}

			const relationMatch = line.match(/([A-Za-z0-9_]+)\s*([<|o*.]+--[<|o*.]+|--|<\|--|\*--|o--)\s*([A-Za-z0-9_]+)/);
			if (relationMatch) {
				classes.add(relationMatch[1]);
				classes.add(relationMatch[3]);
				relations.push({ from: relationMatch[1], to: relationMatch[3], type: relationMatch[2] });
			}
		}

		return {
			kind: "classDiagram",
			classes: normalizeNodes(classes),
			relations,
		};
	}

	return { kind: "unknown", raw: mermaid };
}

function normalizeNodes(list: Set<string>): string[] {
	return Array.from(list).filter(Boolean).sort();
}

function parsePayloadText(text: string): MermaidRequest {
	if (!text.trim()) {
		return {};
	}
	return JSON.parse(text) as MermaidRequest;
}

type RenderStage = "load_mermaid" | "render" | "extract_svg";

const MERMAID_BUNDLE_URL = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";
const MERMAID_LOAD_TIMEOUT_MS = 5000;
const RENDER_TIMEOUT_MS = 10000;
const MAX_RENDER_ATTEMPTS = 3;
const MERMAID_BUNDLE_TIMEOUT_MS = 8000;

let mermaidBundlePromise: Promise<string> | null = null;
let sharedBrowser: Awaited<ReturnType<typeof puppeteer.launch>> | null = null;
let sharedBrowserPromise: Promise<Awaited<ReturnType<typeof puppeteer.launch>>> | null = null;

async function fetchMermaidBundle(): Promise<string> {
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), MERMAID_BUNDLE_TIMEOUT_MS);
	try {
		const response = await fetch(MERMAID_BUNDLE_URL, { signal: controller.signal });
		if (!response.ok) {
			throw new Error(`mermaid_bundle_http_${response.status}`);
		}
		const text = await response.text();
		if (!text.trim()) {
			throw new Error("mermaid_bundle_empty");
		}
		return text;
	} finally {
		clearTimeout(timer);
	}
}

async function getMermaidBundle(): Promise<string> {
	if (!mermaidBundlePromise) {
		mermaidBundlePromise = fetchMermaidBundle();
	}
	try {
		return await mermaidBundlePromise;
	} catch (err) {
		mermaidBundlePromise = null;
		throw err;
	}
}

async function replaceSharedBrowser(
	newBrowser: Awaited<ReturnType<typeof puppeteer.launch>>,
): Promise<void> {
	if (sharedBrowser && sharedBrowser !== newBrowser) {
		try {
			await sharedBrowser.close();
		} catch (err) {
			// swallow close errors; the next attempt or caller will surface real failures.
		}
	}
	sharedBrowser = newBrowser;
	sharedBrowserPromise = Promise.resolve(newBrowser);
}

async function getBrowser(env: Env, forceNew: boolean): Promise<Awaited<ReturnType<typeof puppeteer.launch>>> {
	if (forceNew) {
		try {
			const newBrowser = await puppeteer.launch(env.MYBROWSER);
			await replaceSharedBrowser(newBrowser);
			return newBrowser;
		} catch (err) {
			if (sharedBrowser) {
				return sharedBrowser;
			}
			throw err;
		}
	}

	if (sharedBrowser) {
		return sharedBrowser;
	}
	if (!sharedBrowserPromise) {
		sharedBrowserPromise = puppeteer
			.launch(env.MYBROWSER)
			.then(async (browser) => {
				await replaceSharedBrowser(browser);
				return browser;
			})
			.catch((err) => {
				sharedBrowserPromise = null;
				throw err;
			});
	}
	return sharedBrowserPromise;
}

class RenderError extends Error {
	readonly stage: RenderStage;
	readonly attempt: number;
	readonly elapsedMs: number;

	constructor(message: string, stage: RenderStage, attempt: number, elapsedMs: number) {
		super(message);
		this.stage = stage;
		this.attempt = attempt;
		this.elapsedMs = elapsedMs;
	}
}

function renderFailedResponse(
	requestId: string,
	detail: string,
	stage: RenderStage,
	attempt: number,
	elapsedMs: number,
): Response {
	return jsonResponseWithRequestId(
		{
			ok: false,
			error: "svg_render_failed",
			detail,
			stage,
			attempt,
			attempts: MAX_RENDER_ATTEMPTS,
			elapsedMs,
		},
		requestId,
		422,
	);
}

async function renderMermaidSvg(
	mermaidText: string,
	id: string | null,
	env: Env,
): Promise<{ svg: string; warnings: string[] }> {
	const renderId = id ?? `geary-mermaid-${renderCounter++}`;
	const htmlForBundle = (bundle: string) => `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <script>${bundle}</script>
  </head>
  <body>
    <script>
      (async () => {
        const code = ${JSON.stringify(mermaidText)};
        try {
          if (!globalThis.mermaid) {
            throw new Error("mermaid_not_loaded");
          }
          globalThis.mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
          const { svg } = await globalThis.mermaid.render("${renderId}", code);
          window.__SVG__ = svg;
          document.body.innerHTML = svg;
        } catch (err) {
          window.__SVG_ERROR__ = (err && err.message) || String(err);
        }
      })();
    </script>
  </body>
</html>`;

	let lastError: RenderError | null = null;

	for (let attempt = 1; attempt <= MAX_RENDER_ATTEMPTS; attempt++) {
		const attemptStart = Date.now();
		let browser: Awaited<ReturnType<typeof puppeteer.launch>> | null = null;
		let page: Awaited<ReturnType<Awaited<ReturnType<typeof puppeteer.launch>>["newPage"]>> | null =
			null;

		try {
			let mermaidBundle = "";
			try {
				mermaidBundle = await getMermaidBundle();
			} catch (err) {
				const message = err instanceof Error ? err.message : "mermaid_bundle_failed";
				throw new RenderError(message, "load_mermaid", attempt, Date.now() - attemptStart);
			}

			const html = htmlForBundle(mermaidBundle);
			browser = await puppeteer.launch(env.MYBROWSER);
			page = await browser.newPage();
			await page.setContent(html, { waitUntil: "domcontentloaded" });
			if (attempt === MAX_RENDER_ATTEMPTS) {
				await page.setContent(html, { waitUntil: "domcontentloaded" });
			}

			const stageLoad: RenderStage = "load_mermaid";
			await page.waitForFunction("window.mermaid && window.mermaid.render", {
				timeout: MERMAID_LOAD_TIMEOUT_MS,
			});

			const stageRender: RenderStage = "render";
			await page.waitForFunction("window.__SVG__ || window.__SVG_ERROR__", { timeout: RENDER_TIMEOUT_MS });
			const error = await page.evaluate(() => (window as any).__SVG_ERROR__ ?? null);
			if (error) {
				throw new RenderError(String(error), stageRender, attempt, Date.now() - attemptStart);
			}

			const stageExtract: RenderStage = "extract_svg";
			await page.waitForSelector("svg", { timeout: 2000 });
			const svg = await page.evaluate(() => (window as any).__SVG__);
			if (typeof svg !== "string") {
				throw new RenderError("missing_svg", stageExtract, attempt, Date.now() - attemptStart);
			}
			return { svg: sanitizeSvg(svg), warnings: [] };
		} catch (err) {
			if (err instanceof RenderError) {
				lastError = err;
			} else if (err instanceof Error) {
				lastError = new RenderError(err.message, "load_mermaid", attempt, Date.now() - attemptStart);
			} else {
				lastError = new RenderError("svg_render_failed", "load_mermaid", attempt, Date.now() - attemptStart);
			}
			if (attempt < MAX_RENDER_ATTEMPTS) {
				continue;
			}
			throw lastError;
		} finally {
			try {
				if (page) {
					await page.close();
				}
			} catch (closeErr) {
				// swallow close errors; the next attempt or caller will surface real failures.
			}
			try {
				if (browser) {
					await browser.close();
				}
			} catch (closeErr) {
				// swallow close errors; the next attempt or caller will surface real failures.
			}
		}
	}
	throw lastError ?? new RenderError("svg_render_failed", "load_mermaid", MAX_RENDER_ATTEMPTS, 0);
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		try {
			let requestId = crypto.randomUUID();
			const url = new URL(request.url);

			if (request.method === "OPTIONS") {
				return new Response(null, { status: 204, headers: corsHeaders() });
			}

			if (url.pathname !== "/render" || request.method !== "POST") {
				return jsonResponseWithRequestId({ ok: false, error: "not_found" }, requestId, 404);
			}

			const bodyBuffer = await request.arrayBuffer();

			if (bodyBuffer.byteLength > MAX_MERMAID_BYTES) {
				return errorResponse(413, "payload_too_large", requestId);
			}

			if (!verifyAuth(request, env)) {
				return errorResponse(401, "unauthorized", requestId);
			}

			let payload: MermaidRequest;
			try {
				const text = new TextDecoder().decode(bodyBuffer);
				payload = parsePayloadText(text);
			} catch (err) {
				return errorResponse(400, "invalid_json", requestId);
			}

			if (payload.id) {
				requestId = payload.id;
			}

			const mermaid = payload.mermaid?.trim();
			if (!mermaid) {
				return errorResponse(400, "missing_mermaid", requestId);
			}

			const id = payload.id ?? null;
			const rawFormat = payload.format;
			const normalizedFormat = typeof rawFormat === "string" ? rawFormat.trim().toLowerCase() : "";
			const format = normalizedFormat === "svg" ? "svg" : "json";
			const warnings: string[] = [];

			if (format === "svg") {
				try {
					const { svg, warnings: renderWarnings } = await renderMermaidSvg(mermaid, id, env);
					return jsonResponseWithRequestId({ ok: true, id, svg, warnings: renderWarnings }, requestId, 200);
				} catch (err) {
					if (err instanceof RenderError) {
						return renderFailedResponse(
							requestId,
							err.message,
							err.stage,
							err.attempt,
							err.elapsedMs,
						);
					}
					const detail = err instanceof Error ? err.message : "svg_render_failed";
					return renderFailedResponse(requestId, detail, "render", MAX_RENDER_ATTEMPTS, 0);
				}
			}

			const ast = basicMermaidParse(mermaid);
			return jsonResponseWithRequestId({ ok: true, id, warnings, ast }, requestId, 200);
		} catch (err) {
			const requestId = crypto.randomUUID();
			const message = err instanceof Error ? err.message : "unexpected_error";
			return errorResponse(500, message, requestId);
		}
	},
};

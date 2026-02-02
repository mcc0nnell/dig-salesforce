import { LightningElement, api } from 'lwc';

const SCHEMA_VERSION = '0.1';
const DEFAULT_BOUNDS = {
    max_custom_objects: 2,
    max_permission_sets: 1,
    allow_lwc: false
};

export default class GearyIntakeConsole extends LightningElement {
    @api mode = 'OFFLINE';
    @api keyPresent = false;
    @api workerHost = 'local';

    mermaidText = '';
    svgPreview = '';
    blueprintJson = '';
    receiptJson = '';
    emissionsNdjson = '';
    lastRunId = '';

    errorCode = '';
    errorMessage = '';
    statusMessage = '';
    isBusy = false;

    lastSvgPreview;

    get modeLabel() {
        return this.mode === 'LIVE' ? 'LIVE' : 'OFFLINE';
    }

    get keyPresentLabel() {
        return this.keyPresent ? 'yes' : 'no';
    }

    get hasError() {
        return Boolean(this.errorMessage);
    }

    get hasReceipt() {
        return Boolean(this.receiptJson);
    }

    get hasRunId() {
        return Boolean(this.lastRunId);
    }

    get disableCopyReceipt() {
        return !this.hasReceipt;
    }

    get disableCopyRunId() {
        return !this.hasRunId;
    }

    get isEmptyMermaid() {
        return !this.mermaidText || this.mermaidText.trim().length === 0;
    }

    renderedCallback() {
        if (this.svgPreview !== this.lastSvgPreview) {
            const container = this.template.querySelector('.geary-svg-container');
            if (container) {
                container.innerHTML = this.svgPreview || '';
            }
            this.lastSvgPreview = this.svgPreview;
        }
    }

    handleMermaidChange(event) {
        this.mermaidText = event.target.value;
    }

    handleFileChange(event) {
        const file = event.target.files && event.target.files[0];
        if (!file) {
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            this.mermaidText = String(reader.result || '');
        };
        reader.readAsText(file);
    }

    async handleRenderPreview() {
        this.clearError();
        this.isBusy = true;
        try {
            this.svgPreview = this.renderMermaidToSvg(this.mermaidText);
            this.statusMessage = 'Preview rendered.';
        } catch (error) {
            this.setError('RENDER_FAILED', error?.message || 'Unable to render preview.');
        } finally {
            this.isBusy = false;
        }
    }

    async handleGenerateBlueprint() {
        this.clearError();
        this.isBusy = true;
        try {
            const blueprint = await this.buildBlueprint();
            this.blueprintJson = JSON.stringify(blueprint, null, 2);
            this.statusMessage = 'Blueprint generated.';
        } catch (error) {
            this.setError('BLUEPRINT_FAILED', error?.message || 'Unable to generate blueprint.');
        } finally {
            this.isBusy = false;
        }
    }

    async handleValidateBlueprint() {
        this.clearError();
        this.isBusy = true;
        try {
            const blueprint = this.blueprintJson
                ? JSON.parse(this.blueprintJson)
                : await this.buildBlueprint();
            const validation = this.validateBlueprint(blueprint);
            if (!validation.ok) {
                this.setError(validation.code, validation.message);
                return;
            }
            this.statusMessage = 'Blueprint validated.';
        } catch (error) {
            this.setError('VALIDATION_FAILED', error?.message || 'Unable to validate blueprint.');
        } finally {
            this.isBusy = false;
        }
    }

    async handleExportBundle() {
        this.clearError();
        this.isBusy = true;
        try {
            const startedAt = new Date();
            const blueprint = this.blueprintJson
                ? JSON.parse(this.blueprintJson)
                : await this.buildBlueprint();
            const blueprintJson = JSON.stringify(blueprint, null, 2);
            const inputHash = await this.hashText(this.mermaidText);
            const outputHash = await this.hashText(blueprintJson);
            const runId = this.generateRunId();
            const finishedAt = new Date();
            const receipt = {
                run_id: runId,
                mode: this.modeLabel.toLowerCase(),
                status: 'success',
                input_hash: inputHash,
                output_hash: outputHash,
                started_at: startedAt.toISOString(),
                finished_at: finishedAt.toISOString(),
                error_code: '',
                error_message: ''
            };
            const emissions = this.buildEmissions(runId, startedAt, finishedAt);

            this.blueprintJson = blueprintJson;
            this.receiptJson = JSON.stringify(receipt, null, 2);
            this.emissionsNdjson = emissions.join('\n');
            this.lastRunId = runId;

            this.downloadFile('blueprint.json', 'application/json', this.blueprintJson);
            this.downloadFile('input.mmd', 'text/plain', this.mermaidText || '');
            this.downloadFile('receipt.json', 'application/json', this.receiptJson);
            this.downloadFile('emissions.ndjson', 'application/x-ndjson', this.emissionsNdjson);

            this.statusMessage = 'Bundle exported.';
        } catch (error) {
            this.setError('EXPORT_FAILED', error?.message || 'Unable to export bundle.');
        } finally {
            this.isBusy = false;
        }
    }

    async handleCopyReceipt() {
        if (!this.receiptJson) {
            return;
        }
        await navigator.clipboard.writeText(this.receiptJson);
        this.statusMessage = 'Receipt copied.';
    }

    async handleCopyRunId() {
        if (!this.lastRunId) {
            return;
        }
        await navigator.clipboard.writeText(this.lastRunId);
        this.statusMessage = 'Run ID copied.';
    }

    async buildBlueprint() {
        const mermaid = String(this.mermaidText || '').trim();
        const mermaidHash = await this.hashText(mermaid);
        return {
            schema_version: SCHEMA_VERSION,
            input: {
                mermaid: {
                    format: 'text',
                    text: mermaid,
                    hash: mermaidHash
                }
            },
            bounds: {
                ...DEFAULT_BOUNDS
            },
            operations: [],
            notes: ''
        };
    }

    validateBlueprint(blueprint) {
        if (!blueprint || blueprint.schema_version !== SCHEMA_VERSION) {
            return { ok: false, code: 'INVALID_SCHEMA', message: 'schema_version must be 0.1.' };
        }
        const bounds = blueprint.bounds || {};
        if (bounds.max_custom_objects > DEFAULT_BOUNDS.max_custom_objects) {
            return { ok: false, code: 'OUT_OF_BOUNDS', message: 'Custom object bound exceeded.' };
        }
        if (bounds.max_permission_sets > DEFAULT_BOUNDS.max_permission_sets) {
            return { ok: false, code: 'OUT_OF_BOUNDS', message: 'Permission set bound exceeded.' };
        }
        if (bounds.allow_lwc && !DEFAULT_BOUNDS.allow_lwc) {
            return { ok: false, code: 'OUT_OF_BOUNDS', message: 'LWC creation not allowed in this phase.' };
        }
        const operations = Array.isArray(blueprint.operations) ? blueprint.operations : [];
        let customObjectCount = 0;
        let permissionSetCount = 0;
        for (const op of operations) {
            if (op.action !== 'create_or_update') {
                return { ok: false, code: 'INVALID_OPERATION', message: 'Only create_or_update actions are allowed.' };
            }
            if (op.kind === 'custom_object') {
                customObjectCount += 1;
            } else if (op.kind === 'permission_set') {
                permissionSetCount += 1;
            } else if (op.kind === 'lwc') {
                return { ok: false, code: 'INVALID_OPERATION', message: 'LWC operations are not allowed.' };
            } else {
                return { ok: false, code: 'INVALID_OPERATION', message: 'Unknown operation kind.' };
            }
        }
        if (customObjectCount > bounds.max_custom_objects) {
            return { ok: false, code: 'OUT_OF_BOUNDS', message: 'Too many custom objects.' };
        }
        if (permissionSetCount > bounds.max_permission_sets) {
            return { ok: false, code: 'OUT_OF_BOUNDS', message: 'Too many permission sets.' };
        }
        return { ok: true, code: '', message: '' };
    }

    renderMermaidToSvg(text) {
        const lines = String(text || '').split(/\r?\n/);
        const lineHeight = 18;
        const width = 800;
        const height = Math.max(120, lines.length * lineHeight + 40);
        const escape = (value) => value
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        const textLines = lines
            .map((line, index) => `  <tspan x="20" y="${40 + index * lineHeight}">${escape(line)}</tspan>`)
            .join('\n');
        return `<?xml version="1.0" encoding="UTF-8"?>\n` +
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">\n` +
            `  <rect width="100%" height="100%" fill="#f3f2f2"/>\n` +
            `  <text font-family="SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace" font-size="13" fill="#1f1f1f">\n` +
            `${textLines}\n` +
            `  </text>\n` +
            `</svg>`;
    }

    buildEmissions(runId, startedAt, finishedAt) {
        const started = startedAt.toISOString();
        const finished = finishedAt.toISOString();
        return [
            JSON.stringify({ event: 'run.started', run_id: runId, at: started }),
            JSON.stringify({ event: 'blueprint.generated', run_id: runId, at: started }),
            JSON.stringify({ event: 'blueprint.validated', run_id: runId, at: started }),
            JSON.stringify({ event: 'bundle.exported', run_id: runId, at: finished }),
            JSON.stringify({ event: 'run.completed', run_id: runId, at: finished })
        ];
    }

    async hashText(text) {
        const encoder = new TextEncoder();
        const data = encoder.encode(String(text || ''));
        const digest = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(digest));
        const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
        return `sha256:${hashHex}`;
    }

    generateRunId() {
        const bytes = new Uint8Array(8);
        crypto.getRandomValues(bytes);
        const hex = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
        return `grn_${hex}`;
    }

    downloadFile(filename, mimeType, content) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        anchor.click();
        URL.revokeObjectURL(url);
    }

    clearError() {
        this.errorCode = '';
        this.errorMessage = '';
    }

    setError(code, message) {
        this.errorCode = code;
        this.errorMessage = message;
        this.statusMessage = '';
    }
}

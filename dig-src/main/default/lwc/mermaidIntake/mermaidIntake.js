import { LightningElement, track } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import renderSvgApex from '@salesforce/apex/MermaidRenderService.renderSvg';
import parseAstApex from '@salesforce/apex/MermaidRenderService.parseAst';

export default class MermaidIntake extends LightningElement {
    @track mermaid = '';
    @track isBusy = false;
    @track requestId;

    // Outputs
    @track svg; // raw string
    @track astPretty; // pretty printed json
    @track blueprintPretty; // pretty printed json

    // Computed helpers for disabling buttons and empty-state
    get isEmpty() {
        return !this.mermaid || this.mermaid.trim().length === 0;
    }
    get svgMissing() {
        return !this.svg;
    }
    get astMissing() {
        return !this.astPretty;
    }
    get blueprintMissing() {
        return !this.blueprintPretty;
    }

    handleMermaidChange(evt) {
        this.mermaid = evt.target.value;
    }

    async handleRenderSvg() {
        this.resetBusy();
        this.isBusy = true;
        try {
            const svg = await renderSvgApex({ mermaid: this.mermaid, id: this.requestId || null });
            this.svg = svg;
            this.requestId = this.requestId || this.extractRequestIdFromSvg(svg) || null;
            this.renderSvgIntoContainer(svg);
        } catch (e) {
            this.showError(e, 'Render SVG failed');
        } finally {
            this.isBusy = false;
        }
    }

    async handleParseJson() {
        this.resetBusy();
        this.isBusy = true;
        try {
            const res = await parseAstApex({ mermaid: this.mermaid, id: this.requestId || null });
            // res: { astJson, blueprintJson, requestId }
            this.requestId = res?.requestId || this.requestId || null;
            this.astPretty = this.pretty(res?.astJson);
            this.blueprintPretty = this.pretty(res?.blueprintJson);
        } catch (e) {
            this.showError(e, 'Parse JSON failed');
        } finally {
            this.isBusy = false;
        }
    }

    async handleBoth() {
        // Parse first (for request id), then render
        await this.handleParseJson();
        if (!this.isEmpty) {
            await this.handleRenderSvg();
        }
    }

    // DOM helpers
    renderSvgIntoContainer(svg) {
        try {
            const container = this.template.querySelector('.svg-container');
            if (container) {
                // Safe render: rely on SVG returned by trusted server. Do not evaluate scripts.
                container.innerHTML = '';
                if (svg) {
                    container.innerHTML = svg;
                }
            }
        } catch (e) {
            // non-fatal
            // eslint-disable-next-line no-console
            console.error('Failed to inject SVG', e);
        }
    }

    // Utilities
    resetBusy() {
        // Keep outputs; this method is a placeholder in case we want to clear anything before requests
    }

    extractRequestIdFromSvg(_svg) {
        // Request id is not embedded in svg; return null (placeholder for future)
        return null;
    }

    pretty(v) {
        if (!v) return null;
        try {
            if (typeof v === 'string') {
                return JSON.stringify(JSON.parse(v), null, 2);
            }
            return JSON.stringify(v, null, 2);
        } catch (e) {
            return v; // already pretty or not JSON
        }
    }

    showError(err, title) {
        let message = 'An error occurred';
        if (err && err.body && err.body.message) {
            message = err.body.message;
        } else if (err && err.message) {
            message = err.message;
        }
        this.dispatchEvent(
            new ShowToastEvent({
                title: title || 'Error',
                message,
                variant: 'error'
            })
        );
    }
}

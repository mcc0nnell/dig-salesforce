import { LightningElement } from 'lwc';

export default class MermaidIntake extends LightningElement {
    mermaidCode = '';
    isBusy = false;
    svgContent = '';
    jsonContent = '';
    error = '';
    lastSvgContent;
    
    get isEmpty() {
        return !this.mermaidCode || this.mermaidCode.trim() === '';
    }

    get isBusyOrEmpty() {
        return this.isBusy || this.isEmpty;
    }

    renderedCallback() {
        if (this.svgContent !== this.lastSvgContent) {
            const container = this.template.querySelector('.mermaid-svg-container');
            if (container) {
                container.innerHTML = this.svgContent || '';
            }
            this.lastSvgContent = this.svgContent;
        }
    }
    
    handleCodeChange(event) {
        this.mermaidCode = event.target.value;
    }
    
    handleRenderSvg() {
        // Implementation would go here
    }
    
    handleParseJson() {
        // Implementation would go here
    }
}

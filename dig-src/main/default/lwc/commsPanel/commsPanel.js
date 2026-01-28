import { LightningElement, api, track } from 'lwc';
import getDefaults from '@salesforce/apex/CommsService.getDefaults';
import listMessages from '@salesforce/apex/CommsService.listMessages';
import sendEmailApex from '@salesforce/apex/CommsService.sendEmail';

export default class CommsPanel extends LightningElement {
    @api recordId;

    @track toAddress = '';
    @track subject = '';
    @track bodyText = '';

    contactId;
    defaultsLoaded = false;
    sending = false;
    error;

    @track messages = [];

    connectedCallback() {
        this.loadDefaults();
    }

    async loadDefaults() {
        try {
            const d = await getDefaults({ recordId: this.recordId });
            this.contactId = d?.contactId;
            this.toAddress = d?.toEmail || '';
            this.defaultsLoaded = true;
            await this.refreshMessages();
        } catch (e) {
            this.error = this.normalizeError(e);
            this.defaultsLoaded = true;
        }
    }

    async refreshMessages() {
        try {
            const msgs = await listMessages({ recordId: this.recordId });
            this.messages = msgs || [];
        } catch (e) {
            // non-fatal
        }
    }

    onToChange(e) { this.toAddress = e.target.value; }
    onSubjectChange(e) { this.subject = e.target.value; }
    onBodyChange(e) { this.bodyText = e.target.value; }

    async sendEmail() {
        this.error = null;
        this.sending = true;
        try {
            await sendEmailApex({
                req: {
                    recordId: this.recordId,
                    contactId: this.contactId,
                    toAddress: this.toAddress,
                    subject: this.subject,
                    bodyText: this.bodyText
                }
            });
            this.bodyText = '';
            await this.refreshMessages();
        } catch (e) {
            this.error = this.normalizeError(e);
        } finally {
            this.sending = false;
        }
    }

    normalizeError(e) {
        if (!e) return 'Unknown error';
        if (Array.isArray(e.body)) return e.body.map(x => x.message).join(', ');
        if (e.body && typeof e.body.message === 'string') return e.body.message;
        if (typeof e.message === 'string') return e.message;
        return JSON.stringify(e);
    }
}

import { LightningElement } from 'lwc';
import { subscribe, unsubscribe, onError } from 'lightning/empApi';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';

const CHANNEL = '/event/DIG_Emission__e';
const MAX_EVENTS = 500;

export default class DigEmissionsConsole extends LightningElement {
    channelName = CHANNEL;
    subscription = null;

    runIdFilter = '';
    typeFilter = '';
    levelFilter = '';
    isPaused = false;

    events = [];
    selectedEvent = null;

    columns = [
        {
            label: 'IngestedAt',
            fieldName: 'ingestedAt',
            type: 'date',
            typeAttributes: {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            }
        },
        { label: 'RunId', fieldName: 'runId', type: 'text' },
        { label: 'Seq', fieldName: 'seq', type: 'number' },
        { label: 'Type', fieldName: 'type', type: 'text' },
        { label: 'Level', fieldName: 'level', type: 'text' },
        {
            label: 'Hash',
            fieldName: 'hashShort',
            type: 'text',
            cellAttributes: { title: { fieldName: 'hash' } }
        }
    ];

    get levelOptions() {
        return [
            { label: 'All', value: '' },
            { label: 'DEBUG', value: 'DEBUG' },
            { label: 'INFO', value: 'INFO' },
            { label: 'WARN', value: 'WARN' },
            { label: 'ERROR', value: 'ERROR' }
        ];
    }

    connectedCallback() {
        this.registerErrorListener();
        this.subscribeToChannel();
    }

    disconnectedCallback() {
        this.unsubscribeFromChannel();
    }

    handleRunIdFilter(event) {
        this.runIdFilter = event.target.value || '';
    }

    handleTypeFilter(event) {
        this.typeFilter = event.target.value || '';
    }

    handleLevelFilter(event) {
        this.levelFilter = event.detail.value || '';
    }

    handlePauseToggle(event) {
        this.isPaused = event.target.checked;
        if (this.isPaused) {
            this.unsubscribeFromChannel();
        } else {
            this.subscribeToChannel();
        }
    }

    handleClear() {
        this.events = [];
        this.selectedEvent = null;
    }

    handleRowSelection(event) {
        const rows = event.detail.selectedRows;
        this.selectedEvent = rows && rows.length > 0 ? rows[0] : null;
    }

    get filteredEvents() {
        let filtered = this.events;

        if (this.runIdFilter) {
            const runIdNeedle = this.runIdFilter.toLowerCase();
            filtered = filtered.filter((row) => (row.runId || '').toLowerCase().includes(runIdNeedle));
        }
        if (this.typeFilter) {
            const typeNeedle = this.typeFilter.toLowerCase();
            filtered = filtered.filter((row) => (row.type || '').toLowerCase().includes(typeNeedle));
        }
        if (this.levelFilter) {
            filtered = filtered.filter((row) => row.level === this.levelFilter);
        }

        return filtered;
    }

    get selectedPayloadPretty() {
        if (!this.selectedEvent || !this.selectedEvent.payload) {
            return '';
        }
        try {
            return JSON.stringify(JSON.parse(this.selectedEvent.payload), null, 2);
        } catch (e) {
            return this.selectedEvent.payload;
        }
    }

    subscribeToChannel() {
        if (this.subscription) {
            return;
        }

        const messageCallback = (response) => {
            this.handleEvent(response);
        };

        subscribe(this.channelName, -1, messageCallback)
            .then((response) => {
                this.subscription = response;
            })
            .catch((error) => {
                this.showToast('Subscription failed', this.normalizeError(error), 'error');
            });
    }

    unsubscribeFromChannel() {
        if (!this.subscription) {
            return;
        }
        unsubscribe(this.subscription, () => {
            this.subscription = null;
        });
    }

    registerErrorListener() {
        onError((error) => {
            this.subscription = null;
            this.showToast('EMP API error', this.normalizeError(error), 'error');
        });
    }

    handleEvent(message) {
        if (this.isPaused) {
            return;
        }

        const payload = message && message.data ? message.data.payload : null;
        if (!payload) {
            return;
        }

        const hash = payload.Hash__c || '';
        const record = {
            id: String(message.data.event.replayId),
            runId: payload.RunId__c,
            seq: payload.Seq__c,
            type: payload.Type__c,
            level: payload.Level__c,
            source: payload.Source__c,
            at: payload.At__c,
            ingestedAt: payload.IngestedAt__c,
            prevHash: payload.PrevHash__c,
            hash: hash,
            hashShort: this.truncateHash(hash),
            idempotencyKey: payload.IdempotencyKey__c,
            payload: payload.Payload__c
        };

        const nextEvents = [...this.events, record];
        if (nextEvents.length > MAX_EVENTS) {
            this.events = nextEvents.slice(nextEvents.length - MAX_EVENTS);
        } else {
            this.events = nextEvents;
        }
    }

    truncateHash(hash) {
        if (!hash) {
            return '';
        }
        if (hash.length <= 16) {
            return hash;
        }
        return hash.substring(0, 8) + '...' + hash.substring(hash.length - 8);
    }

    normalizeError(error) {
        if (!error) {
            return 'Unknown error';
        }
        if (typeof error === 'string') {
            return error;
        }
        if (error.message) {
            return error.message;
        }
        return JSON.stringify(error);
    }

    showToast(title, message, variant) {
        this.dispatchEvent(
            new ShowToastEvent({
                title,
                message,
                variant
            })
        );
    }
}

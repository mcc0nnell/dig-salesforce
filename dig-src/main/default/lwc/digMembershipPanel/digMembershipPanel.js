import { LightningElement, track } from 'lwc';
import searchContacts from '@salesforce/apex/DigOps_MembershipController.searchContacts';
import loadPanel from '@salesforce/apex/DigOps_MembershipController.loadPanel';
import createRenewal from '@salesforce/apex/DigOps_MembershipController.createRenewal';
import recompute from '@salesforce/apex/DigOps_MembershipController.recompute';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';

export default class DigMembershipPanel extends LightningElement {
    searchQuery = '';
    searchResults = [];
    selectedContactId;
    selectedContactName;
    panelData;

    renewalLevel = '';
    renewalSource = 'Manual';
    renewalStartDate = this.todayString();
    renewalEndDate = this.addDays(this.renewalStartDate, 365);
    renewalPaidDate;
    renewalPaymentRef;
    renewalNotes;

    searchTimeout;

    termColumns = [
        { label: 'Start Date', fieldName: 'startDate', type: 'date' },
        { label: 'End Date', fieldName: 'endDate', type: 'date' },
        { label: 'Status', fieldName: 'status' },
        { label: 'Level', fieldName: 'level' },
        { label: 'Paid Date', fieldName: 'paidDate', type: 'date' },
        { label: 'Source', fieldName: 'source' },
        { label: 'Payment Ref', fieldName: 'paymentRef' }
    ];

    get isCreateDisabled() {
        return !this.selectedContactId || !this.renewalLevel;
    }

    handleSearchChange(event) {
        this.searchQuery = event.target.value;
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.runSearch();
        }, 300);
    }

    runSearch() {
        if (!this.searchQuery || this.searchQuery.trim().length < 2) {
            this.searchResults = [];
            return;
        }
        searchContacts({ q: this.searchQuery, limitSize: 10 })
            .then((results) => {
                this.searchResults = results;
            })
            .catch((error) => {
                this.showError('Search failed', error);
            });
    }

    handleSelectContact(event) {
        const contactId = event.currentTarget.dataset.id;
        const selected = this.searchResults.find((result) => result.id === contactId);
        this.selectedContactId = contactId;
        this.selectedContactName = selected ? selected.name : undefined;
        this.searchResults = [];
        this.loadPanelData();
    }

    loadPanelData() {
        if (!this.selectedContactId) {
            return;
        }
        loadPanel({ contactId: this.selectedContactId })
            .then((result) => {
                this.panelData = result;
            })
            .catch((error) => {
                this.showError('Load failed', error);
            });
    }

    handleRecompute() {
        recompute({ contactId: this.selectedContactId })
            .then(() => {
                this.showToast('Recomputed', 'Membership summary refreshed', 'success');
                this.loadPanelData();
            })
            .catch((error) => {
                this.showError('Recompute failed', error);
            });
    }

    handleLevelChange(event) {
        this.renewalLevel = event.target.value;
        if (this.renewalStartDate) {
            this.renewalEndDate = this.addDays(this.renewalStartDate, 365);
        }
    }

    handleSourceChange(event) {
        this.renewalSource = event.target.value;
    }

    handleStartDateChange(event) {
        this.renewalStartDate = event.target.value;
        if (!this.renewalEndDate) {
            this.renewalEndDate = this.addDays(this.renewalStartDate, 365);
        }
    }

    handleEndDateChange(event) {
        this.renewalEndDate = event.target.value;
    }

    handlePaidDateChange(event) {
        this.renewalPaidDate = event.target.value;
    }

    handlePaymentRefChange(event) {
        this.renewalPaymentRef = event.target.value;
    }

    handleNotesChange(event) {
        this.renewalNotes = event.target.value;
    }

    handleCreateRenewal() {
        if (this.isCreateDisabled) {
            return;
        }
        const request = {
            contactId: this.selectedContactId,
            level: this.renewalLevel,
            startDate: this.renewalStartDate,
            endDate: this.renewalEndDate,
            source: this.renewalSource,
            paidDate: this.renewalPaidDate || null,
            paymentRef: this.renewalPaymentRef,
            notes: this.renewalNotes
        };
        createRenewal({ req: request })
            .then(() => {
                this.showToast('Renewal created', 'Membership term created', 'success');
                this.loadPanelData();
            })
            .catch((error) => {
                this.showError('Renewal failed', error);
            });
    }

    todayString() {
        return new Date().toISOString().slice(0, 10);
    }

    addDays(dateString, days) {
        if (!dateString) {
            return null;
        }
        const date = new Date(dateString + 'T00:00:00');
        date.setDate(date.getDate() + days);
        return date.toISOString().slice(0, 10);
    }

    showToast(title, message, variant) {
        this.dispatchEvent(new ShowToastEvent({ title, message, variant }));
    }

    showError(title, error) {
        let message = 'Unknown error';
        if (error && error.body && error.body.message) {
            message = error.body.message;
        }
        this.showToast(title, message, 'error');
    }
}

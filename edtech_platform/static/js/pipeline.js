/**
 * Pipeline Status Polling — ExcellStudy
 * Polls the pipeline JSON status endpoint and updates the stepper UI.
 */

class PipelineStatusListener {
  constructor(slug) {
    this.slug = slug;
    this.intervalId = null;
    this.steps = ['schema_check', 'security_scan', 'smoke_test'];
    this.stepLabels = {
      schema_check:  'Schema Validation',
      security_scan: 'Security Scan',
      smoke_test:    'Smoke Test'
    };

    this.init();
  }

  init() {
    this.poll();
    this.intervalId = setInterval(() => this.poll(), 3000);
  }

  poll() {
    fetch(`/api/v1/pipeline/${this.slug}/status/`)
      .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
      })
      .then(data => {
        this.updateUI(data);
      })
      .catch(error => {
        console.error('[Pipeline] Polling error:', error);
      });
  }

  updateUI(data) {
    const status = data.status;

    if (status === 'live') {
      // All steps passed!
      this.steps.forEach(stepId => {
        this.updateStepUI(stepId, 'passed', 'Check passed successfully.');
      });
      this.updateOverallStatus('passed');
      this.showSuccessBanner();
      clearInterval(this.intervalId);
    } else if (status === 'rejected') {
      const reason = data.rejection_reason || 'Validation failed.';
      
      let failedStep = 'schema_check'; // default
      if (reason.toLowerCase().includes('security') || reason.toLowerCase().includes('vulnerability')) {
        failedStep = 'security_scan';
      } else if (reason.toLowerCase().includes('smoke') || reason.toLowerCase().includes('endpoint') || reason.toLowerCase().includes('unreachable') || reason.toLowerCase().includes('test')) {
        failedStep = 'smoke_test';
      }

      let failedFound = false;
      this.steps.forEach(stepId => {
        if (stepId === failedStep) {
          this.updateStepUI(stepId, 'failed', reason);
          failedFound = true;
        } else if (!failedFound) {
          this.updateStepUI(stepId, 'passed', 'Step passed.');
        } else {
          this.updateStepUI(stepId, 'pending', null);
        }
      });

      this.updateOverallStatus('failed');
      this.showFailureBanner(failedStep, reason);
      clearInterval(this.intervalId);
    } else {
      // Pending state: show schema_check running, others pending
      this.updateStepUI('schema_check', 'running', 'Running validation checks...');
      this.updateStepUI('security_scan', 'pending', null);
      this.updateStepUI('smoke_test', 'pending', null);
      this.updateOverallStatus('running');
    }
  }

  updateStepUI(stepId, status, log) {
    const stepEl = document.getElementById(`step-${stepId}`);
    if (!stepEl) return;

    stepEl.classList.remove(
      'stepper__step--pending',
      'stepper__step--running',
      'stepper__step--passed',
      'stepper__step--failed'
    );
    stepEl.classList.add(`stepper__step--${status}`);

    const indicator = document.getElementById(`indicator-${stepId}`);
    if (indicator) {
      indicator.className = 'step-indicator ' + status;
      indicator.innerHTML = '';
      if (status === 'passed') {
        indicator.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8.5L6.5 12L13 4" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      } else if (status === 'failed') {
        indicator.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 3L11 11M11 3L3 11" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>';
      } else if (status === 'running') {
        indicator.innerHTML = '<span class="animate-spin" style="display:inline-block; font-size: 1.25rem;">⟳</span>';
      }
    }

    const stepBody = document.getElementById(`step-${stepId}`);
    if (stepBody) {
      stepBody.style.opacity = (status === 'pending') ? '0.6' : '1';
    }

    if (log) {
      const logPanel = document.getElementById(`log-${stepId}`);
      if (logPanel) logPanel.textContent = log;
    }
  }

  updateOverallStatus(status) {
    const el = document.getElementById('pipeline-overall-status') || document.getElementById('pipeline-status');
    if (!el) return;

    const map = {
      running: { text: 'Running',   cls: 'badge--pending',  emoji: '⏳' },
      passed:  { text: 'Live',      cls: 'badge--live',     emoji: '✅' },
      failed:  { text: 'Rejected',  cls: 'badge--rejected', emoji: '❌' }
    };
    const info = map[status] || map.running;
    el.textContent = `${info.emoji} ${info.text}`;
  }

  showSuccessBanner() {
    const rBanner = document.getElementById('banner-running');
    if (rBanner) rBanner.style.display = 'none';
    const fBanner = document.getElementById('banner-failure');
    if (fBanner) fBanner.style.display = 'none';
    const sBanner = document.getElementById('banner-success');
    if (sBanner) sBanner.style.display = 'flex';
  }

  showFailureBanner(failedStep, reason) {
    const rBanner = document.getElementById('banner-running');
    if (rBanner) rBanner.style.display = 'none';
    const sBanner = document.getElementById('banner-success');
    if (sBanner) sBanner.style.display = 'none';
    const fBanner = document.getElementById('banner-failure');
    if (fBanner) {
      fBanner.style.display = 'flex';
      const label = this.stepLabels[failedStep] || failedStep;
      const stepNameEl = document.getElementById('failed-step-name');
      if (stepNameEl) {
        stepNameEl.innerHTML = `— Failed at <strong>${label}</strong><br/><span style="font-size:0.85rem; font-weight:normal; display:block; margin-top:4px;">${reason}</span>`;
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const jobIdEl = document.getElementById('pipeline-job-id');
  if (jobIdEl) {
    window.pipelineListener = new PipelineStatusListener(jobIdEl.dataset.jobId);
  }
});

/* Shared email → topic dialog. Email stays in memory until the visitor submits
   the genuine Kit form. No address goes to URLs, storage, analytics or events. */
(function () {
  'use strict';
  if (window.MSRASubscriptions) return;
  var topicTags = { 'feline-urinary': '25146776', 'rabbit-gut': '25146778', 'new-research': '25146779' };
  var descriptions = {
    'feline-urinary': 'Guides, research and evidence updates on feline urinary health.',
    'rabbit-gut': 'Research and evidence updates on rabbit digestion.',
    'new-research': 'New MSRA research projects and questions across species.'
  };
  var dialog, dialogEmail, choices = [], returnFocus, status;

  function known(topic) { return Object.prototype.hasOwnProperty.call(topicTags, topic); }
  function queryTopics() {
    var params = new URLSearchParams(window.location.search);
    return params.getAll('topic').concat(params.getAll('topics').join(',').split(',')).filter(known);
  }
  function chosen(input, topics) {
    return topics.some(function (topic) { return input.value === topic || input.value === topicTags[topic]; });
  }
  function updateStatus(message) {
    if (status) status.textContent = message || '';
    choices.forEach(function (input) { input.removeAttribute('aria-invalid'); });
  }
  function openDialog(trigger, email, topic) {
    if (!dialog || typeof dialog.showModal !== 'function') return false;
    if (dialog.open) return true;
    returnFocus = trigger;
    if (dialogEmail) dialogEmail.value = email ? email.value.trim() : '';
    var suggestions = known(topic) ? [topic] : queryTopics();
    choices.forEach(function (input) { input.checked = chosen(input, suggestions); });
    updateStatus(dialog.dataset.runtimeBlocked === 'true' ? 'Email signup is unavailable. No subscription has been confirmed.' : '');
    dialog.showModal();
    document.body.classList.add('subscription-dialog-open');
    if (dialogEmail && !dialogEmail.value) dialogEmail.focus();
    else if (choices[0]) choices[0].focus();
    else dialog.querySelector('[data-subscription-close]').focus();
    return true;
  }
  function initInline(section) {
    var form = section.querySelector('form'), mapping;
    try { mapping = JSON.parse(section.dataset.topicTags || '{}'); } catch (error) { mapping = {}; }
    var keys = Object.keys(topicTags);
    var inputs = form ? Array.from(form.querySelectorAll('input[name="tags[]"]')) : [];
    var email = form && form.querySelector('input[name="email_address"][type="email"][required]');
    var valid = section.dataset.signupReady === 'true' && section.querySelectorAll('form').length === 1 &&
      section.dataset.formId === '10113119' && section.dataset.formUid === '924e9b0702' &&
      section.dataset.formAction === 'https://app.kit.com/forms/10113119/subscriptions' &&
      form && form.getAttribute('action') === section.dataset.formAction && String(form.getAttribute('method') || '').toLowerCase() === 'post' &&
      form.dataset.svForm === '10113119' && form.dataset.uid === '924e9b0702' && email &&
      mapping && typeof mapping === 'object' && !Array.isArray(mapping) && Object.keys(mapping).length === keys.length && inputs.length === keys.length && keys.every(function (topic) {
        return mapping[topic] === topicTags[topic] && inputs.filter(function (input) {
          return input.type === 'checkbox' && input.value === topicTags[topic];
        }).length === 1;
      });
    if (!valid) {
      dialog.dataset.runtimeBlocked = 'true';
      if (form) {
        form.removeAttribute('action');
        form.querySelectorAll('input,button,select,textarea').forEach(function (control) { control.disabled = true; });
        form.addEventListener('submit', function (event) { event.preventDefault(); event.stopImmediatePropagation(); }, true);
      }
      updateStatus('Email signup is unavailable. No subscription has been confirmed.');
      return;
    }
    dialogEmail = email;
    email.setAttribute('autocomplete', 'email');
    email.setAttribute('aria-label', 'Your email address');
    choices = inputs;
    keys.forEach(function (topic) {
      var input = inputs.filter(function (item) { return item.value === topicTags[topic]; })[0];
      var label = form.querySelector('label[for="' + input.id + '"]');
      if (label) {
        var description = document.createElement('span');
        description.className = 'subscription-dialog__topic-description';
        description.textContent = descriptions[topic];
        label.appendChild(description);
      }
    });
    var submitText = form.querySelector('.formkit-submit > span');
    if (submitText) submitText.textContent = 'Receive research updates';
    form.addEventListener('submit', function (event) {
      if (!dialog.open || !inputs.some(function (input) { return input.checked; })) {
        event.preventDefault();
        event.stopImmediatePropagation();
        updateStatus('Choose at least one topic before subscribing.');
        inputs[0].setAttribute('aria-invalid', 'true');
        inputs[0].focus();
      }
      // Kit handles its actual response. A submit is never reported as a signup.
    }, true);
  }
  function init() {
    if (dialog) return;
    dialog = document.querySelector('[data-subscription-modal]');
    if (!dialog) return;
    status = dialog.querySelector('[data-subscription-selection]');
    var inline = dialog.querySelector('[data-subscription-inline]');
    if (inline) initInline(inline);
    else {
      dialogEmail = dialog.querySelector('[data-subscription-email]');
      choices = Array.from(dialog.querySelectorAll('[data-subscription-topic]'));
    }
    dialog.querySelector('[data-subscription-close]').addEventListener('click', function () { dialog.close(); });
    dialog.addEventListener('keydown', function (event) {
      if (event.key !== 'Tab') return;
      var focusable = Array.from(dialog.querySelectorAll('a[href],button,input,select,textarea,[tabindex]')).filter(function (control) {
        return !control.disabled && control.tabIndex >= 0 && control.getClientRects().length;
      });
      if (!focusable.length) return;
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog)) {
        event.preventDefault(); first.focus();
      }
    });
    dialog.addEventListener('click', function (event) {
      if (event.target !== dialog) return;
      var bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
    dialog.addEventListener('close', function () {
      document.body.classList.remove('subscription-dialog-open');
      if (dialogEmail) dialogEmail.value = '';
      choices.forEach(function (input) { input.checked = false; });
      updateStatus();
      if (returnFocus && returnFocus.isConnected) returnFocus.focus();
    });
    choices.forEach(function (input) { input.addEventListener('change', function () { updateStatus(); }); });
    var preview = dialog.querySelector('[data-subscription-preview-form]');
    if (preview) preview.addEventListener('submit', function (event) { event.preventDefault(); });
    var handoff = dialog.querySelector('[data-subscription-link]');
    if (handoff) handoff.addEventListener('click', function (event) {
      if (!choices.some(function (input) { return input.checked; })) { event.preventDefault(); choices[0].focus(); }
    });
    // Delegation also covers research cards inserted after the page has loaded.
    document.addEventListener('submit', function (event) {
      var form = event.target.closest('[data-subscription-entry]');
      if (!form) return;
      var email = form.querySelector('[data-subscription-entry-email]');
      if (!email || !email.reportValidity()) { event.preventDefault(); return; }
      if (openDialog(event.submitter || email, email, form.dataset.topic || '')) event.preventDefault();
    });
    document.addEventListener('click', function (event) {
      var link = event.target.closest('[data-subscription-open]');
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button) return;
      if (openDialog(link, null, link.dataset.topic || '')) event.preventDefault();
    });
  }
  window.MSRASubscriptions = { init: init };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

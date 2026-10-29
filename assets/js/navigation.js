/* Shared English and localized navigation. No requests or content translation. */
(function () {
  'use strict';
  // Project lists open only through an explicit click or key, never hover or focus.
  var nav = document.querySelector('header[data-msra-nav], header.nav');
  var navToggle = document.getElementById('nav-toggle');
  var navLinks = document.getElementById('primary-nav-links');
  var closeNavigation = function () {};
  if (nav && navToggle && navLinks && window.matchMedia) {
    var breakpoint = Number(nav.getAttribute('data-nav-breakpoint')) || 760;
    var smallNav = window.matchMedia('(max-width: ' + breakpoint + 'px)');
    var disclosures = Array.from(navLinks.querySelectorAll('[data-nav-disclosure]')).map(function (node) {
      var button = node.querySelector('[data-nav-disclosure-toggle]');
      var panel = button && document.getElementById(button.getAttribute('aria-controls'));
      return button && panel && node.contains(panel) ? { node: node, button: button, panel: panel } : null;
    }).filter(Boolean);
    disclosures.forEach(function (item) {
      item.button.hidden = false;
    });
    function closeBranch(item) {
      item.panel.hidden = true;
      item.button.setAttribute('aria-expanded', 'false');
    }
    function closeTopics() { disclosures.forEach(closeBranch); }
    function openBranch(item) {
      disclosures.forEach(function (candidate) {
        if (candidate !== item) closeBranch(candidate);
      });
      item.panel.hidden = false;
      item.button.setAttribute('aria-expanded', 'true');
    }
    function focusNav(control) {
      control.focus();
    }
    function setNav(open, restoreFocus) {
      if (!open) closeTopics();
      navLinks.hidden = smallNav.matches && !open;
      navToggle.setAttribute('aria-expanded', String(smallNav.matches && open));
      if (restoreFocus) focusNav(navToggle);
    }
    function syncNav() {
      var active = document.activeElement;
      var wasInLinks = navLinks.contains(active);
      var activeBranch = disclosures.filter(function (item) { return item.panel.contains(active); })[0];
      setNav(false, false);
      if (smallNav.matches && wasInLinks) focusNav(navToggle);
      else if (!smallNav.matches && active === navToggle) focusNav(navLinks.querySelector('a[href]'));
      else if (activeBranch) focusNav(activeBranch.button);
    }
    closeNavigation = function () { setNav(false, false); };
    nav.setAttribute('data-nav-ready', 'true');
    navToggle.hidden = false;
    syncNav();
    navToggle.addEventListener('click', function () { setNav(navLinks.hidden, false); });
    disclosures.forEach(function (item) {
      item.button.addEventListener('click', function () {
        if (item.panel.hidden) openBranch(item);
        else closeBranch(item);
      });
    });
    document.addEventListener('pointerdown', function (event) {
      if (!event.target.closest('.primary-nav')) setNav(false, false);
    }, true);
    navLinks.addEventListener('focusout', function () {
      setTimeout(function () {
        disclosures.forEach(function (item) {
          if (!item.node.contains(document.activeElement)) closeBranch(item);
        });
        if (smallNav.matches && !nav.querySelector('.primary-nav').contains(document.activeElement)) setNav(false, false);
      }, 0);
    });
    navLinks.addEventListener('click', function (event) {
      if (event.target.closest('a')) setNav(false, false);
    });
    navLinks.addEventListener('keydown', function (event) {
      if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
      var row = event.target.closest('.nav-row');
      var item = disclosures.filter(function (candidate) { return row && row.contains(candidate.button); })[0];
      if (!item) return;
      openBranch(item);
      var controls = Array.from(item.panel.querySelectorAll('a[href],button')).filter(function (control) {
        return !control.hidden && !control.closest('[hidden]');
      });
      if (controls.length) {
        event.preventDefault();
        controls[event.key === 'ArrowDown' ? 0 : controls.length - 1].focus();
      }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape') return;
      var open = disclosures.filter(function (item) { return !item.panel.hidden; });
      var containing = open.filter(function (item) { return item.node.contains(event.target); });
      var current = (containing.length ? containing : open).slice(-1)[0];
      if (current) {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeBranch(current);
        focusNav(current.button);
      } else if (smallNav.matches && !navLinks.hidden) {
        event.preventDefault();
        event.stopImmediatePropagation();
        setNav(false, true);
      }
    });
    window.addEventListener('resize', syncNav);
    if (smallNav.addEventListener) smallNav.addEventListener('change', syncNav);
    else smallNav.addListener(syncNav);
  }

  // The native language disclosure works without JS. Enhancement closes it
  // when focus, pointer activity, or Escape moves back to ordinary navigation.
  if (nav) {
    var editions = Array.from(nav.querySelectorAll('details.edition-menu'));
    function closeEditions(except) {
      editions.forEach(function (details) { if (details !== except) details.open = false; });
    }
    editions.forEach(function (details) {
      var more = details.querySelector('[data-language-more]');
      details.addEventListener('toggle', function () {
        if (!details.open) {
          if (more) more.open = false;
          return;
        }
        closeEditions(details);
        closeNavigation();
      });
      details.addEventListener('focusout', function () {
        setTimeout(function () {
          if (!details.contains(document.activeElement)) details.open = false;
        }, 0);
      });
      details.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape' || !details.open) return;
        event.preventDefault();
        event.stopPropagation();
        if (more && more.open && more.contains(event.target)) {
          more.open = false;
          more.querySelector('summary').focus();
          return;
        }
        details.open = false;
        details.querySelector('summary').focus();
      });
    });
    document.addEventListener('pointerdown', function (event) {
      editions.forEach(function (details) {
        if (!details.contains(event.target)) details.open = false;
      });
    }, true);
    window.addEventListener('resize', function () {
      editions.forEach(function (details) {
        var restoreFocus = details.open && details.contains(document.activeElement);
        details.open = false;
        if (restoreFocus) details.querySelector('summary').focus();
      });
    });
  }
})();

/* Voice input — auto-bind mic button to text inputs/textarea, vi-VN speech-to-text.
 * Pure vanilla JS, no deps. Uses Web Speech API.
 * Supported: Chrome, Edge, Safari 14.1+. Firefox desktop: graceful exit.
 */
(function () {
  'use strict';

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    if (window.console) {
      console.info('Voice input disabled: Web Speech API not supported (use Chrome/Edge)');
    }
    return;
  }

  var SKIP_TYPES = {
    password: 1, email: 1, number: 1, date: 1, tel: 1,
    hidden: 1, url: 1, time: 1, 'datetime-local': 1
  };

  function isEligible(input) {
    if (!input) return false;
    if (!(input instanceof HTMLInputElement) && !(input instanceof HTMLTextAreaElement)) return false;
    if (input instanceof HTMLInputElement && SKIP_TYPES[input.type]) return false;
    if (input.disabled || input.readOnly) return false;
    if (input.dataset.voiceBound === '1') return false;
    if (input.closest('.admin')) return false;
    if (input.closest('template')) return false;
    return true;
  }

  function createMicBtn(input) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'voice-mic-btn';
    btn.innerHTML = '🎤';
    btn.title = 'Nhập bằng giọng nói (vi)';
    btn.setAttribute('aria-label', 'Nhập bằng giọng nói');
    btn.style.cssText = [
      'border:none', 'background:transparent', 'cursor:pointer',
      'padding:0 4px', 'font-size:14px', 'opacity:0.5',
      'vertical-align:middle', 'display:inline-block'
    ].join(';');
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      toggle(input, btn);
    });

    if (input.parentNode) {
      if (input.nextSibling) {
        input.parentNode.insertBefore(btn, input.nextSibling);
      } else {
        input.parentNode.appendChild(btn);
      }
    }
    input.dataset.voiceBound = '1';
  }

  function toggle(input, btn) {
    if (input.dataset.listening === '1') {
      try {
        input._voiceRec && input._voiceRec.stop();
      } catch (e) { /* ignore */ }
    } else {
      start(input, btn);
    }
  }

  function start(input, btn) {
    var rec = new SR();
    rec.lang = 'vi-VN';
    rec.interimResults = true;
    rec.continuous = false;
    var original = input.value || '';
    var finalText = '';
    if (original && !/\s$/.test(original)) finalText = ' ';

    rec.onresult = function (e) {
      var interim = '';
      for (var i = e.resultIndex; i < e.results.length; i++) {
        var r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript + ' ';
        else interim += r[0].transcript;
      }
      input.value = original + finalText + interim;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    };

    rec.onerror = function (e) {
      var msg = 'Lỗi nhận diện giọng nói';
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        msg = 'Cấp quyền mic trong browser để dùng voice input';
      } else if (e.error === 'network') {
        msg = 'Lỗi mạng khi nhận diện giọng nói';
      } else if (e.error) {
        msg += ': ' + e.error;
      }
      toast(msg);
      resetButton(input, btn);
    };

    rec.onend = function () {
      resetButton(input, btn);
      input._voiceRec = null;
    };

    try {
      rec.start();
      input._voiceRec = rec;
      btn.innerHTML = '⏹';
      btn.style.opacity = '1';
      btn.title = 'Đang nghe — click để dừng';
      input.dataset.listening = '1';
    } catch (e) {
      toast('Không truy cập được mic: ' + (e.message || e));
    }
  }

  function resetButton(input, btn) {
    btn.innerHTML = '🎤';
    btn.style.opacity = '0.5';
    btn.title = 'Nhập bằng giọng nói (vi)';
    input.dataset.listening = '0';
  }

  function toast(msg) {
    var el = document.createElement('div');
    el.textContent = msg;
    el.style.cssText = [
      'position:fixed', 'bottom:20px', 'left:50%', 'transform:translateX(-50%)',
      'background:#dc3545', 'color:white', 'padding:10px 18px',
      'border-radius:8px', 'z-index:9999', 'font-size:14px',
      'box-shadow:0 4px 12px rgba(0,0,0,0.2)', 'max-width:90vw'
    ].join(';');
    document.body.appendChild(el);
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 3000);
  }

  function scan(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll('input, textarea');
    for (var i = 0; i < nodes.length; i++) {
      if (isEligible(nodes[i])) createMicBtn(nodes[i]);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { scan(); });
  } else {
    scan();
  }

  var obs = new MutationObserver(function (muts) {
    for (var i = 0; i < muts.length; i++) {
      var m = muts[i];
      for (var j = 0; j < m.addedNodes.length; j++) {
        var node = m.addedNodes[j];
        if (node.nodeType !== 1) continue;
        if (isEligible(node)) createMicBtn(node);
        if (node.querySelectorAll) {
          var nested = node.querySelectorAll('input, textarea');
          for (var k = 0; k < nested.length; k++) {
            if (isEligible(nested[k])) createMicBtn(nested[k]);
          }
        }
      }
    }
  });
  obs.observe(document.body, { childList: true, subtree: true });
})();

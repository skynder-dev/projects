// ==UserScript==
// @name         GoDog
// @name:en      GoDog
// @name:ru      GoDog
// @namespace    GoDog.constitution
// @version      7.0.6
// @description  GoDog for ChatGPT: GO, AUTO, NEW, STOP. Local updates, original UI.
// @match        https://chatgpt.com/*
// @run-at       document-idle
// @noframes
// @grant        none
// @updateURL    http://127.0.0.1:43129/godog.meta.js
// @downloadURL  http://127.0.0.1:43129/godog.user.js
// ==/UserScript==

(() => {
  'use strict';
  // Keep namespace and localhost update URLs unchanged. Tampermonkey upgrades the installed script from its existing downloadURL, updating the visible name.
  // LOCAL ONLY. No fetch, XMLHttpRequest, GM_xmlhttpRequest, WebSocket, heartbeat or cloud endpoint.
  // Direct controls: GO -> native submit, STOP -> local AUTO off,
  // NEW -> same-tab native new chat with local handoff, AUTO -> event-driven next GO.
  const VERSION = '7.0.6';
  const STATE_KEY = 'godog-pc-local-v7-session';
  const NEW_KEY = 'godog-pc-local-v7-handoff';
  const VERSION_KEY = 'godog-pc-local-v7-version-seen';
  const DRAFT_KEY = 'godog-pc-local-v7-saved-draft';
  if (window.top !== window.self) return;
  // DO NOT seize old GoDog's panel. Disable the old Tampermonkey script first.
  if (document.getElementById('chatgpt-go-watchdog')) {
    console.warn('[GoDog Local] Another GoDog owns the UI. Disable the legacy userscript.');
    return;
  }
  const safeStorage = {
    get(k) { try { return sessionStorage.getItem(k); } catch (_) { return null; } },
    set(k,v) { try { sessionStorage.setItem(k,v); } catch (_) {} },
    del(k) { try { sessionStorage.removeItem(k); } catch (_) {} }
  };
  let restored = {};
  try { restored = JSON.parse(safeStorage.get(STATE_KEY) || '{}') || {}; } catch (_) {}
  let auto = restored.auto === true;
  let awaitReply = restored.awaitReply === true;
  let busySeen = restored.busySeen === true;
  let lastAssistantSignature = String(restored.assistant || '');
  let ownInput = false;
  let watching = false;
  let newHandoff = null;
  try { newHandoff = JSON.parse(safeStorage.get(NEW_KEY) || 'null'); } catch (_) {}
  let pendingAck = null;
  const root = document.createElement('div');
  root.id = 'chatgpt-go-watchdog';
  root.removeAttribute('title');
  root.innerHTML = "\n    <div class=\"cg-identity\"><span class=\"cg-version\"></span><span class=\"cg-project\"></span></div>\n    <span class=\"cg-status\"></span>\n    <div class=\"cg-update-notice\" role=\"status\" aria-live=\"polite\" aria-hidden=\"true\">\n      <div class=\"cg-update-copy\">\n        <span class=\"cg-update-kicker\">UPDATED</span>\n        <strong class=\"cg-update-version\"></strong>\n        <span class=\"cg-update-time\"></span>\n      </div>\n      <button class=\"cg-update-dismiss\" type=\"button\" title=\"Dismiss update notice\">OK</button>\n    </div>\n    <div class=\"cg-actions\">\n      <span class=\"cg-timer\" data-mode=\"idle\" title=\"GoDog timer\">--:--</span>\n      <button class=\"cg-auto\" title=\"Continuous mode\">AUTO</button>\n      <button class=\"cg-new\" title=\"Save pre_handoff, open the successor chat, and continue with AUTO ON\">NEW</button>\n      <button class=\"cg-stop\" title=\"Pause AUTO in this chat; resuming continues with GO, without restore/bootstrap\">STOP</button>\n      <button class=\"cg-go\" title=\"Send a new GO turn\">GO</button>\n    </div>\n  ";
  const style = document.createElement('style');
  style.textContent = "\n    #chatgpt-go-watchdog {\n      position: fixed;\n      z-index: 2147483647;\n      display: flex;\n      flex-direction: column;\n      gap: 5px;\n      align-items: stretch;\n      width: 58px;\n      padding: 6px;\n      border-radius: 12px;\n      background: rgba(18,18,18,.92);\n      box-shadow: 0 8px 30px rgba(0,0,0,.35);\n      user-select: none;\n      font: 11px/1.15 system-ui, -apple-system, Segoe UI, sans-serif;\n      backdrop-filter: blur(10px);\n    }\n    #chatgpt-go-watchdog button {\n      width: 100%;\n      min-width: 0;\n      border: 1px solid rgba(255,255,255,.16);\n      border-radius: 8px;\n      padding: 7px 3px;\n      background: #242424;\n      color: #fff;\n      cursor: pointer;\n      font-weight: 700;\n    }\n    #chatgpt-go-watchdog button:hover { background: #303030; }\n    #chatgpt-go-watchdog .cg-update-notice {\n      position: absolute;\n      left: 8px;\n      bottom: calc(100% + 8px);\n      min-width: 268px;\n      max-width: min(430px, calc(100vw - 32px));\n      display: none;\n      align-items: center;\n      gap: 10px;\n      padding: 10px 10px 10px 12px;\n      box-sizing: border-box;\n      border: 1px solid rgba(244,166,76,.72);\n      border-radius: 11px;\n      background: rgba(38,31,23,.97);\n      color: rgba(255,248,238,.97);\n      box-shadow: 0 8px 30px rgba(0,0,0,.38), 0 0 22px rgba(244,154,56,.23);\n      pointer-events: auto;\n      z-index: 4;\n    }\n    #chatgpt-go-watchdog[data-version-notice=\"show\"] .cg-update-notice {\n      display: flex;\n      animation: cg-version-notice-pop .24s ease-out, cg-version-notice-glow 1.6s ease-in-out 2;\n    }\n    #chatgpt-go-watchdog[data-version-notice=\"show\"] .cg-version {\n      border-color: rgba(244,166,76,.78) !important;\n      box-shadow: 0 0 12px rgba(244,154,56,.32) !important;\n      color: rgba(255,238,211,.98) !important;\n    }\n    #chatgpt-go-watchdog .cg-update-copy {\n      display: grid;\n      grid-template-columns: auto 1fr;\n      grid-template-areas:\n        \"kicker version\"\n        \"time time\";\n      align-items: center;\n      gap: 3px 7px;\n      min-width: 0;\n      flex: 1 1 auto;\n    }\n    #chatgpt-go-watchdog .cg-update-kicker {\n      grid-area: kicker;\n      font-size: 8px;\n      line-height: 1;\n      font-weight: 800;\n      letter-spacing: .08em;\n      color: rgba(255,187,105,.95);\n    }\n    #chatgpt-go-watchdog .cg-update-version {\n      grid-area: version;\n      min-width: 0;\n      font-size: 12px;\n      line-height: 1.1;\n      font-weight: 800;\n      overflow: hidden;\n      text-overflow: ellipsis;\n      white-space: nowrap;\n    }\n    #chatgpt-go-watchdog .cg-update-time {\n      grid-area: time;\n      font-size: 9px;\n      line-height: 1.2;\n      color: rgba(232,221,205,.76);\n      white-space: nowrap;\n      overflow: hidden;\n      text-overflow: ellipsis;\n    }\n    #chatgpt-go-watchdog .cg-update-dismiss {\n      width: 38px !important;\n      min-width: 38px !important;\n      height: 27px !important;\n      flex: 0 0 38px !important;\n      padding: 0 !important;\n      border-color: rgba(244,166,76,.42) !important;\n      background: rgba(244,154,56,.16) !important;\n      color: rgba(255,239,217,.94) !important;\n      font-size: 9px !important;\n    }\n    @keyframes cg-version-notice-pop {\n      from { opacity: 0; transform: translateY(5px) scale(.985); }\n      to { opacity: 1; transform: translateY(0) scale(1); }\n    }\n    @keyframes cg-version-notice-glow {\n      0%,100% { box-shadow: 0 8px 30px rgba(0,0,0,.38), 0 0 16px rgba(244,154,56,.18); }\n      50% { box-shadow: 0 8px 30px rgba(0,0,0,.38), 0 0 28px rgba(244,154,56,.34); }\n    }\n    #chatgpt-go-watchdog .cg-auto.on {\n      outline: 2px solid rgba(255,255,255,.55);\n      background: #3a3a3a;\n    }\n    #chatgpt-go-watchdog .cg-status {\n      color: #cfcfcf;\n      padding: 2px 1px 0;\n      white-space: nowrap;\n      text-align: center;\n      overflow: hidden;\n      text-overflow: ellipsis;\n      font-size: 9px;\n      line-height: 1.15;\n    }\n    #chatgpt-go-watchdog .cg-status:empty {\n      display: none;\n    }\n\n    /* v4.42.41 composer-aligned dock. GO is intentionally rightmost, roughly under ChatGPT Send. */\n    #chatgpt-go-watchdog {\n      position: fixed !important;\n      left: 24px !important;\n      right: 24px !important;\n      bottom: 0 !important;\n      top: auto !important;\n      width: auto !important;\n      height: 34px !important;\n      box-sizing: border-box;\n      flex-direction: row !important;\n      align-items: center !important;\n      justify-content: flex-start;\n      gap: 5px !important;\n      padding: 3px 4px !important;\n      border-radius: 0 !important;\n      border: 0 !important;\n      border-top: 1px solid rgba(128,178,214,.24) !important;\n      background: rgba(18,20,23,.93) !important;\n      box-shadow: 0 -1px 8px rgba(82,151,205,.15) !important;\n      backdrop-filter: blur(8px) saturate(.95);\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog::after {\n      content: '';\n      position: absolute;\n      left: 0;\n      right: 0;\n      top: -2px;\n      height: 2px;\n      background: linear-gradient(90deg, rgba(91,145,181,.12), rgba(96,164,214,.58) 34%, rgba(116,180,220,.66) 50%, rgba(96,164,214,.58) 66%, rgba(91,145,181,.12));\n      box-shadow: 0 -1px 8px rgba(86,157,211,.28), 0 1px 6px rgba(86,157,211,.18);\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog::before {\n      content: attr(data-meta);\n      order: 0;\n      flex: 0 1 150px;\n      min-width: 78px;\n      max-width: 150px;\n      overflow: hidden;\n      text-overflow: ellipsis;\n      white-space: nowrap;\n      color: rgba(226,229,232,.76);\n      font-size: 9px;\n      letter-spacing: .01em;\n      padding-left: 2px;\n    }\n    #chatgpt-go-watchdog .cg-status {\n      order: 1;\n      flex: 1 1 auto;\n      min-width: 0;\n      padding: 0 7px !important;\n      text-align: right !important;\n      color: rgba(226,229,232,.72) !important;\n      font-size: 9px !important;\n      line-height: 1 !important;\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog button {\n      pointer-events: auto;\n      flex: 0 0 60px;\n      width: 60px !important;\n      height: 27px;\n      padding: 0 8px !important;\n      border-radius: 8px !important;\n      border: 1px solid rgba(255,255,255,.18) !important;\n      background: rgba(255,255,255,.10) !important;\n      color: rgba(247,248,249,.90) !important;\n      box-shadow: none !important;\n      font-size: 9px;\n      line-height: 1;\n    }\n    #chatgpt-go-watchdog button:hover {\n      filter: brightness(1.18);\n      color: #fff !important;\n    }\n    #chatgpt-go-watchdog .cg-auto {\n      order: 2;\n      background: rgba(72,112,79,.42) !important;\n      border-color: rgba(111,151,117,.46) !important;\n    }\n    #chatgpt-go-watchdog .cg-auto.on {\n      outline: none !important;\n      background: rgba(72,126,82,.62) !important;\n      border-color: rgba(127,174,134,.68) !important;\n      color: rgba(250,255,250,.96) !important;\n    }\n    #chatgpt-go-watchdog .cg-new {\n      order: 3;\n      background: rgba(145,103,54,.48) !important;\n      border-color: rgba(181,134,75,.52) !important;\n    }\n    #chatgpt-go-watchdog .cg-stop {\n      order: 4;\n      background: rgba(132,69,74,.48) !important;\n      border-color: rgba(170,94,100,.54) !important;\n    }\n    #chatgpt-go-watchdog .cg-go {\n      order: 5;\n      flex-basis: 66px;\n      width: 66px !important;\n      background: rgba(60,105,146,.56) !important;\n      border-color: rgba(99,148,187,.62) !important;\n      color: rgba(250,253,255,.96) !important;\n    }\n    @media (max-width: 430px) {\n      #chatgpt-go-watchdog { gap: 4px !important; padding-inline: 2px !important; }\n      #chatgpt-go-watchdog::after {\n      content: '';\n      position: absolute;\n      left: 0;\n      right: 0;\n      top: -2px;\n      height: 2px;\n      background: linear-gradient(90deg, rgba(91,145,181,.12), rgba(96,164,214,.58) 34%, rgba(116,180,220,.66) 50%, rgba(96,164,214,.58) 66%, rgba(91,145,181,.12));\n      box-shadow: 0 -1px 8px rgba(86,157,211,.28), 0 1px 6px rgba(86,157,211,.18);\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog::before { flex-basis: 82px; min-width: 68px; max-width: 82px; font-size: 8px; }\n      #chatgpt-go-watchdog .cg-status { font-size: 8px !important; padding-inline: 2px !important; }\n      #chatgpt-go-watchdog button { flex-basis: 48px; width: 48px !important; padding-inline: 4px !important; font-size: 8px; }\n      #chatgpt-go-watchdog .cg-go { flex-basis: 54px; width: 54px !important; }\n    }\n\n    /* v4.42.42: grid dock. Version left, passive status centered, controls pinned to the right with GO nearest Send. */\n    #chatgpt-go-watchdog {\n      display: grid !important;\n      grid-template-columns: minmax(128px, 1fr) minmax(110px, 1fr) 60px 60px 60px 70px;\n      column-gap: 6px !important;\n      align-items: center !important;\n      height: 36px !important;\n      bottom: 3px !important;\n      padding: 4px 6px !important;\n      border-radius: 12px !important;\n      border: 1px solid rgba(255,255,255,.10) !important;\n      border-top-color: rgba(126,183,221,.30) !important;\n      background: rgba(22,24,27,.96) !important;\n      box-shadow: 0 2px 12px rgba(0,0,0,.24), 0 -1px 7px rgba(88,158,207,.14) !important;\n    }\n    #chatgpt-go-watchdog::after {\n      left: 12px !important;\n      right: 12px !important;\n      top: -2px !important;\n      height: 2px !important;\n      border-radius: 999px;\n      background: linear-gradient(90deg, rgba(89,146,185,.10), rgba(91,168,220,.56) 30%, rgba(126,194,235,.72) 50%, rgba(91,168,220,.56) 70%, rgba(89,146,185,.10)) !important;\n      box-shadow: 0 -1px 7px rgba(91,168,220,.27), 0 1px 5px rgba(91,168,220,.18) !important;\n    }\n    #chatgpt-go-watchdog::before {\n      grid-column: 1;\n      order: initial !important;\n      justify-self: start;\n      align-self: center;\n      width: auto;\n      max-width: 100%;\n      min-width: 0;\n      box-sizing: border-box;\n      padding: 5px 9px !important;\n      border: 1px solid rgba(255,255,255,.10);\n      border-radius: 8px;\n      background: rgba(255,255,255,.055);\n      color: rgba(235,238,241,.82) !important;\n      font-size: 9px !important;\n      line-height: 1;\n    }\n    #chatgpt-go-watchdog .cg-status {\n      display: flex !important;\n      grid-column: 2;\n      order: initial !important;\n      justify-self: center;\n      align-items: center;\n      justify-content: center;\n      width: min(100%, 210px);\n      height: 23px;\n      box-sizing: border-box;\n      padding: 0 10px !important;\n      border: 1px solid rgba(126,155,177,.16);\n      border-radius: 999px;\n      background: rgba(104,128,146,.11);\n      color: rgba(229,235,239,.84) !important;\n      font-size: 9px !important;\n      font-weight: 650;\n      letter-spacing: .035em;\n      text-transform: uppercase;\n      text-align: center !important;\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog .cg-status::before {\n      content: '';\n      flex: 0 0 5px;\n      width: 5px;\n      height: 5px;\n      margin-right: 6px;\n      border-radius: 50%;\n      background: rgba(113,176,216,.78);\n      box-shadow: 0 0 5px rgba(113,176,216,.30);\n    }\n    #chatgpt-go-watchdog .cg-auto { grid-column: 3; }\n    #chatgpt-go-watchdog .cg-new  { grid-column: 4; }\n    #chatgpt-go-watchdog .cg-stop { grid-column: 5; }\n    #chatgpt-go-watchdog .cg-go   { grid-column: 6; }\n    #chatgpt-go-watchdog button {\n      order: initial !important;\n      width: 100% !important;\n      min-width: 0 !important;\n      height: 27px !important;\n      padding: 0 8px !important;\n      font-size: 9px !important;\n    }\n    #chatgpt-go-watchdog .cg-go {\n      width: 100% !important;\n      background: rgba(60,112,157,.62) !important;\n      border-color: rgba(105,160,203,.70) !important;\n    }\n    #chatgpt-go-watchdog .cg-auto {\n      background: rgba(74,122,82,.46) !important;\n      border-color: rgba(117,161,123,.50) !important;\n    }\n    #chatgpt-go-watchdog .cg-auto.on { background: rgba(75,138,88,.68) !important; }\n    #chatgpt-go-watchdog .cg-new {\n      background: rgba(151,108,56,.52) !important;\n      border-color: rgba(188,142,81,.58) !important;\n    }\n    #chatgpt-go-watchdog .cg-stop {\n      background: rgba(139,72,78,.52) !important;\n      border-color: rgba(179,98,105,.60) !important;\n    }\n    @media (max-width: 620px) {\n      #chatgpt-go-watchdog {\n        grid-template-columns: minmax(92px, 1fr) minmax(72px, 1fr) 54px 54px 54px 60px;\n        column-gap: 4px !important;\n      }\n      #chatgpt-go-watchdog::before { padding-inline: 7px !important; font-size: 8px !important; }\n      #chatgpt-go-watchdog .cg-status { font-size: 8px !important; padding-inline: 6px !important; }\n    }\n    @media (max-width: 430px) {\n      #chatgpt-go-watchdog {\n        grid-template-columns: minmax(64px, .85fr) minmax(48px, 1fr) 39px 39px 39px 45px;\n        column-gap: 3px !important;\n        padding-inline: 4px !important;\n      }\n      #chatgpt-go-watchdog::before { padding-inline: 5px !important; font-size: 7.5px !important; }\n      #chatgpt-go-watchdog .cg-status { font-size: 7.5px !important; padding-inline: 4px !important; }\n      #chatgpt-go-watchdog button { padding-inline: 2px !important; font-size: 8px !important; }\n    }\n\n    /* v4.42.43: three independent dock zones. Meta left, passive status center, controls right. */\n    #chatgpt-go-watchdog {\n      display: grid !important;\n      grid-template-columns: minmax(112px, max-content) minmax(72px, 1fr) max-content !important;\n      column-gap: 8px !important;\n      align-items: center !important;\n      height: 33px !important;\n      bottom: 3px !important;\n      padding: 2px 7px !important;\n      border-radius: 13px !important;\n      overflow: visible;\n    }\n    #chatgpt-go-watchdog::before { content: none !important; display: none !important; }\n    #chatgpt-go-watchdog .cg-meta {\n      grid-column: 1;\n      justify-self: start;\n      min-width: 0;\n      max-width: 190px;\n      box-sizing: border-box;\n      overflow: hidden;\n      text-overflow: ellipsis;\n      white-space: nowrap;\n      padding: 6px 10px;\n      border-radius: 9px;\n      border: 1px solid rgba(255,255,255,.12);\n      background: rgba(255,255,255,.07);\n      color: rgba(238,241,244,.84);\n      font-size: 9px;\n      line-height: 1;\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog .cg-status {\n      grid-column: 2 !important;\n      justify-self: center !important;\n      width: min(100%, 188px) !important;\n      height: 21px !important;\n      box-sizing: border-box;\n      display: flex !important;\n      align-items: center;\n      justify-content: center;\n      gap: 7px;\n      padding: 0 10px !important;\n      border-radius: 999px !important;\n      border: 1px solid rgba(130,153,171,.20) !important;\n      background: rgba(103,127,145,.12) !important;\n      color: rgba(233,238,242,.86) !important;\n      font-size: 9px !important;\n      font-weight: 650;\n      letter-spacing: .035em;\n      text-transform: uppercase;\n      text-align: center !important;\n      pointer-events: none !important;\n      overflow: hidden;\n      text-overflow: ellipsis;\n      white-space: nowrap;\n    }\n    #chatgpt-go-watchdog .cg-status::before {\n      content: '';\n      flex: 0 0 6px;\n      width: 6px;\n      height: 6px;\n      border-radius: 50%;\n      background: rgba(145,166,181,.82);\n      box-shadow: 0 0 6px rgba(145,166,181,.24);\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"active\"] .cg-status::before { background: rgba(110,190,124,.92); box-shadow: 0 0 7px rgba(110,190,124,.34); }\n    #chatgpt-go-watchdog[data-status-tone=\"amber\"] .cg-status::before { background: rgba(218,161,84,.92); box-shadow: 0 0 7px rgba(218,161,84,.32); }\n    #chatgpt-go-watchdog[data-status-tone=\"danger\"] .cg-status::before { background: rgba(211,104,111,.92); box-shadow: 0 0 7px rgba(211,104,111,.34); }\n    #chatgpt-go-watchdog .cg-timer {\n      display: inline-flex;\n      align-items: center;\n      justify-content: center;\n      flex: 0 0 104px;\n      width: 104px;\n      height: 25px;\n      box-sizing: border-box;\n      border-radius: 999px;\n      border: 1px solid rgba(218,161,84,.34);\n      background: rgba(218,161,84,.10);\n      color: rgba(255,220,169,.92);\n      font-size: 9px;\n      font-weight: 800;\n      letter-spacing: .04em;\n      font-variant-numeric: tabular-nums;\n      white-space: nowrap;\n      pointer-events: none;\n      box-shadow: inset 0 0 7px rgba(218,161,84,.04);\n    }\n    #chatgpt-go-watchdog .cg-timer[data-mode=\"countdown\"] {\n      border-color: rgba(225,170,91,.62);\n      background: rgba(218,161,84,.16);\n      color: rgba(255,230,190,.98);\n      box-shadow: 0 0 8px rgba(218,161,84,.18), inset 0 0 7px rgba(218,161,84,.06);\n    }\n    #chatgpt-go-watchdog .cg-timer[data-mode=\"error\"] {\n      border-color: rgba(211,104,111,.74);\n      background: rgba(211,104,111,.15);\n      color: rgba(255,215,218,.98);\n      box-shadow: 0 0 9px rgba(211,104,111,.22);\n    }\n    #chatgpt-go-watchdog .cg-timer[data-mode=\"idle\"] {\n      border-color: rgba(145,166,181,.20);\n      background: rgba(145,166,181,.06);\n      color: rgba(214,220,225,.52);\n    }\n    #chatgpt-go-watchdog .cg-actions {\n      grid-column: 3;\n      justify-self: end;\n      display: flex;\n      align-items: center;\n      justify-content: flex-end;\n      gap: 6px;\n      min-width: 0;\n      pointer-events: auto;\n    }\n    #chatgpt-go-watchdog .cg-actions button {\n      display: inline-flex !important;\n      align-items: center;\n      justify-content: center;\n      flex: 0 0 58px !important;\n      width: 58px !important;\n      height: 25px !important;\n      margin: 0 !important;\n      padding: 0 8px !important;\n      visibility: visible !important;\n      opacity: 1 !important;\n      position: static !important;\n      grid-column: auto !important;\n      order: initial !important;\n    }\n    #chatgpt-go-watchdog .cg-actions .cg-go {\n      flex-basis: 70px !important;\n      width: 70px !important;\n      margin-right: 1px !important;\n    }\n    @media (max-width: 620px) {\n      #chatgpt-go-watchdog { grid-template-columns: minmax(88px, 1fr) minmax(58px, 1fr) max-content !important; column-gap: 5px !important; }\n      #chatgpt-go-watchdog .cg-meta { max-width: 120px; padding-inline: 7px; font-size: 8px; }\n      #chatgpt-go-watchdog .cg-status { width: min(100%, 138px) !important; padding-inline: 6px !important; font-size: 8px !important; }\n      #chatgpt-go-watchdog .cg-actions { gap: 4px; }\n      #chatgpt-go-watchdog .cg-actions button { flex-basis: 47px !important; width: 47px !important; padding-inline: 4px !important; font-size: 8px !important; }\n      #chatgpt-go-watchdog .cg-actions .cg-go { flex-basis: 56px !important; width: 56px !important; }\n    }\n    @media (max-width: 430px) {\n      #chatgpt-go-watchdog { grid-template-columns: 72px minmax(42px, 1fr) max-content !important; column-gap: 4px !important; padding-inline: 5px !important; }\n      #chatgpt-go-watchdog .cg-meta { max-width: 72px; padding-inline: 5px; font-size: 7.5px; }\n      #chatgpt-go-watchdog .cg-status { width: 100% !important; padding-inline: 4px !important; font-size: 7.5px !important; }\n      #chatgpt-go-watchdog .cg-actions { gap: 3px; }\n      #chatgpt-go-watchdog .cg-actions button { flex-basis: 36px !important; width: 36px !important; padding-inline: 2px !important; font-size: 7.5px !important; }\n      #chatgpt-go-watchdog .cg-actions .cg-go { flex-basis: 44px !important; width: 44px !important; }\n    }\n\n    /* v4.42.45: split identity chips + neutral status fill with state-colored neon perimeter. */\n    #chatgpt-go-watchdog .cg-meta { display: none !important; }\n    #chatgpt-go-watchdog .cg-identity {\n      grid-column: 1;\n      justify-self: start;\n      display: flex;\n      align-items: center;\n      gap: 5px;\n      min-width: 0;\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog .cg-version,\n    #chatgpt-go-watchdog .cg-project {\n      display: inline-flex;\n      align-items: center;\n      height: 21px;\n      box-sizing: border-box;\n      padding: 0 8px;\n      border-radius: 999px;\n      border: 1px solid rgba(255,255,255,.105);\n      background: rgba(255,255,255,.05);\n      color: rgba(232,235,238,.76);\n      font-size: 8.5px;\n      line-height: 1;\n      white-space: nowrap;\n    }\n    #chatgpt-go-watchdog .cg-version { background: rgba(101,126,145,.09); border-color: rgba(132,157,176,.15); }\n    #chatgpt-go-watchdog .cg-project { background: rgba(128,106,151,.095); border-color: rgba(156,132,180,.18); color: rgba(239,232,245,.82); }\n    #chatgpt-go-watchdog .cg-status {\n      background: rgba(30,34,38,.74) !important;\n      border: 1px solid rgba(126,151,171,.34) !important;\n      box-shadow: 0 0 7px rgba(112,153,181,.16), inset 0 0 7px rgba(112,153,181,.035) !important;\n      color: rgba(238,241,243,.90) !important;\n    }\n    #chatgpt-go-watchdog .cg-status::before { display: none !important; content: none !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"idle\"] .cg-status {\n      border-color: rgba(139,164,182,.38) !important;\n      box-shadow: -11px 0 13px -9px rgba(125,158,181,.22), 11px 0 13px -9px rgba(125,158,181,.22), 0 0 6px rgba(125,158,181,.15), inset 0 0 6px rgba(125,158,181,.035) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"active\"] .cg-status {\n      border-color: rgba(103,191,120,.62) !important;\n      box-shadow: -13px 0 15px -9px rgba(90,193,111,.42), 13px 0 15px -9px rgba(90,193,111,.42), 0 0 7px rgba(90,193,111,.28), inset 0 0 7px rgba(90,193,111,.055) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"amber\"] .cg-status {\n      border-color: rgba(224,163,76,.66) !important;\n      box-shadow: -13px 0 15px -9px rgba(224,154,63,.42), 13px 0 15px -9px rgba(224,154,63,.42), 0 0 7px rgba(224,154,63,.29), inset 0 0 7px rgba(224,154,63,.055) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"danger\"] .cg-status {\n      border-color: rgba(220,96,104,.72) !important;\n      box-shadow: -14px 0 16px -9px rgba(220,85,95,.47), 14px 0 16px -9px rgba(220,85,95,.47), 0 0 8px rgba(220,85,95,.32), inset 0 0 7px rgba(220,85,95,.06) !important;\n    }\n    @media (max-width: 620px) {\n      #chatgpt-go-watchdog .cg-identity { gap: 3px; }\n      #chatgpt-go-watchdog .cg-version, #chatgpt-go-watchdog .cg-project { padding-inline: 5px; font-size: 7.5px; }\n    }\n    @media (max-width: 430px) {\n      #chatgpt-go-watchdog .cg-version { max-width: 64px; overflow: hidden; text-overflow: ellipsis; }\n      #chatgpt-go-watchdog .cg-project { max-width: 58px; overflow: hidden; text-overflow: ellipsis; }\n    }\n\n    /* v4.42.47 visual polish: half-step brighter controls, clearer project chip, textured status + wider side neon. */\n    #chatgpt-go-watchdog .cg-project {\n      background: rgba(128,106,151,.15) !important;\n      border-color: rgba(162,136,188,.27) !important;\n      color: rgba(242,236,248,.86) !important;\n    }\n    #chatgpt-go-watchdog .cg-actions .cg-auto { background: rgba(74,128,82,.52) !important; border-color: rgba(122,168,128,.56) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-auto.on { background: rgba(77,145,90,.73) !important; border-color: rgba(132,184,140,.74) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-new { background: rgba(156,112,57,.575) !important; border-color: rgba(196,148,84,.64) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-stop { background: rgba(145,75,81,.575) !important; border-color: rgba(188,102,110,.65) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-go { background: rgba(63,118,165,.67) !important; border-color: rgba(106,164,210,.75) !important; }\n    #chatgpt-go-watchdog .cg-status {\n      background-color: rgba(28,32,36,.86) !important;\n      background-image: repeating-linear-gradient(135deg, rgba(255,255,255,.030) 0 2px, rgba(255,255,255,0) 2px 7px) !important;\n      background-blend-mode: screen;\n      cursor: default !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"idle\"] .cg-status {\n      box-shadow: -17px 0 20px -10px rgba(125,158,181,.28), 17px 0 20px -10px rgba(125,158,181,.28), 0 0 6px rgba(125,158,181,.16), inset 0 0 6px rgba(125,158,181,.035) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"active\"] .cg-status {\n      box-shadow: -20px 0 23px -10px rgba(90,193,111,.50), 20px 0 23px -10px rgba(90,193,111,.50), 0 0 8px rgba(90,193,111,.30), inset 0 0 7px rgba(90,193,111,.055) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"amber\"] .cg-status {\n      box-shadow: -20px 0 23px -10px rgba(224,154,63,.50), 20px 0 23px -10px rgba(224,154,63,.50), 0 0 8px rgba(224,154,63,.31), inset 0 0 7px rgba(224,154,63,.055) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"danger\"] .cg-status {\n      box-shadow: -21px 0 24px -10px rgba(220,85,95,.56), 21px 0 24px -10px rgba(220,85,95,.56), 0 0 9px rgba(220,85,95,.34), inset 0 0 7px rgba(220,85,95,.06) !important;\n    }\n\n    /* v4.42.48 visual tuning */\n    #chatgpt-go-watchdog .cg-project { background: rgba(128,106,151,.18) !important; border-color: rgba(166,140,193,.32) !important; color: rgba(244,239,249,.88) !important; }\n    #chatgpt-go-watchdog .cg-actions button { color: rgba(253,254,255,.97) !important; font-size: 9px !important; font-weight: 700 !important; letter-spacing: .028em !important; text-shadow: 0 1px 1px rgba(0,0,0,.28); }\n\n    /* v4.42.48 final visual balance */\n    #chatgpt-go-watchdog .cg-actions .cg-auto { background: rgba(74,124,82,.48) !important; border-color: rgba(120,165,126,.52) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-auto.on { background: rgba(76,140,89,.67) !important; border-color: rgba(130,180,137,.69) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-new { background: rgba(154,110,56,.53) !important; border-color: rgba(192,145,82,.59) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-stop { background: rgba(142,74,80,.53) !important; border-color: rgba(184,100,108,.60) !important; }\n    #chatgpt-go-watchdog .cg-actions .cg-go { background: rgba(62,115,161,.62) !important; border-color: rgba(103,162,208,.70) !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"idle\"] .cg-status { box-shadow: -38px 0 46px -12px rgba(125,158,181,.34), 38px 0 46px -12px rgba(125,158,181,.34), 0 0 6px rgba(125,158,181,.15), inset 0 0 6px rgba(125,158,181,.035) !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"active\"] .cg-status { box-shadow: -48px 0 56px -12px rgba(90,193,111,.56), 48px 0 56px -12px rgba(90,193,111,.56), 0 0 8px rgba(90,193,111,.28), inset 0 0 7px rgba(90,193,111,.05) !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"amber\"] .cg-status { box-shadow: -48px 0 56px -12px rgba(224,154,63,.56), 48px 0 56px -12px rgba(224,154,63,.56), 0 0 8px rgba(224,154,63,.29), inset 0 0 7px rgba(224,154,63,.05) !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"danger\"] .cg-status { box-shadow: -52px 0 60px -12px rgba(220,85,95,.62), 52px 0 60px -12px rgba(220,85,95,.62), 0 0 9px rgba(220,85,95,.32), inset 0 0 7px rgba(220,85,95,.055) !important; }\n\n    /* v4.42.49 explicit side glow: pseudo-elements extend neon horizontally without consuming layout width. */\n    #chatgpt-go-watchdog .cg-status { position: relative !important; overflow: visible !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"idle\"] .cg-status { --cg-status-neon: rgba(125,158,181,.48); }\n    #chatgpt-go-watchdog[data-status-tone=\"active\"] .cg-status { --cg-status-neon: rgba(90,193,111,.72); }\n    #chatgpt-go-watchdog[data-status-tone=\"amber\"] .cg-status { --cg-status-neon: rgba(224,154,63,.72); }\n    #chatgpt-go-watchdog[data-status-tone=\"danger\"] .cg-status { --cg-status-neon: rgba(220,85,95,.78); }\n    #chatgpt-go-watchdog .cg-status::before,\n    #chatgpt-go-watchdog .cg-status::after {\n      content: '' !important;\n      display: block !important;\n      position: absolute;\n      top: 50%;\n      width: 42px;\n      height: 7px;\n      transform: translateY(-50%);\n      border-radius: 999px;\n      filter: blur(6px);\n      opacity: .72;\n      pointer-events: none;\n    }\n    #chatgpt-go-watchdog .cg-status::before { right: calc(100% - 4px); background: linear-gradient(90deg, transparent, var(--cg-status-neon)); }\n    #chatgpt-go-watchdog .cg-status::after { left: calc(100% - 4px); background: linear-gradient(90deg, var(--cg-status-neon), transparent); }\n\n    /* v4.42.51 real bezel: dock surface blends into composer; outer shell owns the frame. */\n    #chatgpt-go-watchdog {\n      border-radius: 0 !important;\n      box-shadow: none !important;\n    }\n    #chatgpt-go-watchdog::after {\n      content: none !important;\n      display: none !important;\n      background: none !important;\n      box-shadow: none !important;\n    }\n\n    /* v4.42.51 glow rebalance: keep status state visible without bleeding into neighboring controls. */\n    #chatgpt-go-watchdog .cg-status::before,\n    #chatgpt-go-watchdog .cg-status::after {\n      width: 24px !important;\n      height: 5px !important;\n      filter: blur(5px) !important;\n      opacity: .46 !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"idle\"] .cg-status { box-shadow: -14px 0 18px -12px rgba(125,158,181,.18), 14px 0 18px -12px rgba(125,158,181,.18), 0 0 5px rgba(125,158,181,.12), inset 0 0 5px rgba(125,158,181,.03) !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"active\"] .cg-status { box-shadow: -18px 0 22px -12px rgba(90,193,111,.28), 18px 0 22px -12px rgba(90,193,111,.28), 0 0 6px rgba(90,193,111,.20), inset 0 0 6px rgba(90,193,111,.04) !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"amber\"] .cg-status { box-shadow: -18px 0 22px -12px rgba(224,154,63,.28), 18px 0 22px -12px rgba(224,154,63,.28), 0 0 6px rgba(224,154,63,.20), inset 0 0 6px rgba(224,154,63,.04) !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"danger\"] .cg-status { box-shadow: -20px 0 24px -12px rgba(220,85,95,.32), 20px 0 24px -12px rgba(220,85,95,.32), 0 0 7px rgba(220,85,95,.22), inset 0 0 6px rgba(220,85,95,.045) !important; }\n\n    /* v4.42.54 own-surface-only dock. Never style/class/resize ChatGPT composer. */\n    #chatgpt-go-watchdog {\n      background: rgb(27,27,27) !important;\n      border: 0 !important;\n      box-shadow: none !important;\n      backdrop-filter: none !important;\n      border-radius: 0 !important;\n      overflow: visible !important;\n    }\n    #chatgpt-go-watchdog::before,\n    #chatgpt-go-watchdog::after {\n      content: '' !important;\n      display: block !important;\n      position: absolute !important;\n      top: -14px !important;\n      bottom: 0 !important;\n      width: 5px !important;\n      box-sizing: border-box !important;\n      background: rgb(27,27,27) !important;\n      box-shadow: none !important;\n      pointer-events: none !important;\n      z-index: -1 !important;\n    }\n    #chatgpt-go-watchdog::before {\n      left: 0 !important;\n      border-left: 2px solid rgba(94,100,106,.58) !important;\n      border-top: -9px !important;\n      border-radius: 4px 0 0 0 !important;\n    }\n    #chatgpt-go-watchdog::after {\n      right: 0 !important;\n      border-right: 2px solid rgba(94,100,106,.58) !important;\n      border-top: 0 !important;\n      border-radius: 0 4px 0 0 !important;\n    }\n\n    /* v4.42.84 unified composer/dock bezel.\n       Keep every repair pixel inside the composer-aligned dock width.\n       The frame intentionally uses the same surface color as the dock/chat seam,\n       so it fills anti-aliased black gaps instead of looking like a new outline. */\n    #chatgpt-go-watchdog {\n      --cg-unified-surface: rgb(27,27,27);\n      --cg-bezel-thickness: 9px;\n      /* v4.43.33: the GoDog slab remains solid below the composer. The visual\n         continuation upward is painted by the composer itself as a same-shape\n         zero-blur shadow ladder, so the rounded input stays on top. */\n      background: var(--cg-unified-surface) !important;\n      backdrop-filter: none !important;\n      border-radius: 0 0 14px 14px !important;\n      border: 0 !important;\n      box-shadow: none !important;\n      overflow: visible !important;\n    }\n    /* v4.42.90: only two side bridges. Each runs from the vertical midpoint\n       of the ChatGPT composer to the vertical midpoint of the GoDog dock. */\n    #chatgpt-go-watchdog::before,\n    #chatgpt-go-watchdog::after { content: none !important; display: none !important; }\n    #chatgpt-go-watchdog > .cg-dock-bg-lift {\n      display: none !important;\n    }\n    .cg-composer-seam-cap {\n      position: fixed !important;\n      width: 5px !important;\n      height: 14px !important;\n      box-sizing: border-box !important;\n      background: var(--cg-seam-surface, rgb(27,27,27)) !important;\n      pointer-events: none !important;\n      z-index: -1 !important;\n      display: none;\n    }\n    .cg-composer-seam-cap.cg-left {\n      clip-path: none !important;\n      border-left: 1px solid var(--cg-seam-edge, rgba(255,255,255,.014)) !important;\n    }\n    .cg-composer-seam-cap.cg-right {\n      clip-path: none !important;\n      border-right: 1px solid var(--cg-seam-edge, rgba(255,255,255,.014)) !important;\n    }\n    #chatgpt-go-watchdog-underlay {\n      position: absolute !important;\n      box-sizing: border-box !important;\n      pointer-events: none !important;\n      z-index: -1 !important;\n      display: none;\n      border: 1px solid var(--cg-underlay-edge, rgba(255,255,255,.014)) !important;\n      box-shadow: none !important;\n    }\n    .cg-fixed-side-bridge {\n      position: fixed !important;\n      width: 5px !important;\n      box-sizing: border-box !important;\n      border: 0 !important;\n      border-radius: 0 !important;\n      box-shadow: none !important;\n      pointer-events: none !important;\n      z-index: 2147483646 !important;\n      display: none;\n    }\n    #chatgpt-go-watchdog > * {\n      position: relative;\n      z-index: 1;\n    }\n\n    /* v4.42.57 status state light lives inside the pill only. */\n    #chatgpt-go-watchdog .cg-status::before,\n    #chatgpt-go-watchdog .cg-status::after { content: none !important; display: none !important; }\n    #chatgpt-go-watchdog[data-status-tone=\"idle\"] .cg-status {\n      box-shadow: inset 0 0 12px rgba(125,158,181,.18), inset 0 0 4px rgba(165,194,214,.20) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"active\"] .cg-status {\n      box-shadow: inset 0 0 14px rgba(90,193,111,.30), inset 0 0 5px rgba(126,226,145,.24) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"amber\"] .cg-status {\n      box-shadow: inset 0 0 14px rgba(224,154,63,.30), inset 0 0 5px rgba(240,184,104,.24) !important;\n    }\n    #chatgpt-go-watchdog[data-status-tone=\"danger\"] .cg-status {\n      box-shadow: inset 0 0 15px rgba(220,85,95,.34), inset 0 0 5px rgba(240,126,136,.26) !important;\n    }\n\n    /* v4.42.99: 1px outer edge, inner pixels stay unified surface. */\n    #chatgpt-go-watchdog {\n      --cg-unified-edge: rgba(255,255,255,.014);\n      box-sizing: border-box !important;\n      border-top: 0 !important;\n      border-left: 1px solid var(--cg-unified-edge) !important;\n      border-right: 1px solid var(--cg-unified-edge) !important;\n      border-bottom: 1px solid var(--cg-unified-edge) !important;\n    }\n  ";
  style.id = 'godog-pc-local-original-style';

  function $(selector) { return root.querySelector(selector); }
  const goButton = $('.cg-go'), autoButton = $('.cg-auto'), newButton = $('.cg-new'), stopButton = $('.cg-stop');
  const statusNode = $('.cg-status');
  const savedState = () => safeStorage.set(STATE_KEY, JSON.stringify({ auto, awaitReply, busySeen, assistant:lastAssistantSignature }));
  function status(text) {
    if (statusNode && statusNode.textContent !== text) statusNode.textContent = text;
    root.dataset.status = text === 'ALEX NEEDED' ? 'alex_needed' : '';
    // Existing 6.0.26 CSS controls status glow, without any new style rules.
    root.dataset.statusTone = /ALEX NEEDED|FAILED|CHAT BUSY|NO COMPOSER/i.test(text)
      ? 'danger' : /AUTO|SENT|GO|NEW/i.test(text) ? 'active' : 'idle';
  }
  function projectLabel() {
    const title = String(document.title || '');
    const match = title.match(/\b(GoDog|Forge|RevEng|Social|TownLabel|MedEng|MediaEngine)\b/i);
    if (!match) return 'GoDog';
    const key=match[1].toLowerCase();
    return {godog:'GoDog',forge:'Forge',reveng:'RevEng',social:'Social',townlabel:'TownLabel',medeng:'MedEng',mediaengine:'MedEng'}[key] || 'GoDog';
  }
  function paint() {
    if (autoButton) {
      autoButton.classList.toggle('on', auto);
      autoButton.textContent = 'AUTO'; // Exact original label even when AUTO is on.
      autoButton.setAttribute('aria-pressed',auto?'true':'false');
    }
    const vn=$('.cg-version'); if(vn) vn.textContent='GoDog '+VERSION;
    const pn=$('.cg-project'); if(pn) pn.textContent=projectLabel();
    const tm=$('.cg-timer'); if(tm) {
      tm.textContent='';
      tm.style.setProperty('display','none','important');
      tm.setAttribute('aria-hidden','true');
    }
    root.dataset.meta='GoDog '+VERSION;
  }
  function mount() {
    if (!style.isConnected) document.documentElement.appendChild(style);
    if (!root.isConnected && document.body) document.body.appendChild(root);
  }
  // UI-only restoration: the 6.0.26 panel was placed directly under
  // the ChatGPT composer. The original 35 KB CSS is unchanged.
  let lastDock = '';
  function alignDockToComposer() {
    if (!root.isConnected) return;
    const vw=Math.max(1,window.innerWidth||document.documentElement.clientWidth||1200);
    const vh=Math.max(40,window.innerHeight||720);
    const ed=composer();
    const editorRect=ed?.getBoundingClientRect?.();
    const valid=(r)=>!!r && Number.isFinite(r.width) && Number.isFinite(r.left) &&
      r.width>=240 && r.width<=vw-8 && r.height>=32 && r.height<=320;
    let surface=ed?.closest?.('[data-type="unified-composer"]') || null;
    if (!valid(surface?.getBoundingClientRect?.())) surface=null;
    // ChatGPT changes markup. Use the nearest realistically sized rounded
    // composer surface instead of blindly using a viewport-wide <form>.
    if (!surface && ed) {
      let opaque=null, sized=null;
      for(let el=ed.parentElement,i=0;el&&i<11;el=el.parentElement,i++) {
        const r=el.getBoundingClientRect?.();
        if(!valid(r)) continue;
        const cs=window.getComputedStyle?.(el);
        const radius=parseFloat(cs?.borderTopLeftRadius||'0')||0;
        const bg=String(cs?.backgroundColor||'');
        if(!sized) sized=el;
        if(bg && bg!=='transparent' && bg!=='rgba(0, 0, 0, 0)' && !opaque) opaque=el;
        if(radius>=12 && r.width>=(editorRect?.width||0)) {surface=el;break;}
      }
      surface=surface||opaque||sized;
    }
    const rect=surface?.getBoundingClientRect?.();
    const fallbackWidth=Math.max(250,Math.min(vw-16,
      vw>1500?780:Math.min(960,Math.round(vw*.82))));
    let width=fallbackWidth, left=Math.round((vw-width)/2), dockTop=vh-40;
    if(valid(rect)) {
      width=Math.min(rect.width,vw-16);
      left=Math.max(8,Math.min(Math.round(rect.left),vw-width-8));
      const send=getSendButton(), sr=send?.getBoundingClientRect?.();
      const dockHeight=Math.max(33,Math.round(root.getBoundingClientRect().height||36));
      const below=(sr?.width>8&&sr?.height>8)?sr.bottom+2:rect.bottom-1;
      dockTop=Math.max(0,Math.min(Math.round(below),vh-dockHeight-3));
    } else if(valid(editorRect)) {
      width=Math.max(250,Math.min(vw-16,editorRect.width+72));
      left=Math.max(8,Math.min(Math.round(editorRect.left-36),vw-width-8));
      dockTop=Math.max(0,Math.min(Math.round(editorRect.bottom+12),vh-39));
    }
    // A width constraint is mandatory even when composer geometry fails.
    // It eliminates the observed full-viewport 7.0.2 dock failure.
    const signature=[left,Math.round(width),dockTop].join(':');
    if(signature!==lastDock) {
      lastDock=signature;
      root.style.setProperty('left',left+'px','important');
      root.style.setProperty('width',Math.round(width)+'px','important');
      root.style.setProperty('max-width','calc(100vw - 16px)','important');
      root.style.setProperty('right','auto','important');
      root.style.setProperty('top',dockTop+'px','important');
      root.style.setProperty('bottom','auto','important');
    }
    root.style.setProperty('visibility',ed?'visible':'hidden','important');
  }
  function getSendButton() {
    return document.querySelector('[data-testid="send-button"], button[aria-label="Send prompt"], button[aria-label="Send message"], button[aria-label="Send"], button[title="Send"]');
  }
  function getNativeStopButton() {
    return document.querySelector('[data-testid="stop-button"], button[aria-label="Stop generating"], button[aria-label="Stop generation"], button[aria-label="Stop response"]');
  }
  function isBusy() {
    return !!getNativeStopButton();
  }
  function composer() {
    for(const selector of ['#prompt-textarea','[data-testid="composer-text-input"]','[contenteditable="true"][data-testid*="composer"]','[contenteditable="true"][aria-label="Ask ChatGPT"]','[contenteditable][role="textbox"]','textarea[placeholder="Ask ChatGPT"]']) {
      const el=document.querySelector(selector);
      if(el && !el.closest('#chatgpt-go-watchdog') && el.getAttribute('aria-disabled')!=='true') return el;
    }
    const send = getSendButton(), form = send && send.closest('form');
    return form && form.querySelector('[contenteditable="true"], textarea') || null;
  }
  function textOf(el) {
    if(!el) return '';
    return (typeof el.value==='string' ? el.value : el.innerText || el.textContent || '').trim();
  }
  function lastMessage(role) {
    const nodes = document.querySelectorAll('[data-message-author-role="' + role + '"]');
    return nodes.length ? nodes[nodes.length-1] : null;
  }
  function assistantText() {
    const el=lastMessage('assistant');
    if(!el) return '';
    const body=el.querySelector('.markdown, .prose, [data-testid="message-text"]') || el;
    return textOf(body);
  }
  function userText() {
    const el=lastMessage('user'); return textOf(el);
  }
  function assistantSignature() {
    const el=lastMessage('assistant');
    if(!el) return '';
    const id=el.getAttribute('data-message-id') || el.getAttribute('data-testid') || '';
    const txt=assistantText();
    // Signature changes as the latest assistant reply streams, but AUTO sends only after native busy control disappears.
    return id+'|'+txt.length+'|'+txt.slice(-180);
  }
  function getDraft() { return textOf(composer()); }
  function putComposer(message) {
    const editor=composer(); if(!editor) return false;
    ownInput=true;
    try {
      editor.focus();
      if('value' in editor && typeof editor.value==='string') {
        const proto=editor.tagName==='TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
        if(setter) setter.call(editor,message); else editor.value=message;
        editor.dispatchEvent(new Event('input',{bubbles:true}));
      } else {
        const sel=window.getSelection();
        const rng=document.createRange(); rng.selectNodeContents(editor);
        sel.removeAllRanges(); sel.addRange(rng);
        const worked=typeof document.execCommand==='function' && document.execCommand('insertText',false,message);
        if(!worked || textOf(editor)!==message) {
          // ProseMirror/Tiptap fallback. The synthetic input also notifies the framework.
          editor.replaceChildren();
          const p=document.createElement('p'); p.textContent=message; editor.appendChild(p);
          try {editor.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:message}));}
          catch (_) {editor.dispatchEvent(new Event('input',{bubbles:true}));}
        }
      }
      return getDraft()===message;
    } finally { ownInput=false; }
  }
  function pressNativeSend() {
    const b=getSendButton();
    if(b && !b.disabled && b.getAttribute('aria-disabled')!=='true') {
      b.click();
      return 'button';
    }
    const ed=composer();
    if(!ed) return null;
    // One immediate native-enter fallback, no timer, no retry loop.
    ed.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',bubbles:true,cancelable:true,keyCode:13,which:13}));
    return 'enter';
  }
  function sendNow(message, cause) {
    if(isBusy()) {status('CHAT BUSY'); return false;}
    const ed=composer();
    if(!ed) {status('NO COMPOSER'); return false;}
    const draft=getDraft();
    if(draft && draft!==message) {
      safeStorage.set(DRAFT_KEY,draft); // never silently discard a manual draft
    }
    if(!putComposer(message)) {status('INPUT FAILED'); return false;}
    // Fire the native submission immediately. No go queue, cooldown, counter, polling or timeout.
    const route=pressNativeSend();
    if(!route) {status('SEND UNAVAILABLE'); return false;}
    pendingAck={text:message,previousUser: lastMessage('user'),route};
    awaitReply=auto && cause!=='manual';
    busySeen=false;
    lastAssistantSignature=assistantSignature();
    savedState();
    status(cause==='handoff' ? 'NEW → CLICK' : 'GO → CLICK');
    // ChatGPT may enable Send only after updating React state: one microtask recheck, not a timer.
    if(route==='enter') queueMicrotask(() => {
      const b=getSendButton();
      if(b && !b.disabled && b.getAttribute('aria-disabled')!=='true' && getDraft()===message && !isBusy()) {
        b.click(); pendingAck.route='button';
      }
    });
    return true;
  }
  function pauseAuto(reason) {
    auto=false; awaitReply=false; busySeen=false;
    savedState(); paint(); status(reason || 'STOPPED');
  }
  function sendGo(manual) {
    if(manual) { // Direct manual click overrides AUTO scheduling state, but does not alter AUTO setting.
      awaitReply=false;
    }
    const sent=sendNow('GO',manual?'manual':'auto');
    if(sent && auto) { awaitReply=true; savedState(); }
    return sent;
  }
  function takeSnapshot() {
    const a=assistantText().slice(-7000), u=userText().slice(-1300);
    const route=document.title.slice(0,120);
    return {
      from:location.href,
      project:route,
      assistant:a,
      user:u,
      resumeAuto:true
    };
  }
  function handoffMessage(h) {
    return '[GODOG LOCAL NEW / CONTINUE]\n' +
      'Проект: '+(h.project||'текущий')+'\n'+
      'Перенос выполнен локально, без Supabase. Продолжи работу с последнего этапа, не повторяй уже выполненное.\n' +
      'Последнее сообщение пользователя:\n'+(h.user||'(нет)')+'\n'+
      'Последний ответ ассистента:\n'+(h.assistant||'(нет)')+'\n'+
      'Выполни следующий полезный конкретный шаг, сохрани контрольную точку в ответе. Не выдумывай доступ к отсутствующим инструментам.';
  }
  function goNewChat() {
    newHandoff=takeSnapshot();
    safeStorage.set(NEW_KEY,JSON.stringify(newHandoff));
    auto=false; awaitReply=false; savedState(); paint(); status('NEW → CHAT');
    // Native same-tab New Chat, with fallback to same-tab navigation. No handoff wait.
    const candidates=Array.from(document.querySelectorAll('a[href],button[aria-label],button[data-testid]'));
    const native=candidates.find(e=>{
      const label=((e.getAttribute('aria-label')||'')+' '+(e.getAttribute('title')||'')+' '+(e.getAttribute('data-testid')||'')).toLowerCase();
      return /new.chat|new.conversation|new-chat/.test(label) && !e.closest('#chatgpt-go-watchdog');
    });
    if(native) {native.click();}
    else {location.assign('https://chatgpt.com/');}
  }
  function inFreshChat() {
    return !lastMessage('user') && !lastMessage('assistant') &&
      !/\/c\/[a-z0-9-]+/i.test(location.pathname);
  }
  function maybeSendHandoff() {
    if(!newHandoff) return;
    if(location.href===newHandoff.from || !inFreshChat() || isBusy() || !composer()) return;
    const msg=handoffMessage(newHandoff);
    // Clear before attempting: a missed native click should NOT duplicate the full handoff.
    safeStorage.del(NEW_KEY); newHandoff=null;
    auto=true; paint(); savedState();
    const ok=sendNow(msg,'handoff');
    if(!ok) {
      // Explicit failure, never silently queue a new message or spin in retry loops.
      auto=false; paint(); savedState(); status('NEW SEND FAILED');
    }
  }
  function maybeConfirm() {
    if(!pendingAck) return;
    const u=lastMessage('user');
    const txt=textOf(u);
    if(u && u!==pendingAck.previousUser && (txt===pendingAck.text || txt.includes(pendingAck.text.slice(0,100)))) {
      pendingAck=null;
      status(auto?'AUTO ON':'SENT');
    } else if(isBusy()) {
      pendingAck=null;
      status(auto?'AUTO ON':'SENT');
    }
  }
  function maybeContinueAuto() {
    if(!auto || !awaitReply) return;
    if(isBusy()) {busySeen=true; savedState();return;}
    const s=assistantSignature();
    if(!s || s===lastAssistantSignature) return;
    const text=assistantText();
    if(/(?:^|\n)\s*(?:ALEX_NEEDED|USER_NEEDED|ALEX NEEDED|AUTO_GO_STOP)\s*(?:\n|$)/i.test(text)) {
      pauseAuto('ALEX NEEDED');return;
    }
    // One next GO per NEW completed assistant turn. This is driven by DOM changes, never by a timer.
    awaitReply=false; savedState();
    sendGo(false);
  }
  function tick() {
    mount();
    alignDockToComposer();
    if(newHandoff) maybeSendHandoff();
    maybeConfirm();
    if(auto) maybeContinueAuto();
  }
  function requestTick() {
    if(watching) return;
    watching=true;
    queueMicrotask(()=>{watching=false;tick();});
  }
  goButton?.addEventListener('click',(e)=>{
    if(e.ctrlKey) return;
    sendGo(true);
  });
  stopButton?.addEventListener('click',(e)=>{
    if(e.ctrlKey) return;
    pauseAuto('STOPPED'); // does NOT stop ChatGPT or close any tab
  });
  autoButton?.addEventListener('click',(e)=>{
    if(e.ctrlKey) return;
    if(auto) {pauseAuto('AUTO OFF');return;}
    auto=true; paint();savedState();status('AUTO ON');
    if(isBusy()) {awaitReply=true;busySeen=true;lastAssistantSignature=assistantSignature();savedState();status('AUTO ARMED');}
    else sendGo(false); // immediately sends GO if ChatGPT can accept it
  });
  newButton?.addEventListener('click',(e)=>{if(e.ctrlKey)return;goNewChat();});
  $('.cg-update-dismiss')?.addEventListener('click',()=>{
    root.dataset.versionNotice='hidden';
    try{localStorage.setItem(VERSION_KEY,VERSION);}catch(_){}
  });
  document.addEventListener('input',(event)=>{
    if(ownInput || !event.isTrusted || !auto) return;
    const ed=composer();
    if(ed && (ed===event.target || ed.contains(event.target))) pauseAuto('USER TYPING');
  },true);
  mount(); paint();status(auto?'AUTO':'DISARMED');
  window.addEventListener('resize',requestTick,{passive:true});
  try {
    const last=localStorage.getItem(VERSION_KEY);
    if(last && last!==VERSION) {
      root.dataset.versionNotice='show';
      const ver=$('.cg-update-version'); if(ver) ver.textContent='GoDog '+VERSION;
      const t=$('.cg-update-time'); if(t) t.textContent='Локальная версия. Без Supabase.';
    } else if(!last) localStorage.setItem(VERSION_KEY,VERSION);
  } catch(_){}
  // Observer is LOCAL and event-driven. No timers, no remote requests.
  const observer=new MutationObserver(requestTick);
  observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['disabled','aria-disabled']});
  requestTick();
})();

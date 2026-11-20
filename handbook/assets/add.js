/* Add an item: photo -> optional AI fill-in -> commit to the inventory repository.
   Runs entirely in the browser. Keys never leave it except to api.github.com / api.anthropic.com. */
(function () {
  var data = JSON.parse(document.getElementById('add-data').textContent);
  var $ = function (id) { return document.getElementById(id); };
  var store = {
    get: function (k) { try { return localStorage.getItem('tl.' + k) || ''; } catch (e) { return ''; } },
    set: function (k, v) { try { localStorage.setItem('tl.' + k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem('tl.' + k); } catch (e) {} }
  };
  var HEAD_NOTES = 'Notes (Function & Operating Range)';
  var photo = null;      // {blob (460px for the repo), ai (base64 ~1000px)}

  // ---- settings -------------------------------------------------------------------------------
  function loadSettings() {
    $('s-gh').value = store.get('gh'); $('s-ai').value = store.get('ai');
    $('s-repo').value = store.get('repo') || data.repo || ''; $('s-branch').value = store.get('branch') || data.branch || 'main';
    $('s-model').value = store.get('model') || data.model;
    $('a-set').open = !store.get('gh');
    refresh();
  }
  function refresh() { $('a-ai').disabled = !(photo && store.get('ai')); }
  $('s-save').addEventListener('click', function () {
    store.set('gh', $('s-gh').value.trim()); store.set('ai', $('s-ai').value.trim());
    store.set('repo', $('s-repo').value.trim()); store.set('branch', $('s-branch').value.trim());
    store.set('model', $('s-model').value.trim());
    say('Settings saved on this device.', 'ok'); $('a-set').open = false; refresh();
  });
  $('s-forget').addEventListener('click', function () {
    store.del('gh'); store.del('ai'); $('s-gh').value = ''; $('s-ai').value = '';
    say('Keys removed from this device.', 'ok'); refresh();
  });

  function say(text, kind, html) {
    var m = $('a-msg'); m.hidden = !text; m.className = 'notice' + (kind ? ' ' + kind : '');
    if (html) m.innerHTML = text; else m.textContent = text;
    if (text) m.scrollIntoView({ block: 'nearest' });
  }

  // ---- type list ------------------------------------------------------------------------------
  var sel = $('f-type'); sel.innerHTML = '<option value="">Choose...</option>';
  data.types.forEach(function (t) {
    var o = document.createElement('option'); o.value = t.prefix; o.textContent = t.group + ' (' + t.prefix + ')'; sel.appendChild(o);
  });

  // ---- photo ----------------------------------------------------------------------------------
  function resize(file, edge, q) {
    var load = window.createImageBitmap
      ? createImageBitmap(file, { imageOrientation: 'from-image' })
      : new Promise(function (ok, no) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = no; i.src = URL.createObjectURL(file); });
    return load.then(function (b) {
      var w = b.width || b.naturalWidth, h = b.height || b.naturalHeight, s = Math.min(1, edge / Math.max(w, h));
      var c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w * s)); c.height = Math.max(1, Math.round(h * s));
      var x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height); x.drawImage(b, 0, 0, c.width, c.height);
      return new Promise(function (ok) { c.toBlob(function (bl) { ok(bl); }, 'image/jpeg', q); });
    });
  }
  function blobToB64(blob) {
    return new Promise(function (ok, no) {
      var r = new FileReader(); r.onload = function () { ok(String(r.result).split(',')[1]); }; r.onerror = no; r.readAsDataURL(blob);
    });
  }
  function pick(e) {
    var f = e.target.files && e.target.files[0]; if (!f) return;
    say('');
    Promise.all([resize(f, 460, 0.88), resize(f, 1000, 0.85)]).then(function (r) {
      return blobToB64(r[1]).then(function (b64) { photo = { blob: r[0], ai: b64 }; });
    }).then(function () {
      var p = $('a-prev'); p.src = URL.createObjectURL(photo.blob); p.hidden = false; refresh();
    }).catch(function () { say('That file could not be read as a photo. Try a JPEG or PNG.', 'err'); });
  }
  $('a-cam').addEventListener('change', pick); $('a-file').addEventListener('change', pick);

  // ---- AI fill-in -----------------------------------------------------------------------------
  function prompt() {
    var kinds = data.types.map(function (t) { return t.prefix + ' = ' + t.group; }).join('; ');
    return 'You are helping catalogue equipment in a university photonics and fabrication lab. Look at the photo and identify the item. ' +
      'Reply with ONLY one JSON object (no markdown) with these keys: type, name, maker, part, wave, size, spec, qty, notes, setup.\n' +
      'type: the best matching code from this list: ' + kinds + '.\n' +
      'Rules: Transcribe any text on labels exactly. NEVER invent a part number, serial or specification: if you cannot read it, leave it empty. ' +
      'If no maker marking is visible, maker is "Unmarked". name: plain words, lead with the distinguishing feature. ' +
      'wave: the optical band, or "n/a" for non-optical items; leave empty if unknown. size: dimensions, thread or mount if visible. ' +
      'spec: the single number that matters most for this item, if it can be read or reliably inferred. qty: integer count of identical items in the photo (default 1). ' +
      'notes: one or two plain sentences, no markdown, no line breaks: what it is typically used for in a lab and the one or two things most likely to damage it or give a wrong result. ' +
      'Put the words NOT CONFIRMED next to anything you inferred rather than read off the item. setup: leave empty.';
  }
  $('a-ai').addEventListener('click', function () {
    var btn = $('a-ai'), st = $('a-aistat'); btn.disabled = true; st.textContent = 'Looking at the photo...';
    fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-api-key': store.get('ai'), 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' },
      body: JSON.stringify({
        model: store.get('model') || data.model, max_tokens: 1500,
        messages: [{ role: 'user', content: [{ type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: photo.ai } }, { type: 'text', text: prompt() }] }]
      })
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error((r.status === 401 ? 'The Anthropic key was rejected. ' : r.status === 404 ? 'Model not found: change it under Keys and repository. ' : r.status === 429 ? 'Rate limited. Wait a minute and try again. ' : '') + ((j && j.error && j.error.message) || 'HTTP ' + r.status));
        return j;
      });
    }).then(function (j) {
      var t = (j.content || []).map(function (c) { return c.text || ''; }).join(''), m = /\{[\s\S]*\}/.exec(t);
      if (!m) throw new Error('The AI did not return usable data. Fill the form by hand.');
      var o = JSON.parse(m[0]), set = function (id, v) { if (v !== undefined && v !== null && String(v).trim() !== '') $(id).value = String(v).replace(/\s+/g, ' ').trim(); };
      if (o.type && data.types.some(function (x) { return x.prefix === o.type; })) $('f-type').value = o.type;
      set('f-name', o.name); set('f-maker', o.maker); set('f-part', o.part); set('f-wave', o.wave); set('f-size', o.size);
      set('f-spec', o.spec); set('f-qty', parseInt(o.qty, 10) > 0 ? parseInt(o.qty, 10) : 1); set('f-notes', o.notes); set('f-setup', o.setup);
      $('f-unsure').checked = true;
      st.textContent = 'Filled in. The AI only sees the photo, so check every field against the item.';
    }).catch(function (e) {
      st.textContent = ''; say('AI fill-in failed: ' + (e.message === 'Failed to fetch' ? 'could not reach api.anthropic.com (network or blocker).' : e.message), 'err');
    }).then(function () { refresh(); });
  });

  // ---- CSV ------------------------------------------------------------------------------------
  function parseCSV(text) {
    var rows = [], row = [], f = '', q = false, i = 0, c;
    for (; i < text.length; i++) {
      c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
      else if (c === '"') q = true;
      else if (c === ',') { row.push(f); f = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(f); f = ''; rows.push(row); row = []; }
      else f += c;
    }
    if (f !== '' || row.length) { row.push(f); rows.push(row); }
    return rows;
  }
  function csvLine(fields) {
    return fields.map(function (v) { v = String(v == null ? '' : v); return /[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(',');
  }
  function clean(v, max) { return String(v || '').replace(/\s+/g, ' ').trim().slice(0, max); }

  // ---- GitHub ---------------------------------------------------------------------------------
  function gh(path, opt) {
    opt = opt || {};
    var h = { Authorization: 'Bearer ' + store.get('gh'), Accept: opt.raw ? 'application/vnd.github.raw+json' : 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
    if (opt.body) h['Content-Type'] = 'application/json';
    return fetch('https://api.github.com/repos/' + opt.repo + path, { method: opt.method || 'GET', headers: h, body: opt.body ? JSON.stringify(opt.body) : undefined }).then(function (r) {
      if (opt.raw && r.ok) return r.text();
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) { var e = new Error(r.status === 401 ? 'GitHub rejected the token (expired or wrong).' : r.status === 403 || r.status === 404 ? 'GitHub says no access to ' + opt.repo + ' (check the token has Contents: Read and write on this repository, and that you have write access). ' + (j.message || '') : (j.message || 'HTTP ' + r.status)); e.status = r.status; throw e; }
        return j;
      });
    });
  }

  function save(f, repo, branch, attempt) {
    var o = { repo: repo };
    return gh('/git/ref/heads/' + encodeURIComponent(branch), o).then(function (ref) {
      var head = ref.object.sha;
      return gh('/git/commits/' + head, o).then(function (commit) {
        return gh('/contents/optics_catalog.csv?ref=' + head, { repo: repo, raw: true }).then(function (text) {
          var nl = /\r\n/.test(text.slice(0, 5000)) ? '\r\n' : '\n';
          var rows = parseCSV(text), head0 = rows[0], col = function (n) { return head0.indexOf(n); };
          if (head0.length !== 13) throw new Error('optics_catalog.csv does not have 13 columns; not touching it.');
          var iID = col('ID'), iPart = col('Part Number'), max = 0, dup = '';
          rows.slice(1).forEach(function (r) {
            if (r[iID] && r[iID].indexOf(f.prefix + '-') === 0) max = Math.max(max, parseInt(r[iID].slice(f.prefix.length + 1), 10) || 0);
            if (!dup && f.part.length >= 3 && r[iPart] && r[iPart].trim().toLowerCase() === f.part.toLowerCase()) dup = r[iID];
          });
          var id = f.prefix + '-' + String(max + 1).padStart(3, '0'), notes = f.notes;
          if (dup) notes += ' FLAG: possible duplicate of ' + dup + ' (same part number). Compare the two before keeping both.';
          if (f.unsure) notes += ' FLAG: added through the website on ' + new Date().toISOString().slice(0, 10) + '; details not yet checked against the part.';
          var line = csvLine([id, f.category, f.name, f.maker, f.part, f.wave || 'n/a', f.size, f.spec, notes.trim(), f.qty, '', f.setup, 'Added through the website' + (f.photo ? '; photo taken on site' : '; no photo')]);
          var next = text + (/[\r\n]$/.test(text) ? '' : nl) + line + nl;
          var blobs = [gh('/git/blobs', { repo: repo, method: 'POST', body: { content: next, encoding: 'utf-8' } })];
          if (f.photo) blobs.push(blobToB64(f.photo).then(function (b64) { return gh('/git/blobs', { repo: repo, method: 'POST', body: { content: b64, encoding: 'base64' } }); }));
          return Promise.all(blobs).then(function (b) {
            var tree = [{ path: 'optics_catalog.csv', mode: '100644', type: 'blob', sha: b[0].sha }];
            if (f.photo) tree.push({ path: 'crops/' + id + '.jpg', mode: '100644', type: 'blob', sha: b[1].sha });
            return gh('/git/trees', { repo: repo, method: 'POST', body: { base_tree: commit.tree.sha, tree: tree } });
          }).then(function (t) {
            return gh('/git/commits', { repo: repo, method: 'POST', body: { message: 'Add ' + f.name + ' (' + id + ')', tree: t.sha, parents: [head] } });
          }).then(function (c) {
            return gh('/git/refs/heads/' + encodeURIComponent(branch), { repo: repo, method: 'PATCH', body: { sha: c.sha, force: false } }).then(function () { return { id: id, dup: dup }; });
          });
        });
      });
    }).catch(function (e) {
      if (e.status === 422 && attempt < 3) return save(f, repo, branch, attempt + 1);   // someone else committed first: redo from the new head
      throw e;
    });
  }

  $('a-form').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var repo = (store.get('repo') || data.repo || '').trim(), branch = (store.get('branch') || data.branch || 'main').trim();
    if (!store.get('gh')) { $('a-set').open = true; say('Add your GitHub token under "Keys and repository" first.', 'err'); return; }
    if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) { $('a-set').open = true; say('Set the repository as owner/name under "Keys and repository".', 'err'); return; }
    var t = data.types.filter(function (x) { return x.prefix === $('f-type').value; })[0];
    if (!t) { say('Choose the kind of item.', 'err'); return; }
    var qty = parseInt($('f-qty').value, 10);
    if (!(qty >= 1)) { say('Quantity must be a whole number, 1 or more.', 'err'); return; }
    var f = { prefix: t.prefix, category: t.category, name: clean($('f-name').value, 300), maker: clean($('f-maker').value, 200), part: clean($('f-part').value, 200),
      wave: clean($('f-wave').value, 100), size: clean($('f-size').value, 200), spec: clean($('f-spec').value, 300), qty: String(qty),
      setup: clean($('f-setup').value, 200), notes: clean($('f-notes').value, 3000), unsure: $('f-unsure').checked, photo: photo ? photo.blob : null };
    if (!f.name || !f.maker) { say('Item name and manufacturer are required (write Unmarked if there is no marking).', 'err'); return; }
    var go = $('a-go'); go.disabled = true; go.textContent = 'Saving...'; say('Saving to ' + repo + '...');
    save(f, repo, branch, 0).then(function (r) {
      say('Saved as <b>' + r.id + '</b>' + (r.dup ? ' (flagged as a possible duplicate of ' + r.dup + ')' : '') + '. It will show in the catalogue after the site rebuilds, in about a minute or two. ' +
        '<a href="https://github.com/' + repo + '/commits/' + encodeURIComponent(branch) + '" target="_blank" rel="noopener">See the commit</a>.', 'ok', true);
      $('a-form').reset(); photo = null; $('a-prev').hidden = true; $('a-aistat').textContent = ''; refresh();
    }).catch(function (e) {
      say('Not saved: ' + (e.message === 'Failed to fetch' ? 'could not reach api.github.com (network or blocker).' : e.message), 'err');
    }).then(function () { go.disabled = false; go.textContent = 'Add to catalogue'; });
  });

  loadSettings();
})();

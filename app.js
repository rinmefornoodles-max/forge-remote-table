(async () => {
  'use strict';

  const parts = [
    './app-src/part-00.txt',
    './app-src/part-01.txt',
    './app-src/part-02.txt',
    './app-src/part-03.txt',
    './app-src/qol-internal.txt',
    './app-src/qol-fixes.txt',
    './app-src/interaction-animations.txt',
    './app-src/randomizer-3d.txt',
    './app-src/three-loader-fix.txt',
    './app-src/part-04.txt'
  ];

  try {
    const responses = await Promise.all(parts.map(path => fetch(path, { cache: 'no-store' })));
    const failed = responses.find(response => !response.ok);
    if (failed) throw new Error(`Game source failed to load (${failed.status})`);
    const source = (await Promise.all(responses.map(response => response.text()))).join('');
    (0, eval)(`${source}\n//# sourceURL=forge-remote-table.bundle.js`);
  } catch (error) {
    console.error(error);
    const status = document.getElementById('setup-status');
    if (status) {
      status.textContent = 'The tabletop code could not load. Refresh the page and try again.';
      status.className = 'status error';
    }
  }
})();

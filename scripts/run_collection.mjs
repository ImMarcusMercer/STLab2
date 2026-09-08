// Minimal runner for this collection's Postman scripts; no npm dependencies.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const collection = JSON.parse(fs.readFileSync(new URL('../docs/student-information-api.postman_collection.json', import.meta.url)));
const variables = Object.fromEntries(collection.variable.map(v => [v.key, v.value]));
Object.assign(variables, JSON.parse(fs.readFileSync(0, 'utf8')));
const base = new URL(variables.base);
if (!['localhost', '127.0.0.1', '[::1]'].includes(base.hostname)) {
  throw new Error('The demonstration runner is restricted to localhost.');
}
const substitute = text => text.replace(/\{\{(\w+)\}\}/g, (_, key) => {
  assert.ok(key in variables, `Missing variable ${key}`);
  return variables[key];
});
let total = 0;
let assertions = 0;
for (const group of collection.item) {
  for (const item of group.item) {
    const pm = {
      info: { requestName: item.name },
      collectionVariables: { set: (key, value) => variables[key] = value },
      test: (name, fn) => { fn(); assertions++; },
      expect: value => ({ to: { equal: expected => assert.equal(value, expected) } }),
    };
    const sandbox = vm.createContext({ pm });
    const runScripts = (events, stage) => {
      for (const event of events || []) {
        if (event.listen === stage) vm.runInContext(event.script.exec.join('\n'), sandbox, { timeout: 2000 });
      }
    };
    runScripts(collection.event, 'prerequest');
    const request = item.request;
    const response = await fetch(substitute(request.url), {
      method: request.method,
      headers: Object.fromEntries(request.header.map(h => [h.key, substitute(h.value)])),
      ...(request.body ? { body: substitute(request.body.raw) } : {}),
      signal: AbortSignal.timeout(15000),
    });
    const body = await response.text();
    pm.response = {
      code: response.status,
      json: () => JSON.parse(body),
      to: { have: { status: expected => assert.equal(response.status, expected, item.name) } },
    };
    try {
      runScripts(item.event, 'test');
    } catch (error) {
      // Do not print response bodies, request bodies or variables: they may contain tokens.
      console.error(`FAIL ${item.name}: received HTTP ${response.status}; ${error.name}`);
      process.exit(1);
    }
    console.log(`PASS ${response.status} ${item.name}`);
    total++;
  }
}
console.log(`Completed ${total} HTTP requests and ${assertions} assertions.`);

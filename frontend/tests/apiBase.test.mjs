import test from "node:test";
import assert from "node:assert/strict";
import { normalizeApiBase } from "../src/services/apiBase.mjs";

test("uses a same-origin API path when no build variable is set", () => {
  assert.equal(normalizeApiBase(undefined), "/api");
  assert.equal(normalizeApiBase("   "), "/api");
});

test("removes all trailing slashes from configured API prefixes", () => {
  assert.equal(normalizeApiBase("https://api.example.test/v1///"), "https://api.example.test/v1");
  assert.equal(normalizeApiBase("/api///"), "/api");
});

#!/usr/bin/env node

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const SCHEMA_VERSION = '1.0.0';
const DEFAULT_ROOT = path.resolve(__dirname, '../data/dreams');
const BANNED_KEY = /empno|e-?mail|phone|contact|연락처|연구실|면담시간|password|passwd|cookie|session(?:id)?/i;
const EMAIL_VALUE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
const MOBILE_VALUE = /(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)/;
const LANDLINE_VALUE = /(?<!\d)0\d{1,2}[ -]\d{3,4}[ -]\d{4}(?!\d)/;

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function fail(message) {
  throw new Error(message);
}

function scanPrivacy(value, location = '$') {
  if (Array.isArray(value)) {
    value.forEach((item, index) => scanPrivacy(item, `${location}[${index}]`));
    return;
  }
  if (value && typeof value === 'object') {
    for (const [key, item] of Object.entries(value)) {
      if (BANNED_KEY.test(key)) fail(`banned key at ${location}.${key}`);
      scanPrivacy(item, `${location}.${key}`);
    }
    return;
  }
  if (typeof value === 'string') {
    if (EMAIL_VALUE.test(value)) fail(`email-like value at ${location}`);
    if (MOBILE_VALUE.test(value)) fail(`mobile-like value at ${location}`);
    if (LANDLINE_VALUE.test(value)) fail(`phone-like value at ${location}`);
  }
}

function readDataset(root, entry) {
  const absolutePath = path.join(root, entry.path);
  if (!fs.existsSync(absolutePath)) fail(`missing dataset: ${entry.path}`);
  const buffer = fs.readFileSync(absolutePath);
  if (buffer.length !== entry.bytes) fail(`byte count mismatch: ${entry.path}`);
  const checksum = sha256(buffer);
  if (checksum !== entry.sha256) fail(`checksum mismatch: ${entry.path}`);
  let value;
  try {
    value = JSON.parse(zlib.gunzipSync(buffer).toString('utf8'));
  } catch (error) {
    fail(`invalid gzip JSON ${entry.path}: ${error.message}`);
  }
  if (value.schemaVersion !== SCHEMA_VERSION) fail(`schema version mismatch: ${entry.path}`);
  scanPrivacy(value);
  return value;
}

function validateTerm(entry, value) {
  if (value.kind !== 'dreams-term-catalog') fail(`unexpected kind: ${entry.path}`);
  if (Number(value.academicYear) !== Number(entry.academicYear)) fail(`year mismatch: ${entry.path}`);
  if (String(value.termCode) !== String(entry.termCode)) fail(`term mismatch: ${entry.path}`);
  if (!Array.isArray(value.sections)) fail(`sections must be an array: ${entry.path}`);
  if (value.sections.length !== entry.records) fail(`record count mismatch: ${entry.path}`);
  if (value.collection?.storedSections !== entry.records) fail(`collection count mismatch: ${entry.path}`);
  if (value.collection?.developmentLimit !== null) fail(`development-limited archive is not publishable: ${entry.path}`);

  const seen = new Set();
  for (const [index, section] of value.sections.entries()) {
    if (!section.courseCode || !section.sectionCode || !section.koreanName) {
      fail(`missing section identity at ${entry.path} sections[${index}]`);
    }
    const key = `${section.courseCode}\u0000${section.sectionCode}`;
    if (seen.has(key)) fail(`duplicate section ${section.courseCode}-${section.sectionCode}: ${entry.path}`);
    seen.add(key);
    if (!['AVAILABLE', 'BLANK'].includes(section.detailStatus)) {
      fail(`unexpected detail status for ${section.courseCode}-${section.sectionCode}: ${entry.path}`);
    }
  }

  const observedCoverage = {
    available: value.sections.filter((section) => section.detailStatus === 'AVAILABLE').length,
    blankAtSource: value.sections.filter((section) => section.detailStatus === 'BLANK').length,
    withEnglishName: value.sections.filter((section) => section.englishName).length,
    withLocation: value.sections.filter((section) => section.rawLocation).length,
    withOverview: value.sections.filter((section) => section.syllabus?.overview).length,
    withWeeklyPlan: value.sections.filter((section) => section.syllabus?.weeklyPlans?.length).length,
  };
  if (JSON.stringify(observedCoverage) !== JSON.stringify(entry.detailCoverage)) {
    fail(`detail coverage mismatch: ${entry.path}`);
  }
  if (observedCoverage.available + observedCoverage.blankAtSource !== entry.records) {
    fail(`unaccounted detail records: ${entry.path}`);
  }
  return observedCoverage;
}

function validateCurriculum(entry, value) {
  if (value.kind !== 'dreams-curriculum') fail(`unexpected kind: ${entry.path}`);
  if (Number(value.academicYear) !== Number(entry.academicYear)) fail(`year mismatch: ${entry.path}`);
  if (!Array.isArray(value.departments)) fail(`departments must be an array: ${entry.path}`);
  const records = value.departments.reduce((sum, department) => {
    if (!department.departmentCode || !department.departmentName || !Array.isArray(department.courses)) {
      fail(`invalid curriculum department: ${entry.path}`);
    }
    return sum + department.courses.length;
  }, 0);
  if (value.departments.length !== entry.departments || records !== entry.records) {
    fail(`curriculum counts mismatch: ${entry.path}`);
  }
}

function validateRelations(entry, value) {
  if (value.kind !== 'dreams-course-relations') fail(`unexpected kind: ${entry.path}`);
  if (!Array.isArray(value.replacementCourses) || !Array.isArray(value.equivalentCourses)) {
    fail(`invalid relation arrays: ${entry.path}`);
  }
  if (value.replacementCourses.length !== entry.replacementRecords) fail(`replacement count mismatch: ${entry.path}`);
  if (value.equivalentCourses.length !== entry.equivalentRecords) fail(`equivalent count mismatch: ${entry.path}`);
}

function main() {
  const root = path.resolve(process.argv[2] || DEFAULT_ROOT);
  const manifestPath = path.join(root, 'manifest.json');
  if (!fs.existsSync(manifestPath)) fail(`missing manifest: ${manifestPath}`);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (manifest.schemaVersion !== SCHEMA_VERSION) fail('manifest schema version mismatch');
  if (!Array.isArray(manifest.datasets)) fail('manifest datasets must be an array');
  scanPrivacy(manifest);

  let sectionTermRecords = 0;
  let availableDetails = 0;
  let blankDetails = 0;
  for (const entry of manifest.datasets) {
    const value = readDataset(root, entry);
    if (entry.kind === 'term') {
      const coverage = validateTerm(entry, value);
      sectionTermRecords += entry.records;
      availableDetails += coverage.available;
      blankDetails += coverage.blankAtSource;
    } else if (entry.kind === 'curriculum') validateCurriculum(entry, value);
    else if (entry.kind === 'relations') validateRelations(entry, value);
    else fail(`unknown manifest kind: ${entry.kind}`);
  }

  const termDatasets = manifest.datasets.filter((entry) => entry.kind === 'term').length;
  const curricula = manifest.datasets.filter((entry) => entry.kind === 'curriculum').length;
  if (manifest.totals.datasets !== manifest.datasets.length) fail('manifest dataset total mismatch');
  if (manifest.totals.termDatasets !== termDatasets) fail('manifest term total mismatch');
  if (manifest.totals.sectionTermRecords !== sectionTermRecords) fail('manifest section total mismatch');
  if (manifest.totals.curricula !== curricula) fail('manifest curriculum total mismatch');

  const expectedTermFiles = manifest.requestedRange.years.length * manifest.requestedRange.terms.length;
  if (termDatasets !== expectedTermFiles) {
    fail(`term coverage incomplete: expected ${expectedTermFiles}, found ${termDatasets}`);
  }
  if (curricula !== manifest.requestedRange.years.length) {
    fail(`curriculum coverage incomplete: expected ${manifest.requestedRange.years.length}, found ${curricula}`);
  }
  if (!manifest.datasets.some((entry) => entry.kind === 'relations')) fail('course relations dataset is missing');

  console.log(JSON.stringify({
    valid: true,
    root,
    datasets: manifest.datasets.length,
    termDatasets,
    sectionTermRecords,
    availableDetails,
    blankDetails,
    curricula,
  }, null, 2));
}

try {
  main();
} catch (error) {
  console.error(`DREAMS archive validation failed: ${error.message}`);
  process.exitCode = 1;
}

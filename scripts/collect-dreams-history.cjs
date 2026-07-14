#!/usr/bin/env node

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const { chromium } = require('../e2e/node_modules/playwright');

const BASE_URL = 'https://dreams2.daejin.ac.kr';
const DEFAULT_CREDENTIALS_FILE = path.join(os.homedir(), '.claude/docs/credentials.md');
const DEFAULT_OUTPUT_ROOT = path.resolve(__dirname, '../data/dreams');
const SCHEMA_VERSION = '1.0.0';
const TERM_LABELS = {
  '1': '1학기',
  '2': '2학기',
  '11': '여름계절학기',
  '22': '겨울계절학기',
};
const CATEGORY_DEFINITIONS = [
  ['B41001', '교양필수'],
  ['B41002', '교양선택'],
  ['B41003', '이공기초교양'],
  ['B41004', '교직'],
  ['B41005', '전공'],
  ['B41006', '계열교양'],
  ['B41011', '계열교양(별도코드)'],
  ['B41020', '일반선택'],
];

function parseArgs(argv) {
  const options = {
    from: 2020,
    to: 2026,
    terms: ['1', '2', '11', '22'],
    concurrency: 6,
    force: false,
    limit: null,
    skipTerms: false,
    skipCurricula: false,
    skipRelations: false,
    outputRoot: process.env.DREAMS_OUTPUT_ROOT
      ? path.resolve(process.env.DREAMS_OUTPUT_ROOT)
      : DEFAULT_OUTPUT_ROOT,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    const next = () => {
      index += 1;
      if (index >= argv.length) throw new Error(`${argument} requires a value`);
      return argv[index];
    };
    if (argument === '--from') options.from = Number(next());
    else if (argument === '--to') options.to = Number(next());
    else if (argument === '--years') {
      const years = next().split(',').map(Number);
      options.from = Math.min(...years);
      options.to = Math.max(...years);
      options.explicitYears = new Set(years);
    } else if (argument === '--terms') options.terms = next().split(',').map(String);
    else if (argument === '--concurrency') options.concurrency = Number(next());
    else if (argument === '--limit') options.limit = Number(next());
    else if (argument === '--output') options.outputRoot = path.resolve(next());
    else if (argument === '--force') options.force = true;
    else if (argument === '--skip-terms') options.skipTerms = true;
    else if (argument === '--skip-curricula') options.skipCurricula = true;
    else if (argument === '--skip-relations') options.skipRelations = true;
    else if (argument === '--help') {
      console.log(`Usage: node scripts/collect-dreams-history.cjs [options]

Options:
  --from YEAR              first academic year (default: 2020)
  --to YEAR                last academic year (default: 2026)
  --years Y1,Y2            explicit academic years
  --terms 1,2,11,22        term codes to collect
  --concurrency N          syllabus page workers (default: 6)
  --limit N                development-only per-term section limit
  --output PATH            archive root (default: data/dreams)
  --force                  replace valid existing archives
  --skip-terms             skip term collection
  --skip-curricula         skip curriculum collection
  --skip-relations         skip replacement/equivalent relations

Credentials are read from DREAMS_ID/DREAMS_PW/DREAMS_SSO_URL or from
DREAMS_CREDENTIALS_FILE (default: ${DEFAULT_CREDENTIALS_FILE}).`);
      process.exit(0);
    } else throw new Error(`unknown argument: ${argument}`);
  }

  if (!Number.isInteger(options.from) || !Number.isInteger(options.to) || options.from > options.to) {
    throw new Error('invalid year range');
  }
  if (!Number.isInteger(options.concurrency) || options.concurrency < 1 || options.concurrency > 12) {
    throw new Error('--concurrency must be between 1 and 12');
  }
  if (options.limit !== null && (!Number.isInteger(options.limit) || options.limit < 1)) {
    throw new Error('--limit must be a positive integer');
  }
  for (const term of options.terms) {
    if (!TERM_LABELS[term]) throw new Error(`unsupported term code: ${term}`);
  }
  return options;
}

function readCredentials() {
  if (process.env.DREAMS_ID && process.env.DREAMS_PW) {
    return {
      id: process.env.DREAMS_ID,
      password: process.env.DREAMS_PW,
      ssoUrl: process.env.DREAMS_SSO_URL || `${BASE_URL}/`,
    };
  }

  const credentialsFile = process.env.DREAMS_CREDENTIALS_FILE || DEFAULT_CREDENTIALS_FILE;
  const document = fs.readFileSync(credentialsFile, 'utf8');
  const section = document.split(/^### 대진대학교 포털.*$/m)[1]?.split(/^### /m)[0] || '';
  const field = (label) => {
    const line = section.split('\n').find((candidate) => label.test(candidate));
    return line?.split(/[:：]/).slice(1).join(':').trim().replace(/^`|`$/g, '') || null;
  };
  const id = field(/학번\(ID\)|학번|교번/i);
  const password = field(/비밀번호|password|PW/i);
  const ssoUrl = field(/SSO 로그인 진입/i);
  if (!id || !password || !ssoUrl) {
    throw new Error(`DREAMS credentials were not found in ${credentialsFile}`);
  }
  return { id, password, ssoUrl };
}

function yearsFor(options) {
  const years = [];
  for (let year = options.from; year <= options.to; year += 1) {
    if (!options.explicitYears || options.explicitYears.has(year)) years.push(year);
  }
  return years;
}

function normalizeText(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
}

function nullableText(value) {
  const normalized = normalizeText(value);
  return normalized || null;
}

function numberOrNull(value) {
  const normalized = normalizeText(value).replace(/,/g, '');
  if (!normalized) return null;
  const result = Number(normalized.replace(/%$/, ''));
  return Number.isFinite(result) ? result : null;
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function log(message) {
  const stamp = new Date().toISOString().slice(11, 19);
  console.log(`[${stamp}] ${message}`);
}

function uniqueBy(items, key) {
  const seen = new Set();
  return items.filter((item) => {
    const value = key(item);
    if (seen.has(value)) return false;
    seen.add(value);
    return true;
  });
}

function sanitizeText(value) {
  return normalizeText(value)
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[개인정보 제거]')
    .replace(/(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)/g, '[개인정보 제거]')
    .replace(/(?<!\d)0\d{1,2}[ -]?\d{3,4}[ -]?\d{4}(?!\d)/g, '[개인정보 제거]');
}

function sanitizeDeep(value) {
  if (Array.isArray(value)) return value.map(sanitizeDeep);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, sanitizeDeep(item)]));
  }
  return typeof value === 'string' ? sanitizeText(value) : value;
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function writeGzipJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const serialized = `${JSON.stringify(value, null, 2)}\n`;
  const compressed = zlib.gzipSync(Buffer.from(serialized, 'utf8'), { level: 9, mtime: 0 });
  const temporary = `${filePath}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, compressed);
  fs.renameSync(temporary, filePath);
  return { bytes: compressed.length, sha256: sha256(compressed) };
}

function readGzipJson(filePath) {
  return JSON.parse(zlib.gunzipSync(fs.readFileSync(filePath)).toString('utf8'));
}

function isReusableArchive(filePath, expectedKind, expectedYear, expectedTerm = null) {
  if (!fs.existsSync(filePath)) return false;
  try {
    const value = readGzipJson(filePath);
    if (value.schemaVersion !== SCHEMA_VERSION || value.kind !== expectedKind) return false;
    if (Number(value.academicYear) !== expectedYear) return false;
    if (expectedTerm !== null && String(value.termCode) !== String(expectedTerm)) return false;
    return true;
  } catch {
    return false;
  }
}

async function withRetries(label, operation, attempts = 4) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await operation(attempt);
    } catch (error) {
      lastError = error;
      if (attempt < attempts) await sleep(250 * attempt);
    }
  }
  throw new Error(`${label} failed after ${attempts} attempts: ${lastError?.message || lastError}`);
}

async function login(page, credentials) {
  log('DREAMS2 SSO login');
  await page.goto(credentials.ssoUrl, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.getByPlaceholder('학번(교번)').fill(credentials.id);
  await page.getByPlaceholder('비밀번호').fill(credentials.password);
  const submit = page.locator('input[type="submit"][value="로그인"]');
  if (await submit.count()) await submit.first().click();
  else await page.getByRole('button', { name: '로그인', exact: true }).last().click();
  await page.waitForLoadState('domcontentloaded');
  const confirmation = page.getByText('확인', { exact: true });
  if (await confirmation.count()) await confirmation.first().click().catch(() => {});
  await page.goto(`${BASE_URL}/sugang/LinkPortal.jsp?dvd=P`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  const response = await page.goto(`${BASE_URL}/sugang/new/sugang_wlsn0120.jsp`, {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  if (!response || !response.ok()) throw new Error('DREAMS2 course catalog session initialization failed');
  log('DREAMS2 session initialized');
}

function decodeEucKr(buffer) {
  return new TextDecoder('euc-kr').decode(buffer).replace(/^\uFEFF/, '');
}

async function postJson(context, endpoint, body) {
  return withRetries(endpoint, async () => {
    const response = await context.request.post(`${BASE_URL}${endpoint}`, {
      data: body,
      headers: { 'Content-Type': 'application/json; charset=UTF-8' },
      timeout: 30_000,
    });
    if (!response.ok()) throw new Error(`HTTP ${response.status()}`);
    const text = decodeEucKr(await response.body()).trim();
    if (!text) return {};
    return JSON.parse(text);
  });
}

async function collectAcademicUnits(page, years) {
  const result = new Map();
  for (const year of years) {
    log(`${year} academic-unit map`);
    await page.goto(`${BASE_URL}/sugang/center/WlsnEdu0101.jsp?yyyy=${year}`, {
      waitUntil: 'domcontentloaded',
      timeout: 30_000,
    });
    const colleges = await page.locator('select[name="gsCd"] option').evaluateAll((options) =>
      options
        .map((option) => ({ code: option.value.trim(), name: option.textContent.replace(/\s+/g, ' ').trim() }))
        .filter((option) => option.code),
    );

    const units = [];
    for (const college of colleges) {
      await page.goto(
        `${BASE_URL}/sugang/center/WlsnEdu0101.jsp?yyyy=${year}&gsCd=${encodeURIComponent(college.code)}`,
        { waitUntil: 'domcontentloaded', timeout: 30_000 },
      );
      const departments = await page.locator('select[name="deptCd"] option').evaluateAll((options) =>
        options
          .map((option) => ({ code: option.value.trim(), name: option.textContent.replace(/\s+/g, ' ').trim() }))
          .filter((option) => option.code),
      );
      for (const department of departments) {
        units.push({
          collegeCode: college.code,
          collegeName: college.name,
          departmentCode: department.code,
          departmentName: department.name,
        });
      }
    }
    const uniqueUnits = uniqueBy(units, (unit) => unit.departmentCode).sort((left, right) =>
      left.departmentCode.localeCompare(right.departmentCode),
    );
    result.set(year, uniqueUnits);
    log(`${year} academic units: ${colleges.length} colleges, ${uniqueUnits.length} departments`);
  }
  return result;
}

async function submitCurriculum(page, year, unit) {
  await page.goto(
    `${BASE_URL}/sugang/center/WlsnEdu0101.jsp?yyyy=${year}&gsCd=${encodeURIComponent(unit.collegeCode)}`,
    { waitUntil: 'domcontentloaded', timeout: 30_000 },
  );
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30_000 }),
    page.evaluate(({ yearValue, collegeCode, departmentCode }) => {
      const form = document.createElement('form');
      form.method = 'post';
      form.action = '/sugang/center/WlsnEdu0102.jsp';
      for (const [name, value] of Object.entries({
        yyyy: String(yearValue),
        gsCd: collegeCode,
        deptCd: departmentCode,
      })) {
        const input = document.createElement('input');
        input.name = name;
        input.value = value;
        form.appendChild(input);
      }
      document.body.appendChild(form);
      form.submit();
    }, { yearValue: year, collegeCode: unit.collegeCode, departmentCode: unit.departmentCode }),
  ]);

  return page.locator('table').evaluateAll((tables) => {
    const clean = (value) => value.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
    const table = tables.find((candidate) => {
      const first = candidate.rows[0];
      if (!first) return false;
      const header = [...first.cells].map((cell) => clean(cell.innerText));
      return header.includes('이수구분') && header.includes('교과목명') && header.includes('강의TYPE');
    });
    if (!table) return [];
    return [...table.rows].slice(1).map((row) => [...row.cells].map((cell) => clean(cell.innerText)));
  });
}

async function collectCurriculum(page, outputRoot, year, units, collectedAt, force) {
  const filePath = path.join(outputRoot, 'curricula', `curriculum-${year}.json.gz`);
  if (!force && isReusableArchive(filePath, 'dreams-curriculum', year)) {
    log(`${year} curriculum: reuse existing archive`);
    return;
  }

  log(`${year} curriculum: ${units.length} departments`);
  const departments = [];
  for (let index = 0; index < units.length; index += 1) {
    const unit = units[index];
    const rawRows = await withRetries(
      `${year} curriculum ${unit.departmentCode}`,
      () => submitCurriculum(page, year, unit),
      3,
    );
    const courses = rawRows
      .map((cells) => ({
        grade: numberOrNull(cells[0]),
        recommendedTerm: nullableText(cells[1]),
        completionCategory: nullableText(cells[2]),
        courseName: nullableText(cells[3]),
        credits: numberOrNull(cells[4]),
        lectureHours: numberOrNull(cells[5]),
        practiceHours: numberOrNull(cells[6]),
        lectureType: nullableText(cells[7]),
      }))
      .filter((course) => course.courseName);
    departments.push({ ...unit, courses });
    if ((index + 1) % 20 === 0 || index + 1 === units.length) {
      log(`${year} curriculum: ${index + 1}/${units.length}`);
    }
  }

  const archive = sanitizeDeep({
    schemaVersion: SCHEMA_VERSION,
    kind: 'dreams-curriculum',
    academicYear: year,
    collectedAt,
    source: {
      system: '대진대학교 DREAMS2 수강편람',
      endpoint: '/sugang/center/WlsnEdu0102.jsp',
    },
    departments,
  });
  const stats = writeGzipJson(filePath, archive);
  const courseRows = departments.reduce((sum, department) => sum + department.courses.length, 0);
  log(`${year} curriculum saved: ${courseRows} rows, ${stats.bytes} bytes`);
}

async function fetchCourseRows(context, year, term, params) {
  const data = await postJson(context, '/sugang/NSugangWlsn0120?cmd=list', {
    ...params,
    fhd_yyyy: String(year),
    fhd_shtm: String(term),
  });
  return Array.isArray(data.resultList) ? data.resultList : [];
}

async function collectTermIndex(context, year, term, units) {
  const records = new Map();
  const categoryCounts = [];
  const areaCounts = [];
  const departmentCounts = [];

  const merge = (row, categoryContext = null, departmentContext = null) => {
    const courseCode = normalizeText(row.curiNo);
    const sectionCode = normalizeText(row.clssNo);
    if (!courseCode || !sectionCode) return;
    const key = `${courseCode}\u0000${sectionCode}`;
    let record = records.get(key);
    if (!record) {
      record = {
        courseCode,
        sectionCode,
        koreanName: nullableText(row.cousNm),
        professorName: nullableText(row.profNm),
        completionCategory: nullableText(row.korNm),
        credits: numberOrNull(row.pnt),
        rawLectureTime: nullableText(row.lectTm),
        categoryContexts: [],
        departmentContexts: [],
        _detailToken: normalizeText(row.empno),
      };
      records.set(key, record);
    } else if (!record._detailToken && row.empno) {
      record._detailToken = normalizeText(row.empno);
    }
    if (categoryContext) {
      const signature = JSON.stringify(categoryContext);
      if (!record.categoryContexts.some((context) => JSON.stringify(context) === signature)) {
        record.categoryContexts.push(categoryContext);
      }
    }
    if (departmentContext) {
      if (!record.departmentContexts.some((context) => context.departmentCode === departmentContext.departmentCode)) {
        record.departmentContexts.push(departmentContext);
      }
    }
  };

  for (const [code, name] of CATEGORY_DEFINITIONS) {
    const rows = await fetchCourseRows(context, year, term, { ic_kwa: code });
    rows.forEach((row) => merge(row, { code, name }));
    categoryCounts.push({ code, name, rows: rows.length });
  }

  const areasData = await postJson(context, '/sugang/NCommonCode?cmd=sust', {
    selectYear: `${year}${term}`,
  });
  const areas = (areasData.resultList || []).map((row) => ({
    code: normalizeText(row.comm_cd),
    name: normalizeText(row.kor_nm),
  })).filter((area) => area.code);
  for (const area of areas) {
    const rows = await fetchCourseRows(context, year, term, { ic_kwa: 'B41002', ic_kwa_2: area.code });
    rows.forEach((row) => merge(row, { code: 'B41002', name: '교양선택', areaCode: area.code, areaName: area.name }));
    areaCounts.push({ ...area, rows: rows.length });
  }

  for (const unit of units) {
    const rows = await fetchCourseRows(context, year, term, { ic_kwa: 'B41005', ic_kwa_1: unit.departmentCode });
    const contextValue = {
      collegeCode: unit.collegeCode,
      collegeName: unit.collegeName,
      departmentCode: unit.departmentCode,
      departmentName: unit.departmentName,
    };
    rows.forEach((row) => merge(row, { code: 'B41005', name: '전공' }, contextValue));
    if (rows.length) departmentCounts.push({ ...contextValue, rows: rows.length });
  }

  return {
    records: [...records.values()].sort((left, right) =>
      left.courseCode.localeCompare(right.courseCode) || left.sectionCode.localeCompare(right.sectionCode),
    ),
    querySummary: { categoryCounts, areaCounts, departmentCounts },
  };
}

async function parseDetailPage(page) {
  return page.evaluate(() => {
    const clean = (value) => (value || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
    const rows = (table) => [...table.rows].map((row) => [...row.cells].map((cell) => clean(cell.innerText)));
    const tables = [...document.querySelectorAll('table')];
    const smallestTable = (predicate) => tables
      .filter(predicate)
      .sort((left, right) => clean(left.innerText).length - clean(right.innerText).length)[0];
    const summaryTable = smallestTable((table) => {
      const directCells = rows(table).flat();
      return directCells.includes('교과목명(국문)') && directCells.includes('교과번호-분반');
    });
    if (!summaryTable) return { status: 'BLANK', summary: {}, syllabus: null };

    const summaryRows = rows(summaryTable);
    const labelValue = (label) => {
      for (const row of summaryRows) {
        const index = row.findIndex((cell) => cell === label || cell.replace(/\s+/g, '') === label.replace(/\s+/g, ''));
        if (index >= 0) return row[index + 1] || '';
      }
      return '';
    };
    const hours = labelValue('학점/강의 /실습').split('/').map(clean);

    const tableWithHeaders = (...headers) => smallestTable((table) =>
      rows(table).some((row) => headers.every((header) => row.includes(header))),
    );
    const afterHeading = (prefix) => {
      for (const table of tables) {
        const directRows = [...table.rows];
        for (let index = 0; index < directRows.length - 1; index += 1) {
          const current = clean(directRows[index].innerText);
          if (current.startsWith(prefix) && current.length < prefix.length + 80) {
            return clean(directRows[index + 1].innerText);
          }
        }
      }
      return '';
    };
    const dataRowsAfterHeader = (table, headerMatcher) => {
      if (!table) return [];
      const all = rows(table);
      const index = all.findIndex(headerMatcher);
      return index >= 0 ? all.slice(index + 1) : [];
    };

    const coreTable = tableWithHeaders('핵심역량', '수업목표');
    const majorTable = tableWithHeaders('전공역량', '수업목표');
    const teachingTable = tableWithHeaders('방법', '개요');
    const evaluationTable = smallestTable((table) => rows(table).some((row) =>
      row.includes('평가요소') && row.some((cell) => cell.includes('반영비율')),
    ));
    const textbookTable = tableWithHeaders('번호', '구분', '교재명', '저자', '출판사', '출판년도');
    const assignmentTable = smallestTable((table) => rows(table).some((row) =>
      row.some((cell) => cell.includes('과 제 명')) && row.includes('피드백일자'),
    ));
    const weeklyTable = smallestTable((table) => rows(table).some((row) =>
      (row.includes('주차') || row.includes('주'))
        && row.includes('수업주제')
        && row.includes('주요 학습내용')
        && row.includes('수업방법')
        && row.includes('선행학습 및 준비사항')
        && row.includes('교재 및 참고자료'),
    ));
    const formatTable = smallestTable((table) => {
      const directCells = rows(table).flat();
      return directCells.some((cell) => cell.includes('이론수업('))
        && directCells.some((cell) => cell.includes('온라인수업('));
    });
    const mediaTable = smallestTable((table) => {
      const directCells = rows(table).flat();
      return directCells.includes('빔프로젝터') && directCells.includes('전자칠판');
    });

    const competencyRows = (table, header) => dataRowsAfterHeader(table, (row) => row.includes(header) && row.includes('수업목표'))
      .filter((row) => row[0] && row[1]?.includes('%') && !row[0].startsWith('※'))
      .map((row) => ({ name: row[0], weighting: row[1] || '', objective: row.slice(2).join(' ') }));

    const modernCoreCompetencies = competencyRows(coreTable, '핵심역량');
    const legacyCoreTable = smallestTable((table) => {
      const directCells = rows(table).flat();
      return directCells.includes('인성역량')
        && directCells.includes('소통역량')
        && directCells.includes('창의융합역량')
        && directCells.some((cell) => /^\d+%$/.test(cell));
    });
    const legacyCoreCompetencies = legacyCoreTable
      ? rows(legacyCoreTable).flatMap((row) => {
          const result = [];
          for (let index = 0; index + 1 < row.length; index += 2) {
            if (row[index] && /^\d+%$/.test(row[index + 1])) {
              result.push({ name: row[index], weighting: row[index + 1], objective: '' });
            }
          }
          return result;
        })
      : [];
    const modernMajorCompetencies = competencyRows(majorTable, '전공역량');
    const legacyMajorTable = smallestTable((table) => {
      const text = clean(table.innerText);
      return text.includes('공통역량') && /:\s*\d+%/.test(text) && text.length < 1000;
    });
    const legacyMajorCompetencies = [];
    if (legacyMajorTable) {
      const text = clean(legacyMajorTable.innerText);
      const expression = /([^:%]+?)\s*:\s*(\d+%)/g;
      for (const match of text.matchAll(expression)) {
        const name = clean(match[1]);
        if (name) legacyMajorCompetencies.push({ name, weighting: match[2], objective: '' });
      }
    }

    const classFormats = [];
    if (formatTable) {
      const expression = /([^()]+)\(\s*●\s*\)/g;
      for (const cell of rows(formatTable).flat()) {
        for (const match of cell.matchAll(expression)) {
          const name = clean(match[1].split(')').pop());
          if (name) classFormats.push(name);
        }
      }
    }

    const teachingMethods = dataRowsAfterHeader(teachingTable, (row) => row.includes('방법') && row.includes('개요'))
      .filter((row) => row.includes('●'))
      .map((row) => ({ method: row[0] || '', description: row[row.length - 1] || '' }));

    const media = [];
    if (mediaTable) {
      const mediaRows = rows(mediaTable);
      for (let index = 0; index + 1 < mediaRows.length; index += 2) {
        const names = mediaRows[index];
        const selected = mediaRows[index + 1];
        names.forEach((name, cellIndex) => {
          if (name && selected[cellIndex]?.includes('●')) media.push(name);
        });
      }
    }

    const evaluations = dataRowsAfterHeader(evaluationTable, (row) => row.includes('평가요소') && row.some((cell) => cell.includes('반영비율')))
      .filter((row) => row[0])
      .map((row) => ({ element: row[0], weight: row[1] || '', criteria: row.slice(2).join(' ') }));

    const textbooks = dataRowsAfterHeader(textbookTable, (row) => row.includes('교재명') && row.includes('저자'))
      .filter((row) => row.slice(1).some(Boolean))
      .map((row) => ({
        number: row[0] || '', type: row[1] || '', title: row[2] || '', author: row[3] || '',
        publisher: row[4] || '', publicationYear: row[5] || '',
      }));

    const assignments = dataRowsAfterHeader(assignmentTable, (row) => row.some((cell) => cell.includes('과 제 명')))
      .filter((row) => row.slice(1, 4).some(Boolean))
      .map((row) => ({
        number: row[0] || '', title: row[1] || '', type: row[2] || '', reference: row[3] || '',
        dueDate: row[4] || '', feedbackDate: row[5] || '',
      }));

    const weeklyPlans = [];
    if (weeklyTable) {
      const allRows = rows(weeklyTable);
      const headerIndex = allRows.findIndex((row) => (row.includes('주차') || row.includes('주')) && row.includes('수업주제'));
      const hasDateColumn = allRows[headerIndex]?.includes('월/일');
      let currentWeek = '';
      for (const row of allRows.slice(headerIndex + 1)) {
        if (!row.some(Boolean)) continue;
        let values = row;
        const fullRowLength = hasDateColumn ? 7 : 6;
        if (row.length >= fullRowLength) currentWeek = row[0] || currentWeek;
        else values = [currentWeek, ...row];
        if (hasDateColumn) {
          weeklyPlans.push({
            week: values[0] || currentWeek,
            date: values[1] || '',
            topic: values[2] || '',
            content: values[3] || '',
            method: values[4] || '',
            preparation: values[5] || '',
            references: values[6] || '',
          });
        } else {
          weeklyPlans.push({
            week: values[0] || currentWeek,
            date: '',
            topic: values[1] || '',
            content: values[2] || '',
            method: values[3] || '',
            preparation: values[4] || '',
            references: values[5] || '',
          });
        }
      }
    }

    return {
      status: 'AVAILABLE',
      summary: {
        englishName: labelValue('교과목명(영문)'),
        completionCategory: labelValue('교과구분'),
        rawLectureTime: labelValue('수업시간'),
        rawLocation: labelValue('수업장소'),
        targetGrade: labelValue('수강대상'),
        credits: hours[0] || '',
        lectureHours: hours[1] || '',
        practiceHours: hours[2] || '',
      },
      syllabus: {
        overview: afterHeading('1. 수업의 개요와 유용성'),
        prerequisites: afterHeading('2. 선행학습 및 선수과목 요건'),
        learningObjectives: afterHeading('3. 수업목표'),
        coreCompetencies: modernCoreCompetencies.length ? modernCoreCompetencies : legacyCoreCompetencies,
        majorCompetencies: modernMajorCompetencies.length ? modernMajorCompetencies : legacyMajorCompetencies,
        classFormats: [...new Set(classFormats)],
        teachingMethods,
        media: [...new Set(media)],
        evaluations,
        textbooks,
        assignments,
        weeklyPlans,
        linkedPrograms: (() => {
          const value = afterHeading('11. 연계 비교과 프로그램');
          return value.includes('장애학생') ? '' : value;
        })(),
      },
    };
  });
}

async function collectDetail(page, year, term, record) {
  const query = new URLSearchParams({
    fhd_00: record.courseCode,
    fhd_01: record.sectionCode,
    fhd_02: String(year),
    fhd_03: String(term),
    fhd_04: record._detailToken,
  });
  return withRetries(`${year}-${term} ${record.courseCode}-${record.sectionCode} detail`, async (attempt) => {
    const response = await page.goto(`${BASE_URL}/sugang/center/Blsn020303.jsp?${query}`, {
      waitUntil: 'load',
      timeout: 30_000,
    });
    if (!response || !response.ok()) throw new Error(`HTTP ${response?.status() || 'no response'}`);
    await page.waitForTimeout(75);
    try {
      return await parseDetailPage(page);
    } catch (error) {
      if (attempt === 4 && /Execution context was destroyed/i.test(error.message)) {
        return { status: 'BLANK', summary: {}, syllabus: null };
      }
      throw error;
    }
  }, 4);
}

function mergeDetail(record, rawDetail) {
  const detail = sanitizeDeep(rawDetail);
  const summary = detail.summary || {};
  return {
    courseCode: record.courseCode,
    sectionCode: record.sectionCode,
    koreanName: record.koreanName,
    englishName: nullableText(summary.englishName),
    professorName: record.professorName,
    completionCategory: nullableText(summary.completionCategory) || record.completionCategory,
    credits: numberOrNull(summary.credits) ?? record.credits,
    lectureHours: numberOrNull(summary.lectureHours),
    practiceHours: numberOrNull(summary.practiceHours),
    rawLectureTime: nullableText(summary.rawLectureTime) || record.rawLectureTime,
    rawLocation: nullableText(summary.rawLocation),
    targetGrade: nullableText(summary.targetGrade),
    listingStatus: 'LISTED',
    detailStatus: detail.status,
    categoryContexts: record.categoryContexts.sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right))),
    departmentContexts: record.departmentContexts.sort((left, right) => left.departmentCode.localeCompare(right.departmentCode)),
    syllabus: detail.status === 'AVAILABLE' ? detail.syllabus : null,
  };
}

async function collectDetails(context, year, term, records, concurrency) {
  if (!records.length) return [];
  const results = new Array(records.length);
  let cursor = 0;
  let completed = 0;
  const pages = await Promise.all(Array.from({ length: Math.min(concurrency, records.length) }, () => context.newPage()));

  await Promise.all(pages.map(async (page) => {
    while (true) {
      const index = cursor;
      cursor += 1;
      if (index >= records.length) break;
      results[index] = mergeDetail(records[index], await collectDetail(page, year, term, records[index]));
      completed += 1;
      if (completed % 100 === 0 || completed === records.length) {
        log(`${year}-${term} syllabus: ${completed}/${records.length}`);
      }
      await sleep(25);
    }
  }));

  await Promise.all(pages.map((page) => page.close()));
  return results;
}

function dataStatus(year, term, sectionCount) {
  if (sectionCount === 0) return 'EMPTY_FUTURE';
  if (year < 2026) return 'FINAL';
  if (year > 2026) return 'PRELIMINARY';
  if (term === '1') return 'FINAL';
  if (term === '11') return 'CURRENT';
  return 'PRELIMINARY';
}

async function collectTerm(context, outputRoot, year, term, units, collectedAt, options) {
  const filePath = path.join(outputRoot, 'terms', `${year}-${term}.json.gz`);
  if (!options.force && isReusableArchive(filePath, 'dreams-term-catalog', year, term)) {
    log(`${year}-${term}: reuse existing archive`);
    return;
  }

  log(`${year}-${term} index collection`);
  const { records: allRecords, querySummary } = await collectTermIndex(context, year, term, units);
  const records = options.limit === null ? allRecords : allRecords.slice(0, options.limit);
  log(`${year}-${term} unique sections: ${allRecords.length}${options.limit ? ` (limited to ${records.length})` : ''}`);
  const sections = await collectDetails(context, year, term, records, options.concurrency);
  const status = dataStatus(year, term, sections.length);
  const detailCoverage = {
    available: sections.filter((section) => section.detailStatus === 'AVAILABLE').length,
    blankAtSource: sections.filter((section) => section.detailStatus === 'BLANK').length,
    withEnglishName: sections.filter((section) => section.englishName).length,
    withLocation: sections.filter((section) => section.rawLocation).length,
    withOverview: sections.filter((section) => section.syllabus?.overview).length,
    withWeeklyPlan: sections.filter((section) => section.syllabus?.weeklyPlans?.length).length,
  };
  const archive = {
    schemaVersion: SCHEMA_VERSION,
    kind: 'dreams-term-catalog',
    academicYear: year,
    termCode: term,
    termName: TERM_LABELS[term],
    dataStatus: status,
    collectedAt,
    source: {
      system: '대진대학교 DREAMS2 수강편람',
      catalogEndpoint: '/sugang/NSugangWlsn0120?cmd=list',
      syllabusEndpoint: '/sugang/center/Blsn020303.jsp',
      closedCourseStatusAvailable: false,
    },
    collection: {
      discoveredSections: allRecords.length,
      storedSections: sections.length,
      developmentLimit: options.limit,
      querySummary,
      detailCoverage,
    },
    sections,
  };
  const stats = writeGzipJson(filePath, archive);
  log(`${year}-${term} saved: ${sections.length} sections, ${stats.bytes} bytes`);
}

async function extractRelationTable(page, pagePath, requiredHeaders) {
  await page.goto(`${BASE_URL}${pagePath}`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  return page.locator('table').evaluateAll((tables, headers) => {
    const clean = (value) => (value || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
    for (const table of tables) {
      const allRows = [...table.rows].map((row) => [...row.cells].map((cell) => clean(cell.innerText)));
      const headerIndex = allRows.findIndex((row) => headers.every((header) => row.includes(header)));
      if (headerIndex >= 0) return allRows.slice(headerIndex + 1).filter((row) => row.some(Boolean));
    }
    return [];
  }, requiredHeaders);
}

async function collectRelations(page, outputRoot, collectedAt, force) {
  const filePath = path.join(outputRoot, 'relations.json.gz');
  if (!force && fs.existsSync(filePath)) {
    try {
      const existing = readGzipJson(filePath);
      if (existing.schemaVersion === SCHEMA_VERSION && existing.kind === 'dreams-course-relations') {
        log('course relations: reuse existing archive');
        return;
      }
    } catch {}
  }

  log('replacement/equivalent course relations');
  const replacementRows = await extractRelationTable(
    page,
    '/sugang/sugang_wlsn1032.jsp?fg=N&selectName=',
    ['년도', '과목명', '대체과목명'],
  );
  const equivalentRows = await extractRelationTable(
    page,
    '/sugang/center/Blsn040202.jsp?fg=N&selectName=',
    ['지정년도', '과목명', '동일과목명'],
  );
  const replacementCourses = replacementRows.map((row) => ({
    designatedYear: nullableText(row[0]),
    originalCourseName: nullableText(row[1]),
    originalCategory: nullableText(row[2]),
    originalCredits: numberOrNull(row[3]),
    originalDepartment: nullableText(row[4]),
    replacementCourseName: nullableText(row[5]),
    replacementCategory: nullableText(row[6]),
    replacementCredits: numberOrNull(row[7]),
    replacementDepartment: nullableText(row[8]),
    note: nullableText(row[9]),
  })).filter((row) => row.originalCourseName || row.replacementCourseName);
  const equivalentCourses = equivalentRows.map((row) => ({
    designatedYear: nullableText(row[0]),
    designatedTerm: nullableText(row[1]),
    originalCourseName: nullableText(row[2]),
    originalCategory: nullableText(row[3]),
    originalCollege: nullableText(row[4]),
    originalDepartment: nullableText(row[5]),
    equivalentCourseName: nullableText(row[6]),
    equivalentCategory: nullableText(row[7]),
    note: nullableText(row[8]),
  })).filter((row) => row.originalCourseName || row.equivalentCourseName);
  const archive = sanitizeDeep({
    schemaVersion: SCHEMA_VERSION,
    kind: 'dreams-course-relations',
    collectedAt,
    source: {
      system: '대진대학교 DREAMS2 수강편람',
      replacementEndpoint: '/sugang/sugang_wlsn1032.jsp',
      equivalentEndpoint: '/sugang/center/Blsn040202.jsp',
    },
    replacementCourses,
    equivalentCourses,
  });
  const stats = writeGzipJson(filePath, archive);
  log(`course relations saved: ${replacementCourses.length} replacement, ${equivalentCourses.length} equivalent, ${stats.bytes} bytes`);
}

function buildManifest(outputRoot, years, terms, collectedAt) {
  const datasets = [];
  const termDirectory = path.join(outputRoot, 'terms');
  const termFiles = fs.existsSync(termDirectory)
    ? fs.readdirSync(termDirectory).filter((file) => /^\d{4}-(?:1|2|11|22)\.json\.gz$/.test(file))
    : [];
  for (const file of termFiles) {
    const absolutePath = path.join(termDirectory, file);
    const buffer = fs.readFileSync(absolutePath);
    const archive = JSON.parse(zlib.gunzipSync(buffer).toString('utf8'));
    datasets.push({
      kind: 'term',
      path: path.relative(outputRoot, absolutePath).replaceAll(path.sep, '/'),
      academicYear: Number(archive.academicYear),
      termCode: String(archive.termCode),
      dataStatus: archive.dataStatus,
      records: archive.sections.length,
      detailCoverage: archive.collection.detailCoverage,
      bytes: buffer.length,
      sha256: sha256(buffer),
    });
  }

  const curriculumDirectory = path.join(outputRoot, 'curricula');
  const curriculumFiles = fs.existsSync(curriculumDirectory)
    ? fs.readdirSync(curriculumDirectory).filter((file) => /^curriculum-\d{4}\.json\.gz$/.test(file))
    : [];
  for (const file of curriculumFiles) {
    const absolutePath = path.join(curriculumDirectory, file);
    const buffer = fs.readFileSync(absolutePath);
    const archive = JSON.parse(zlib.gunzipSync(buffer).toString('utf8'));
    datasets.push({
      kind: 'curriculum',
      path: path.relative(outputRoot, absolutePath).replaceAll(path.sep, '/'),
      academicYear: Number(archive.academicYear),
      departments: archive.departments.length,
      records: archive.departments.reduce((sum, department) => sum + department.courses.length, 0),
      bytes: buffer.length,
      sha256: sha256(buffer),
    });
  }
  const relationsPath = path.join(outputRoot, 'relations.json.gz');
  if (fs.existsSync(relationsPath)) {
    const buffer = fs.readFileSync(relationsPath);
    const archive = JSON.parse(zlib.gunzipSync(buffer).toString('utf8'));
    datasets.push({
      kind: 'relations',
      path: path.relative(outputRoot, relationsPath).replaceAll(path.sep, '/'),
      replacementRecords: archive.replacementCourses.length,
      equivalentRecords: archive.equivalentCourses.length,
      records: archive.replacementCourses.length + archive.equivalentCourses.length,
      bytes: buffer.length,
      sha256: sha256(buffer),
    });
  }
  datasets.sort((left, right) => left.path.localeCompare(right.path));
  const termDatasets = datasets.filter((dataset) => dataset.kind === 'term');
  const archivedYears = [...new Set(termDatasets.map((dataset) => dataset.academicYear))].sort((left, right) => left - right);
  const archivedTerms = [...new Set(termDatasets.map((dataset) => dataset.termCode))].sort((left, right) => Number(left) - Number(right));
  const manifest = {
    schemaVersion: SCHEMA_VERSION,
    generatedAt: collectedAt,
    source: {
      system: '대진대학교 DREAMS2 수강편람',
      authenticatedCollection: true,
      credentialsStored: false,
      privateInstructorFieldsStored: false,
    },
    requestedRange: {
      years: archivedYears.length ? archivedYears : years,
      terms: archivedTerms.length ? archivedTerms : terms,
    },
    totals: {
      datasets: datasets.length,
      termDatasets: termDatasets.length,
      sectionTermRecords: termDatasets.reduce((sum, dataset) => sum + dataset.records, 0),
      curricula: datasets.filter((dataset) => dataset.kind === 'curriculum').length,
    },
    datasets,
  };
  fs.mkdirSync(outputRoot, { recursive: true });
  fs.writeFileSync(path.join(outputRoot, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  return manifest;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const years = yearsFor(options);
  const collectedAt = new Date().toISOString();
  const credentials = readCredentials();
  fs.mkdirSync(options.outputRoot, { recursive: true });

  log(`archive root: ${options.outputRoot}`);
  log(`scope: years=${years.join(',')} terms=${options.terms.join(',')}`);
  const systemChrome = '/usr/bin/google-chrome';
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.DREAMS_BROWSER_EXECUTABLE
      || (fs.existsSync(systemChrome) ? systemChrome : undefined),
  });
  const context = await browser.newContext();
  await context.route('**/*', async (route) => {
    const type = route.request().resourceType();
    if (['image', 'font', 'media', 'stylesheet'].includes(type)) await route.abort();
    else await route.continue();
  });
  const controlPage = await context.newPage();

  try {
    await login(controlPage, credentials);
    const academicUnits = await collectAcademicUnits(controlPage, years);

    if (!options.skipCurricula) {
      for (const year of years) {
        await collectCurriculum(
          controlPage,
          options.outputRoot,
          year,
          academicUnits.get(year) || [],
          collectedAt,
          options.force,
        );
      }
    }

    if (!options.skipTerms) {
      for (const year of years) {
        for (const term of options.terms) {
          await collectTerm(
            context,
            options.outputRoot,
            year,
            term,
            academicUnits.get(year) || [],
            collectedAt,
            options,
          );
        }
      }
    }

    if (!options.skipRelations) {
      await collectRelations(controlPage, options.outputRoot, collectedAt, options.force);
    }
    const manifest = buildManifest(options.outputRoot, years, options.terms, collectedAt);
    log(`manifest saved: ${manifest.totals.sectionTermRecords} section-term records`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exitCode = 1;
});

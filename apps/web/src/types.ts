export const DAYS = ['월', '화', '수', '목', '금', '토'] as const
export type Day = (typeof DAYS)[number]
export type CourseRole = 'must' | 'want' | 'backup' | 'exclude'

export interface Session {
  day: Day
  start: string
  end: string
  room: string | null
  building: string | null
}

export interface Section {
  id: string
  courseCode: string
  sectionCode: string
  name: string
  professor: string | null
  category: string
  credits: number
  rawTime: string | null
  sessions: Session[]
}

export interface Catalog {
  schemaVersion: number
  semester: string
  dataVersion: string
  updatedAt: string
  source: { label: string; url: string }
  sections: Section[]
}

export interface PlanItem {
  sectionId: string
  role: CourseRole
  locked: boolean
}

export interface Preferences {
  targetCredits: number
  minCredits: number
  maxCredits: number
  preferredFreeDays: Day[]
  avoidBefore: string | null
  avoidAfter: string | null
  minLunchMinutes: number
  maxDailyMinutes: number
  compactness: number
  minimizeChanges: boolean
}

export interface DraftSnapshot {
  schemaVersion: 1
  semester: string
  dataVersion: string | null
  items: PlanItem[]
  preferences: Preferences
  updatedAt: string
}

export interface ConflictEdge {
  leftId: string
  rightId: string
  leftName: string
  rightName: string
  sessions: [Session, Session]
}

export interface PlanMetrics {
  credits: number
  campusDays: number
  totalGapMinutes: number
  earliest: string | null
  latest: string | null
  dailyMinutes: Partial<Record<Day, number>>
}

export interface Candidate {
  id: string
  rank: number
  status: 'OPTIMAL' | 'FEASIBLE'
  sectionIds: string[]
  score: number
  reasons: string[]
  unmetPreferences: string[]
  metrics: PlanMetrics
}

export type OptimizationStatus = 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'INFEASIBLE' | 'TIME_LIMIT' | 'CANCELLED' | 'FAILED'

export interface OptimizationJob {
  id: string
  status: OptimizationStatus
  message?: string
  candidates: Candidate[]
  relaxationSuggestions: string[]
}

export interface CommonRule {
  id: string
  admissionYears?: { start?: number; end?: number }
  scope: Record<string, string>
  kind: string
  min?: number
  max?: number
  unit?: string
  operator?: string
  courses?: Array<{ name: string; credits: number }>
  values?: Record<string, number>
  components?: Record<string, number>
  requiresManualReview?: boolean
  sourceRefs: string[]
}

export interface CommonRules {
  schemaVersion: number
  asOf: string
  resultLabel: string
  statuses: string[]
  rules: CommonRule[]
  manualReviewReasons: string[]
}

export interface DepartmentSource {
  college: string
  academicUnit: string
  unitType: string
  curriculumUrl: string | null
  curriculumStatus: string
  graduationUrl: string | null
  majorRequiredStatus: string
  prerequisiteStatus: string
  transitionNote: string | null
  handbookPage: number | null
}

export interface DepartmentSources {
  schemaVersion: number
  asOf: string
  source: string
  departments: DepartmentSource[]
}

export type EntryType = 'FRESHMAN' | 'TRANSFER'
export type SectionGroup = 'ODD' | 'EVEN' | 'UNKNOWN'
export type StudentClassification = 'DOMESTIC' | 'INTERNATIONAL' | 'UNKNOWN'

export interface AcademicProfile {
  schemaVersion: 1
  department: string
  admissionYear: number
  currentGrade: 1 | 2 | 3 | 4
  entryType: EntryType
  studentType: StudentClassification
  sectionGroup: SectionGroup
  updatedAt: string
}

export interface MajorRequiredCourse {
  courseCode: string
  name: string
  grade: number | null
  semesters: number[]
  handbookPage: number
}

export interface MajorRequiredProgram {
  academicUnit: string
  status: 'AVAILABLE' | 'MANUAL_REVIEW'
  manualReviewReason: string | null
  handbookPages: number[]
  courses: MajorRequiredCourse[]
}

export interface MajorRequiredCourses {
  schemaVersion: number
  asOf: string
  cohortAdmissionYear: number
  source: string
  method: string
  programs: MajorRequiredProgram[]
}

export interface AuthSession {
  available: boolean
  authenticated: boolean
  studentNumber: string | null
  expiresAt: string | null
}

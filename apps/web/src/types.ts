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
  professorLocked?: boolean
}

export interface Preferences {
  targetCredits: number
  minCredits: number
  maxCredits: number
  preferredFreeDays: Day[]
  excludedDays: Day[]
  avoidBefore: string | null
  avoidAfter: string | null
  hardStart: string | null
  hardEnd: string | null
  maxGapMinutes: number | null
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

export interface AcademicBasis {
  admissionYear: number
  entryType: EntryType
  studentType: StudentClassification
  sectionGroup: SectionGroup
  gradeMismatchAcknowledged?: boolean
}

export interface AcademicProfile {
  schemaVersion: 2
  department: string
  currentGrade: 1 | 2 | 3 | 4
  academicBasis: AcademicBasis | null
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

export interface UserInfo {
  id: string
  studentNumber: string
  name: string | null
  grade: number | null
  department: string | null
  admissionYear: number | null
  entryType: EntryType | null
  studentType: StudentClassification | null
  sectionGroup: SectionGroup | null
  majorPath: 'ADVANCED_MAJOR' | 'DOUBLE_MAJOR' | 'MINOR' | 'MICRO_MAJOR' | null
  profileCompleted: boolean
  createdAt: string
  updatedAt: string
}

export interface PrivacyConsent {
  id: string
  consentVersion: string
  agreed: boolean
  agreedAt: string
}

export interface SavedTimetable {
  id: string
  name: string
  semester: string
  dataVersion: string | null
  items: PlanItem[]
  preferences: Preferences
  favorite: boolean
  createdAt: string
  updatedAt: string
}

export interface SavedTimetableDetail {
  timetable: SavedTimetable
  sections: Section[]
  metrics: { credits: number; campusDays: number; gapMinutes: number }
  conflictSectionIds: [string, string][]
}

export interface RatingSummary {
  averageRating: number
  reviewCount: number
  popularityScore: number
}

export interface CourseStats extends RatingSummary {
  courseCode: string
  name: string
  category: string
  credits: number
  grade: number | null
  sectionCount: number
  professors: string[]
}

export interface CourseReview {
  id: string
  courseCode: string
  courseName: string
  professor: string | null
  semester: string
  rating: number
  content: string
  mine: boolean
  createdAt: string
  updatedAt: string
}

export type CompletedCourseStatus = 'IN_PROGRESS' | 'COMPLETED'

export interface CompletedCourse {
  id: string
  historicalOfferingId: string | null
  courseCode: string | null
  sectionCode: string | null
  courseName: string
  credits: number
  category: string
  area: string | null
  semester: string | null
  status: CompletedCourseStatus
  inputSource: 'MANUAL' | 'CURRENT_TIMETABLE' | 'HISTORICAL_TIMETABLE'
  createdAt: string
  updatedAt: string
}

export interface CreditSummary {
  totalCredits: number
  majorCredits: number
  liberalCredits: number
  areaCredits: Record<string, number>
}

export interface HistoricalSemester {
  semester: string
  academicYear: number
  termCode: string
  termName: string
  dataStatus: string
  courseCount: number
  collectedAt: string
}

export interface HistoricalCourseOffering {
  id: string
  semester: string
  academicYear: number
  termCode: string
  courseCode: string
  sectionCode: string
  koreanName: string
  englishName: string | null
  professorName: string | null
  completionCategory: string | null
  credits: number | null
  lectureHours: number | null
  practiceHours: number | null
  rawLectureTime: string | null
  rawLocation: string | null
  targetGrade: string | null
  listingStatus: string | null
  detailStatus: string | null
  categoryContexts: Array<Record<string, unknown>>
  departmentContexts: Array<Record<string, unknown>>
}

export interface HistoricalCourseDetail extends HistoricalCourseOffering {
  rawPayload: Record<string, unknown>
}

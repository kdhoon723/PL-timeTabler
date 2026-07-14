import { useEffect, useState } from 'react'
import { loadSharedTimetable } from '../api/client'
import type { DraftSnapshot, SavedTimetable } from '../types'

interface Props {
  code: string
  onBack: () => void
  onLoad: (draft: DraftSnapshot) => void
}

export function SharedTimetablePage({ code, onBack, onLoad }: Props) {
  const [timetable, setTimetable] = useState<SavedTimetable | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { loadSharedTimetable(code).then(({ timetable: loaded }) => setTimetable(loaded)).catch((caught) => setError(caught instanceof Error ? caught.message : '공유 시간표를 불러오지 못했습니다.')) }, [code])
  return <main className="shared-page"><header className="page-header"><button type="button" className="text-button" onClick={onBack}>← 내 시간표로</button><div><h1>공유받은 시간표</h1><p>내용을 확인한 뒤 내 편집기로 복사할 수 있습니다.</p></div></header>{error ? <div className="global-error" role="alert">{error}</div> : !timetable ? <p>시간표를 불러오는 중입니다…</p> : <section className="mypage-section"><h2>{timetable.name}</h2><p>{timetable.semester} · {timetable.items.filter((item) => item.role === 'must' || item.role === 'want').length}과목</p><button type="button" className="primary-button" onClick={() => onLoad({ schemaVersion: 1, semester: timetable.semester, dataVersion: timetable.dataVersion, items: timetable.items, preferences: timetable.preferences, updatedAt: timetable.updatedAt })}>내 편집기로 복사</button></section>}</main>
}

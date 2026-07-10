import type { PlanItem, Section } from '../types'

interface Props { items: PlanItem[]; sectionById: Map<string, Section>; onApplyBackup: (section: Section) => void; onMessage: (message: string) => void }

export function RegistrationChecklist({ items, sectionById, onApplyBackup, onMessage }: Props) {
  const active = items.filter((item) => item.role === 'must' || item.role === 'want').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section)
  const backups = items.filter((item) => item.role === 'backup').map((item) => sectionById.get(item.sectionId)).filter((section): section is Section => !!section)
  const copy = async () => {
    const lines = active.map((section, index) => `${index + 1}. ${section.courseCode}-${section.sectionCode} ${section.name} (${section.professor ?? '교수 미정'})`)
    if (backups.length) lines.push('', '[예비]', ...backups.map((section) => `- ${section.courseCode}-${section.sectionCode} ${section.name}`))
    await navigator.clipboard.writeText(lines.join('\n'))
    onMessage('수강신청 체크리스트를 복사했습니다.')
  }
  return <section className="checklist-panel" aria-labelledby="checklist-title">
    <div className="section-heading"><div><h2 id="checklist-title">수강신청 준비</h2><p>실패에 대비해 예비 과목을 미리 지정해 두세요.</p></div></div>
    <ol className="checklist">{active.map((section) => <li key={section.id}><span><strong>{section.courseCode}-{section.sectionCode}</strong>{section.name}</span><small>{section.professor ?? '교수 미정'}</small></li>)}</ol>
    {backups.length > 0 && <div className="backup-list"><h3>예비 과목</h3>{backups.map((section) => <div key={section.id}><span><strong>{section.name}</strong><small>{section.courseCode}-{section.sectionCode}</small></span><button type="button" onClick={() => onApplyBackup(section)}>시간표에 적용</button></div>)}</div>}
    <button type="button" className="secondary-button full-button" onClick={copy} disabled={!active.length}>과목코드·분반 복사</button>
  </section>
}

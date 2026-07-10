import type { ConflictEdge } from '../types'
import { formatSession } from '../domain/time'
import { WarningIcon } from './Icons'

interface Props {
  conflicts: ConflictEdge[]
  previewReadOnly?: boolean
  onOpen: (sectionId: string) => void
}

export function ConflictNotice({ conflicts, previewReadOnly = false, onOpen }: Props) {
  if (!conflicts.length) return null
  return <section className={`conflict-notice ${previewReadOnly ? 'preview-read-only' : ''}`} aria-labelledby="conflict-title">
    <div><WarningIcon /><div><h2 id="conflict-title">시간이 겹치는 수업이 있습니다.</h2><p>{previewReadOnly ? '미리보기에서는 충돌만 확인할 수 있습니다. 취소한 뒤 현재 시간표에서 분반을 바꿔 주세요.' : '과목을 선택하면 가능한 다른 분반을 바로 확인할 수 있습니다.'}</p></div></div>
    <ul>{conflicts.map((conflict) => <li key={`${conflict.leftId}-${conflict.rightId}`}>
      <span><strong>{conflict.leftName} ↔ {conflict.rightName}</strong><small>{formatSession(conflict.sessions[0])} / {formatSession(conflict.sessions[1])}</small></span>
      {!previewReadOnly && <button type="button" onClick={() => onOpen(conflict.leftId)}>해결</button>}
    </li>)}</ul>
  </section>
}

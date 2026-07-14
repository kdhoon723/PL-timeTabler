import { useCallback, useEffect, useRef, useState } from 'react'
import { createCourseReview, deleteCourseReview, loadCourseReviews, updateCourseReview } from '../api/client'
import type { AuthSession, CourseReview, RatingSummary, Section } from '../types'
import { useSheetSwipeDismiss } from '../hooks/useSheetSwipeDismiss'
import { CloseIcon } from './Icons'

interface Props {
  section: Section | null
  authSession: AuthSession
  onClose: () => void
  onLogin: () => void
  onChanged: () => void
}

const EMPTY_SUMMARY: RatingSummary = { averageRating: 0, reviewCount: 0, popularityScore: 0 }

export function ReviewSheet({ section, authSession, onClose, onLogin, onChanged }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const [reviews, setReviews] = useState<CourseReview[]>([])
  const [summary, setSummary] = useState<RatingSummary>(EMPTY_SUMMARY)
  const [rating, setRating] = useState(5)
  const [content, setContent] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const open = !!section
  const sheetDrag = useSheetSwipeDismiss(ref, onClose)

  const refresh = useCallback(async () => {
    if (!section) return
    const result = await loadCourseReviews(section.courseCode)
    setReviews(result.reviews)
    setSummary(result.ratingSummary)
  }, [section])

  useEffect(() => {
    if (open && ref.current && !ref.current.open) ref.current.showModal()
    if (!open && ref.current?.open) ref.current.close()
    if (open) refresh().catch(() => setError('리뷰를 불러오지 못했습니다.'))
  }, [open, refresh])
  useEffect(() => {
    setEditingId(null)
    setContent('')
    setRating(5)
    setError(null)
  }, [section?.courseCode])

  const submit = async () => {
    if (!section || !content.trim()) return
    setPending(true); setError(null)
    try {
      if (editingId) await updateCourseReview(editingId, { rating, content: content.trim() })
      else await createCourseReview(section.courseCode, { professor: section.professor, semester: '2026-1', rating, content: content.trim() })
      setEditingId(null); setContent(''); setRating(5)
      await refresh(); onChanged()
    } catch (caught) { setError(caught instanceof Error ? caught.message : '리뷰를 저장하지 못했습니다.') }
    finally { setPending(false) }
  }

  const remove = async (review: CourseReview) => {
    setPending(true); setError(null)
    try { await deleteCourseReview(review.id); await refresh(); onChanged() }
    catch { setError('리뷰를 삭제하지 못했습니다.') }
    finally { setPending(false) }
  }

  return <dialog ref={ref} className="sheet detail-sheet review-sheet" onClose={onClose} onCancel={(event) => { event.preventDefault(); onClose() }} aria-labelledby="review-title">
    <div className="sheet-header" {...sheetDrag}><div><h2 id="review-title">{section?.name ?? '강의'} 리뷰</h2><p>평균 ★ {summary.averageRating.toFixed(1)} · 리뷰 {summary.reviewCount}개</p></div><button type="button" className="icon-button" onClick={onClose} aria-label="리뷰 닫기"><CloseIcon /></button></div>
    <div className="review-content">
      {authSession.authenticated ? <section className="review-form" aria-label={editingId ? '리뷰 수정' : '리뷰 작성'}>
        <label><span>별점</span><select value={rating} onChange={(event) => setRating(Number(event.target.value))}>{[5, 4, 3, 2, 1].map((value) => <option value={value} key={value}>{value}점</option>)}</select></label>
        <label><span>내용</span><textarea rows={3} maxLength={2000} value={content} onChange={(event) => setContent(event.target.value)} placeholder={`${section?.professor ?? '담당 교수'} 강의 후기를 작성해 주세요.`} /></label>
        <div className="review-form-actions">{editingId && <button type="button" className="text-button" onClick={() => { setEditingId(null); setContent(''); setRating(5) }}>수정 취소</button>}<button type="button" className="primary-button" disabled={pending || !content.trim()} onClick={submit}>{editingId ? '리뷰 수정' : '리뷰 등록'}</button></div>
      </section> : <div className="login-required"><p>리뷰 작성은 학교 이메일 로그인이 필요합니다.</p><button type="button" className="primary-button" onClick={onLogin}>로그인</button></div>}
      {error && <p className="inline-error" role="alert">{error}</p>}
      <section className="review-list" aria-label="리뷰 목록">{reviews.length ? reviews.map((review) => <article key={review.id}><div><strong>★ {review.rating} · {review.professor ?? '교수 미정'}</strong><small>{review.semester} · {new Date(review.updatedAt).toLocaleDateString('ko-KR')}</small></div><p>{review.content}</p>{review.mine && <div><button type="button" className="text-button" onClick={() => { setEditingId(review.id); setRating(review.rating); setContent(review.content) }}>수정</button><button type="button" className="text-button danger-text" disabled={pending} onClick={() => remove(review)}>삭제</button></div>}</article>) : <p className="empty-copy">아직 작성된 리뷰가 없습니다.</p>}</section>
    </div>
  </dialog>
}

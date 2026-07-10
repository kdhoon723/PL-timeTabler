import { useEffect, useRef, useState } from 'react'
import { logoutAuthSession, startEmailOtp, verifyEmailOtp } from '../api/client'
import type { AuthSession } from '../types'
import { CloseIcon } from './Icons'

interface Props {
  open: boolean
  session: AuthSession
  onClose: () => void
  onSession: (session: AuthSession) => void
}

export function AuthSheet({ open, session, onClose, onSession }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const [studentNumber, setStudentNumber] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'NUMBER' | 'OTP'>('NUMBER')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (open && ref.current && !ref.current.open) ref.current.showModal()
    if (!open && ref.current?.open) ref.current.close()
  }, [open])
  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setInterval(() => setCooldown((value) => Math.max(0, value - 1)), 1_000)
    return () => window.clearInterval(timer)
  }, [cooldown])

  const requestOtp = async () => {
    if (!/^\d{6,12}$/.test(studentNumber)) { setError('학번을 숫자 6~12자리로 입력해 주세요.'); return }
    setPending(true); setError(null)
    try {
      const response = await startEmailOtp(studentNumber)
      setStep('OTP'); setMessage(response.message); setCooldown(60)
    } catch { setError('인증 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.') }
    finally { setPending(false) }
  }
  const verify = async () => {
    if (!/^\d{6}$/.test(code)) { setError('인증번호 6자리를 입력해 주세요.'); return }
    setPending(true); setError(null)
    try { onSession(await verifyEmailOtp(studentNumber, code)); setMessage(null); onClose() }
    catch (caught) { setError(caught instanceof Error ? caught.message : '인증번호를 확인해 주세요.') }
    finally { setPending(false) }
  }
  const logout = async () => {
    setPending(true); setError(null)
    try { await logoutAuthSession(); onSession({ available: session.available, authenticated: false, studentNumber: null, expiresAt: null }); setStep('NUMBER'); onClose() }
    catch { setError('로그아웃하지 못했습니다.') }
    finally { setPending(false) }
  }

  return <dialog ref={ref} className="sheet detail-sheet auth-sheet" onClose={onClose} onCancel={(event) => { event.preventDefault(); onClose() }} aria-labelledby="auth-title">
    <div className="sheet-header"><div><h2 id="auth-title">학교 이메일 로그인</h2><p>비밀번호 없이 인증번호로 로그인합니다.</p></div><button type="button" className="icon-button" onClick={onClose} aria-label="로그인 닫기"><CloseIcon /></button></div>
    {session.authenticated ? <div className="auth-content"><span className="status success">인증됨</span><h3>{session.studentNumber}@daejin.ac.kr</h3><p>학교 이메일 인증 상태입니다. 시간표는 현재 브라우저에 계속 저장됩니다.</p><button type="button" className="secondary-button full-button" disabled={pending} onClick={logout}>로그아웃</button>{error && <p className="inline-error" role="alert">{error}</p>}</div> : <div className="auth-content">
      {step === 'NUMBER' ? <><label><span>학번</span><div className="email-input"><input autoFocus inputMode="numeric" autoComplete="username" value={studentNumber} onChange={(event) => setStudentNumber(event.target.value.replace(/\D/g, '').slice(0, 12))} placeholder="학번 입력" aria-describedby="school-email-preview" /><span>@daejin.ac.kr</span></div><small id="school-email-preview">{studentNumber || '학번'}@daejin.ac.kr로 인증번호를 보냅니다.</small></label><button type="button" className="primary-button full-button" disabled={pending} onClick={requestOtp}>{pending ? '요청 중…' : '인증번호 받기'}</button></> : <><button type="button" className="text-button auth-back" onClick={() => { setStep('NUMBER'); setError(null); setMessage(null) }}>← 학번 다시 입력</button><label><span>인증번호 6자리</span><input className="otp-input" autoFocus inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" /></label>{message && <p className="auth-message">{message}</p>}<button type="button" className="primary-button full-button" disabled={pending || code.length !== 6} onClick={verify}>{pending ? '확인 중…' : '로그인'}</button><button type="button" className="text-button resend-button" disabled={pending || cooldown > 0} onClick={requestOtp}>{cooldown > 0 ? `${cooldown}초 후 다시 받기` : '인증번호 다시 받기'}</button></>}
      {error && <p className="inline-error" role="alert">{error}</p>}
      <p className="auth-disclaimer">이 로그인은 학교 이메일 소유 여부만 확인하며, 공식 재학 증명은 아닙니다. 로그인 없이도 시간표를 만들 수 있습니다.</p>
    </div>}
  </dialog>
}

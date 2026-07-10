import type { SVGProps } from 'react'

type Props = SVGProps<SVGSVGElement>
const base = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true }

export const SearchIcon = (props: Props) => <svg {...base} {...props}><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
export const PlusIcon = (props: Props) => <svg {...base} {...props}><path d="M12 5v14M5 12h14"/></svg>
export const CloseIcon = (props: Props) => <svg {...base} {...props}><path d="m6 6 12 12M18 6 6 18"/></svg>
export const LockIcon = (props: Props) => <svg {...base} {...props}><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
export const UnlockIcon = (props: Props) => <svg {...base} {...props}><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 7-2"/></svg>
export const UndoIcon = (props: Props) => <svg {...base} {...props}><path d="m9 7-4 4 4 4"/><path d="M5 11h8a6 6 0 0 1 6 6"/></svg>
export const RedoIcon = (props: Props) => <svg {...base} {...props}><path d="m15 7 4 4-4 4"/><path d="M19 11h-8a6 6 0 0 0-6 6"/></svg>
export const SlidersIcon = (props: Props) => <svg {...base} {...props}><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>
export const CheckIcon = (props: Props) => <svg {...base} {...props}><path d="m5 12 4 4L19 6"/></svg>
export const WarningIcon = (props: Props) => <svg {...base} {...props}><path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 18h.01"/></svg>
export const TrashIcon = (props: Props) => <svg {...base} {...props}><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13"/></svg>
export const ShareIcon = (props: Props) => <svg {...base} {...props}><circle cx="18" cy="5" r="2"/><circle cx="6" cy="12" r="2"/><circle cx="18" cy="19" r="2"/><path d="m8 11 8-5M8 13l8 5"/></svg>

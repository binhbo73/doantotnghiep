'use client'

import * as AlertDialog from '@radix-ui/react-alert-dialog'
import { AlertTriangle, Check, Loader2, ShieldAlert, Trash2 } from 'lucide-react'

interface DeleteConfirmDialogProps {
    open: boolean
    title: string
    description: string
    resourceName?: string
    isDeleting?: boolean
    blockedItems?: string[]
    onOpenChange: (open: boolean) => void
    onConfirm: () => void | Promise<void>
}

export function DeleteConfirmDialog({
    open,
    title,
    description,
    resourceName,
    isDeleting = false,
    blockedItems = [],
    onOpenChange,
    onConfirm,
}: DeleteConfirmDialogProps) {
    const isBlocked = blockedItems.length > 0

    return (
        <AlertDialog.Root open={open} onOpenChange={(nextOpen) => !isDeleting && onOpenChange(nextOpen)}>
            <AlertDialog.Portal>
                <AlertDialog.Overlay className="fixed inset-0 z-[100] bg-slate-950/45 backdrop-blur-[2px]" />
                <AlertDialog.Content className="fixed left-1/2 top-1/2 z-[101] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-slate-200 bg-white p-6 shadow-2xl">
                    <div className="flex items-start gap-3">
                        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${isBlocked ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-600'}`}>
                            {isBlocked ? (
                                <ShieldAlert size={20} aria-hidden="true" />
                            ) : (
                                <AlertTriangle size={20} aria-hidden="true" />
                            )}
                        </div>
                        <div className="min-w-0 flex-1">
                            <AlertDialog.Title className="text-base font-bold text-slate-900">
                                {title}
                            </AlertDialog.Title>
                            <AlertDialog.Description className="mt-1 text-sm leading-6 text-slate-600">
                                {description}
                            </AlertDialog.Description>
                            {resourceName && (
                                <p className="mt-3 break-words rounded-md bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-800">
                                    {resourceName}
                                </p>
                            )}
                            {isBlocked && (
                                <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-3">
                                    <p className="text-xs font-semibold text-amber-950">
                                        Cần xử lý các dữ liệu sau trước khi xóa:
                                    </p>
                                    <ul className="mt-2 space-y-1.5">
                                        {blockedItems.map((item) => (
                                            <li key={item} className="flex items-center gap-2 text-sm text-amber-900">
                                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600" />
                                                {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="mt-6 flex justify-end gap-2">
                        {isBlocked ? (
                            <button
                                type="button"
                                onClick={() => onOpenChange(false)}
                                className="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800"
                            >
                                <Check size={16} aria-hidden="true" />
                                Đã hiểu
                            </button>
                        ) : (
                            <>
                                <AlertDialog.Cancel asChild>
                                    <button
                                        type="button"
                                        disabled={isDeleting}
                                        className="h-9 rounded-md border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        Hủy
                                    </button>
                                </AlertDialog.Cancel>
                                <button
                                    type="button"
                                    disabled={isDeleting}
                                    onClick={() => void onConfirm()}
                                    className="inline-flex h-9 items-center gap-2 rounded-md bg-red-600 px-4 text-sm font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {isDeleting ? (
                                        <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                                    ) : (
                                        <Trash2 size={16} aria-hidden="true" />
                                    )}
                                    {isDeleting ? 'Đang xóa...' : 'Xóa'}
                                </button>
                            </>
                        )}
                    </div>
                </AlertDialog.Content>
            </AlertDialog.Portal>
        </AlertDialog.Root>
    )
}

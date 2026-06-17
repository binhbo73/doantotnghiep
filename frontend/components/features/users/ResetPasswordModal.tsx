import React, { useState } from 'react'
import { User } from '@/services/users'

interface ResetPasswordModalProps {
    isOpen: boolean
    onClose: () => void
    onSubmit: (newPassword: string, confirmPassword: string, sendEmail: boolean) => Promise<void>
    targetUser: User | null
    loading?: boolean
}

export function ResetPasswordModal({
    isOpen,
    onClose,
    onSubmit,
    targetUser,
    loading = false,
}: ResetPasswordModalProps) {
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [sendEmail, setSendEmail] = useState(true)
    const [error, setError] = useState<string | null>(null)

    if (!isOpen || !targetUser) return null

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)
        
        if (newPassword.length < 8) {
            setError('Mật khẩu mới phải có ít nhất 8 ký tự')
            return
        }
        
        if (newPassword !== confirmPassword) {
            setError('Mật khẩu xác nhận không khớp')
            return
        }

        try {
            await onSubmit(newPassword, confirmPassword, sendEmail)
            setNewPassword('')
            setConfirmPassword('')
            setSendEmail(true)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Có lỗi xảy ra khi đặt lại mật khẩu')
        }
    }

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
                onClick={onClose}
                style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                }}
            />

            {/* Dialog */}
            <div className="fixed inset-0 flex items-center justify-center z-50 p-4 overflow-y-auto">
                <div
                    className="bg-white rounded-xl shadow-2xl w-full max-w-md my-8"
                    style={{
                        backgroundColor: '#ffffff',
                        borderRadius: '12px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
                    }}
                >
                    <div className="px-6 py-4 border-b flex justify-between items-center" style={{ borderColor: '#dce2f3' }}>
                    <h3 className="text-lg font-semibold text-gray-800">
                        Đặt lại mật khẩu
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    >
                        ✕
                    </button>
                </div>
                
                <form onSubmit={handleSubmit} className="p-6">
                    <p className="text-sm text-gray-600 mb-4">
                        Đặt lại mật khẩu cho người dùng <span className="font-semibold">{targetUser.username}</span> ({targetUser.email}).
                    </p>
                    
                    {error && (
                        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
                            {error}
                        </div>
                    )}

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Mật khẩu mới <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                                required
                                minLength={8}
                                placeholder="Ít nhất 8 ký tự"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Xác nhận mật khẩu mới <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                                required
                                minLength={8}
                            />
                        </div>

                        <div className="flex items-center mt-4">
                            <input
                                type="checkbox"
                                id="sendEmail"
                                checked={sendEmail}
                                onChange={(e) => setSendEmail(e.target.checked)}
                                className="h-4 w-4 rounded border-gray-300 accent-[#b75b00] focus:ring-orange-500"
                            />
                            <label htmlFor="sendEmail" className="ml-2 block text-sm text-gray-700">
                                Gửi email thông báo mật khẩu mới cho người dùng
                            </label>
                        </div>
                    </div>

                    <div className="mt-6 flex justify-end space-x-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-50"
                            disabled={loading}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-[#b75b00] text-white rounded-md hover:bg-[#9d4300] focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50"
                            disabled={loading}
                        >
                            {loading ? 'Đang xử lý...' : 'Xác nhận'}
                        </button>
                    </div>
                </form>
            </div>
            </div>
        </>
    )
}

export default ResetPasswordModal

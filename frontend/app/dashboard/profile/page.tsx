'use client'

/**
 * Personal Profile Page
 * Shows detailed information about the currently logged-in user
 * Uses GET /api/v1/users/me to fetch own profile
 */

import React, { useState, useEffect } from 'react'
import {
    Mail, Calendar, Building, Edit, Clock, Lock,
    User, MapPin, Save, X, CheckCircle, AlertCircle,
    Phone, Info, Eye, EyeOff
} from 'lucide-react'
import { getMyProfile, updateMyProfile, MyProfile, resetUserPassword } from '@/services/users'
import { useAuthContext } from '@/context'

// ─── Types ────────────────────────────────────────────────────────────────────

interface EditForm {
    full_name: string
    address: string
    birthday: string
    phone: string
}

interface ChangePasswordForm {
    new_password: string
    confirm_password: string
    send_email: boolean
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getInitials(name: string): string {
    if (!name) return 'U'
    return name.split(' ').slice(0, 2).map(p => p.charAt(0)).join('').toUpperCase()
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return 'Chưa cập nhật'
    return new Date(dateStr).toLocaleDateString('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    })
}

function formatDateTime(dateStr: string | null): string {
    if (!dateStr) return 'Chưa đăng nhập'
    return new Date(dateStr).toLocaleString('vi-VN', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    })
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Avatar({ name, src, size = 96 }: { name: string; src?: string | null; size?: number }) {
    const initials = getInitials(name)
    if (src) {
        return (
            <img
                src={src}
                alt={name}
                className="rounded-full object-cover flex-shrink-0"
                style={{ width: size, height: size }}
            />
        )
    }
    return (
        <div
            className="rounded-full flex items-center justify-center font-bold text-white flex-shrink-0"
            style={{
                width: size, height: size,
                background: 'linear-gradient(135deg, #0058be, #003d82)',
                fontSize: size * 0.35,
            }}
        >
            {initials}
        </div>
    )
}

function Toast({ type, message, onClose }: { type: 'success' | 'error'; message: string; onClose: () => void }) {
    const isSuccess = type === 'success'
    return (
        <div
            className="fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-4 rounded-xl shadow-xl border"
            style={{
                backgroundColor: isSuccess ? '#f0fdf4' : '#fff1f2',
                borderColor: isSuccess ? '#bbf7d0' : '#fecdd3',
                color: isSuccess ? '#15803d' : '#be123c',
                minWidth: 300,
                animation: 'slideIn 0.3s ease'
            }}
        >
            {isSuccess ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
            <span className="text-sm font-medium flex-1">{message}</span>
            <button onClick={onClose} className="opacity-60 hover:opacity-100 transition-opacity">
                <X size={16} />
            </button>
        </div>
    )
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
    return (
        <div className="flex items-start gap-3 py-3 border-b last:border-0" style={{ borderColor: '#f0f3ff' }}>
            <span className="mt-0.5 flex-shrink-0" style={{ color: '#0058be' }}>{icon}</span>
            <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wider mb-0.5" style={{ color: '#8c97b0' }}>{label}</p>
                <p className="text-sm font-medium truncate" style={{ color: '#151c27' }}>{value || 'Chưa cập nhật'}</p>
            </div>
        </div>
    )
}

// ─── Edit Profile Modal ───────────────────────────────────────────────────────

function EditProfileModal({
    profile,
    onClose,
    onSaved,
}: {
    profile: MyProfile
    onClose: () => void
    onSaved: (p: MyProfile) => void
}) {
    const [form, setForm] = useState<EditForm>({
        full_name: profile.full_name || '',
        address: profile.address || '',
        birthday: profile.birthday || '',
        phone: (profile.metadata?.phone as string) || '',
    })
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!form.full_name.trim()) {
            setError('Tên không được để trống')
            return
        }
        try {
            setSaving(true)
            setError(null)
            const updated = await updateMyProfile({
                full_name: form.full_name.trim(),
                address: form.address.trim() || undefined,
                birthday: form.birthday || undefined,
                metadata: { ...profile.metadata, phone: form.phone.trim() },
            })
            onSaved(updated)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Cập nhật thất bại')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
            <div className="w-full max-w-md rounded-2xl overflow-hidden shadow-2xl" style={{ backgroundColor: '#fff' }}>
                {/* Header */}
                <div className="px-6 py-5 flex items-center justify-between" style={{ background: 'linear-gradient(135deg, #0058be, #003d82)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
                            <Edit size={18} className="text-white" />
                        </div>
                        <h2 className="text-base font-semibold text-white">Chỉnh sửa hồ sơ</h2>
                    </div>
                    <button onClick={onClose} className="text-white/70 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {error && (
                        <div className="p-3 rounded-lg text-sm flex items-center gap-2" style={{ backgroundColor: '#fff1f2', color: '#be123c' }}>
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}

                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: '#584237' }}>
                            Họ và tên <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={form.full_name}
                            onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                            className="w-full px-3 py-2.5 rounded-lg text-sm border outline-none transition-all focus:ring-2"
                            style={{ borderColor: '#dce2f3', color: '#151c27' }}
                            placeholder="Nhập họ và tên..."
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: '#584237' }}>
                            Số điện thoại
                        </label>
                        <input
                            type="tel"
                            value={form.phone}
                            onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                            className="w-full px-3 py-2.5 rounded-lg text-sm border outline-none transition-all"
                            style={{ borderColor: '#dce2f3', color: '#151c27' }}
                            placeholder="Nhập số điện thoại..."
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: '#584237' }}>
                            Ngày sinh
                        </label>
                        <input
                            type="date"
                            value={form.birthday}
                            onChange={e => setForm(f => ({ ...f, birthday: e.target.value }))}
                            className="w-full px-3 py-2.5 rounded-lg text-sm border outline-none transition-all"
                            style={{ borderColor: '#dce2f3', color: '#151c27' }}
                            max={new Date().toISOString().split('T')[0]}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: '#584237' }}>
                            Địa chỉ
                        </label>
                        <textarea
                            value={form.address}
                            onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
                            className="w-full px-3 py-2.5 rounded-lg text-sm border outline-none transition-all resize-none"
                            style={{ borderColor: '#dce2f3', color: '#151c27' }}
                            placeholder="Nhập địa chỉ..."
                            rows={3}
                        />
                    </div>

                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-2.5 rounded-lg text-sm font-medium border transition-all hover:bg-gray-50"
                            style={{ borderColor: '#dce2f3', color: '#424754' }}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white transition-all hover:shadow-lg disabled:opacity-50 flex items-center justify-center gap-2"
                            style={{ background: 'linear-gradient(135deg, #0058be, #003d82)' }}
                        >
                            {saving ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <Save size={16} />
                            )}
                            {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

// ─── Change Password Modal ────────────────────────────────────────────────────

function ChangePasswordModal({
    accountId,
    onClose,
    onSuccess,
}: {
    accountId: string
    onClose: () => void
    onSuccess: (msg: string) => void
}) {
    const [form, setForm] = useState<ChangePasswordForm>({
        new_password: '',
        confirm_password: '',
        send_email: true,
    })
    const [showPass, setShowPass] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (form.new_password.length < 8) {
            setError('Mật khẩu phải có ít nhất 8 ký tự')
            return
        }
        if (form.new_password !== form.confirm_password) {
            setError('Mật khẩu xác nhận không khớp')
            return
        }
        try {
            setSaving(true)
            setError(null)
            const res = await resetUserPassword(accountId, {
                new_password: form.new_password,
                confirm_password: form.confirm_password,
                send_email: form.send_email,
            })
            onSuccess(res.note || 'Mật khẩu đã được cập nhật thành công')
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Đổi mật khẩu thất bại')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
            <div className="w-full max-w-md rounded-2xl overflow-hidden shadow-2xl" style={{ backgroundColor: '#fff' }}>
                {/* Header */}
                <div className="px-6 py-5 flex items-center justify-between" style={{ background: 'linear-gradient(135deg, #9d4300, #783200)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
                            <Lock size={18} className="text-white" />
                        </div>
                        <h2 className="text-base font-semibold text-white">Đổi mật khẩu</h2>
                    </div>
                    <button onClick={onClose} className="text-white/70 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {error && (
                        <div className="p-3 rounded-lg text-sm flex items-center gap-2" style={{ backgroundColor: '#fff1f2', color: '#be123c' }}>
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}

                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: '#584237' }}>
                            Mật khẩu mới <span className="text-red-500">*</span>
                        </label>
                        <div className="relative">
                            <input
                                type={showPass ? 'text' : 'password'}
                                value={form.new_password}
                                onChange={e => setForm(f => ({ ...f, new_password: e.target.value }))}
                                className="w-full px-3 py-2.5 pr-10 rounded-lg text-sm border outline-none transition-all"
                                style={{ borderColor: '#dce2f3', color: '#151c27' }}
                                placeholder="Tối thiểu 8 ký tự..."
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowPass(s => !s)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 opacity-50 hover:opacity-80"
                            >
                                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold mb-1.5" style={{ color: '#584237' }}>
                            Xác nhận mật khẩu <span className="text-red-500">*</span>
                        </label>
                        <input
                            type={showPass ? 'text' : 'password'}
                            value={form.confirm_password}
                            onChange={e => setForm(f => ({ ...f, confirm_password: e.target.value }))}
                            className="w-full px-3 py-2.5 rounded-lg text-sm border outline-none transition-all"
                            style={{ borderColor: '#dce2f3', color: '#151c27' }}
                            placeholder="Nhập lại mật khẩu..."
                            required
                        />
                    </div>

                    <label className="flex items-center gap-3 cursor-pointer py-2">
                        <input
                            type="checkbox"
                            checked={form.send_email}
                            onChange={e => setForm(f => ({ ...f, send_email: e.target.checked }))}
                            className="w-4 h-4 rounded"
                        />
                        <span className="text-sm" style={{ color: '#424754' }}>Gửi email thông báo</span>
                    </label>

                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-2.5 rounded-lg text-sm font-medium border transition-all hover:bg-gray-50"
                            style={{ borderColor: '#dce2f3', color: '#424754' }}
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white transition-all hover:shadow-lg disabled:opacity-50 flex items-center justify-center gap-2"
                            style={{ background: 'linear-gradient(135deg, #9d4300, #783200)' }}
                        >
                            {saving ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <Lock size={16} />
                            )}
                            {saving ? 'Đang lưu...' : 'Cập nhật mật khẩu'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

// ─── Skeleton loader ──────────────────────────────────────────────────────────

function Skeleton() {
    return (
        <main className="min-h-screen p-6" style={{ backgroundColor: '#f4f6fb' }}>
            <div className="max-w-3xl mx-auto space-y-4">
                <div className="h-8 w-40 rounded-lg bg-gray-200 animate-pulse" />
                <div className="h-56 rounded-2xl bg-gray-200 animate-pulse" />
                <div className="h-72 rounded-2xl bg-gray-200 animate-pulse" />
            </div>
        </main>
    )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ProfilePage() {
    const { user: authUser, isLoading: authLoading } = useAuthContext()

    const [profile, setProfile] = useState<MyProfile | null>(null)
    const [loading, setLoading] = useState(true)
    const [fetchError, setFetchError] = useState<string | null>(null)
    const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

    const [showEditModal, setShowEditModal] = useState(false)
    const [showPasswordModal, setShowPasswordModal] = useState(false)

    const showToast = (type: 'success' | 'error', message: string) => {
        setToast({ type, message })
        setTimeout(() => setToast(null), 4000)
    }

    // Fetch own profile
    useEffect(() => {
        if (authLoading) return
        const fetch = async () => {
            try {
                setLoading(true)
                setFetchError(null)
                const data = await getMyProfile()
                setProfile(data)
            } catch (err) {
                setFetchError(err instanceof Error ? err.message : 'Không thể tải hồ sơ')
            } finally {
                setLoading(false)
            }
        }
        fetch()
    }, [authLoading])

    if (loading || authLoading) return <Skeleton />

    if (fetchError || !profile) {
        return (
            <main className="min-h-screen p-6 flex items-center justify-center" style={{ backgroundColor: '#f4f6fb' }}>
                <div className="text-center">
                    <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
                        <AlertCircle size={32} className="text-red-500" />
                    </div>
                    <h2 className="text-lg font-semibold mb-2" style={{ color: '#151c27' }}>Không thể tải hồ sơ</h2>
                    <p className="text-sm mb-4" style={{ color: '#8c97b0' }}>{fetchError}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 rounded-lg text-sm text-white font-medium"
                        style={{ backgroundColor: '#0058be' }}
                    >
                        Thử lại
                    </button>
                </div>
            </main>
        )
    }

    const phone = profile.metadata?.phone as string | undefined

    return (
        <>
            {/* Toast */}
            {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}

            <main className="min-h-screen p-6" style={{ backgroundColor: '#f4f6fb' }}>
                <div className="max-w-3xl mx-auto space-y-5">

                    {/* Page title */}
                    <div>
                        <h1 className="text-xl font-bold" style={{ color: '#151c27' }}>Hồ sơ cá nhân</h1>
                        <p className="text-sm mt-0.5" style={{ color: '#8c97b0' }}>Xem và cập nhật thông tin tài khoản của bạn</p>
                    </div>

                    {/* Profile Hero Card */}
                    <div className="rounded-2xl overflow-hidden shadow-sm border" style={{ borderColor: '#dce2f3', backgroundColor: '#fff' }}>
                        {/* Banner */}
                        <div className="h-28 relative" style={{ background: 'linear-gradient(135deg, #0058be 0%, #003d82 50%, #001f5b 100%)' }}>
                            <div className="absolute inset-0 opacity-20"
                                style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, #60a5fa 0%, transparent 50%), radial-gradient(circle at 80% 20%, #818cf8 0%, transparent 40%)' }}
                            />
                        </div>

                        {/* Avatar + Info */}
                        <div className="px-6 pb-6 relative z-10">
                            <div className="flex items-end gap-4 mb-4">
                                <div className="ring-4 ring-white rounded-full shadow-lg bg-white -mt-12 shrink-0">
                                    <Avatar name={profile.full_name} src={profile.avatar_url} size={88} />
                                </div>
                                <div className="mb-1 flex-1">
                                    <h2 className="text-xl font-bold" style={{ color: '#151c27' }}>{profile.full_name}</h2>
                                    <p className="text-sm" style={{ color: '#8c97b0' }}>@{profile.username}</p>
                                </div>
                                <div className="mb-1 flex gap-2">
                                    <button
                                        onClick={() => setShowEditModal(true)}
                                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all hover:shadow-md"
                                        style={{ background: 'linear-gradient(135deg, #0058be, #003d82)' }}
                                    >
                                        <Edit size={15} />
                                        Chỉnh sửa
                                    </button>
                                    <button
                                        onClick={() => setShowPasswordModal(true)}
                                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border transition-all hover:bg-gray-50"
                                        style={{ borderColor: '#dce2f3', color: '#424754' }}
                                    >
                                        <Lock size={15} />
                                        Đổi mật khẩu
                                    </button>
                                </div>
                            </div>

                            {/* Email badge */}
                            <div className="flex items-center gap-2">
                                <span
                                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
                                    style={{ backgroundColor: '#eff4ff', color: '#0058be' }}
                                >
                                    <Mail size={12} />
                                    {profile.email}
                                </span>
                                {profile.department_name && (
                                    <span
                                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
                                        style={{ backgroundColor: '#f0fdf4', color: '#15803d' }}
                                    >
                                        <Building size={12} />
                                        {profile.department_name}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        {/* Personal Info */}
                        <div className="rounded-2xl border shadow-sm p-5" style={{ borderColor: '#dce2f3', backgroundColor: '#fff' }}>
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#eff4ff' }}>
                                    <User size={16} style={{ color: '#0058be' }} />
                                </div>
                                <h3 className="text-sm font-bold" style={{ color: '#151c27' }}>Thông tin cá nhân</h3>
                            </div>

                            <div className="space-y-0">
                                <InfoRow icon={<User size={15} />} label="Họ và tên" value={profile.full_name} />
                                <InfoRow icon={<Mail size={15} />} label="Email" value={profile.email} />
                                <InfoRow icon={<Phone size={15} />} label="Điện thoại" value={phone || ''} />
                                <InfoRow icon={<Calendar size={15} />} label="Ngày sinh" value={formatDate(profile.birthday)} />
                                <InfoRow icon={<MapPin size={15} />} label="Địa chỉ" value={profile.address || ''} />
                            </div>
                        </div>

                        {/* Account Info */}
                        <div className="rounded-2xl border shadow-sm p-5" style={{ borderColor: '#dce2f3', backgroundColor: '#fff' }}>
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#fff7ed' }}>
                                    <Info size={16} style={{ color: '#9d4300' }} />
                                </div>
                                <h3 className="text-sm font-bold" style={{ color: '#151c27' }}>Thông tin tài khoản</h3>
                            </div>

                            <div className="space-y-0">
                                <InfoRow icon={<User size={15} />} label="Tên đăng nhập" value={profile.username} />
                                <InfoRow icon={<Building size={15} />} label="Phòng ban" value={profile.department_name || ''} />
                                <InfoRow icon={<Calendar size={15} />} label="Ngày tạo tài khoản" value={formatDate(profile.created_at)} />
                                <InfoRow icon={<Clock size={15} />} label="Cập nhật lần cuối" value={formatDateTime(profile.updated_at)} />
                            </div>
                        </div>
                    </div>

                    {/* Account ID info (for debugging / transparency) */}
                    <div className="rounded-2xl border shadow-sm p-5" style={{ borderColor: '#dce2f3', backgroundColor: '#fff' }}>
                        <div className="flex items-center gap-2 mb-3">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#f4f6fb' }}>
                                <Info size={16} style={{ color: '#727785' }} />
                            </div>
                            <h3 className="text-sm font-bold" style={{ color: '#151c27' }}>ID tài khoản</h3>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div className="p-3 rounded-lg" style={{ backgroundColor: '#f9f9ff' }}>
                                <p className="text-xs font-semibold mb-1" style={{ color: '#8c97b0' }}>Profile ID</p>
                                <p className="text-xs font-mono break-all" style={{ color: '#424754' }}>{profile.id}</p>
                            </div>
                            <div className="p-3 rounded-lg" style={{ backgroundColor: '#f9f9ff' }}>
                                <p className="text-xs font-semibold mb-1" style={{ color: '#8c97b0' }}>Account ID</p>
                                <p className="text-xs font-mono break-all" style={{ color: '#424754' }}>{profile.account_id}</p>
                            </div>
                        </div>
                    </div>

                </div>
            </main>

            {/* Modals */}
            {showEditModal && (
                <EditProfileModal
                    profile={profile}
                    onClose={() => setShowEditModal(false)}
                    onSaved={(updated) => {
                        setProfile(updated)
                        setShowEditModal(false)
                        showToast('success', 'Cập nhật hồ sơ thành công!')
                    }}
                />
            )}

            {showPasswordModal && (
                <ChangePasswordModal
                    accountId={profile.account_id}
                    onClose={() => setShowPasswordModal(false)}
                    onSuccess={(msg) => {
                        setShowPasswordModal(false)
                        showToast('success', msg)
                    }}
                />
            )}

            <style>{`
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `}</style>
        </>
    )
}

/**
 * User Data Types
 */

export interface UserDetail {
    id: string;
    username: string;
    email: string;
    full_name: string;
    avatar_url?: string;
}

export interface UserProfile {
    id: string;
    user_id: string;
    full_name: string;
    avatar_url?: string;
    phone?: string;
    department_id?: string;
}

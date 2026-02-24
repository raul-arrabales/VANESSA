export type Role = "superadmin" | "admin" | "user";

export type AuthUser = {
  id: number;
  email: string;
  username: string;
  role: Role;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type RegisterPayload = {
  email: string;
  username: string;
  password: string;
  role?: Role;
};

export type RegisterResult = {
  user: AuthUser;
};

export type LoginResult = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};

export type MeResult = {
  user: AuthUser;
};

export type ActivateResult = {
  user: AuthUser;
};

export type UsersResult = {
  users: AuthUser[];
};

export type UpdateRoleResult = {
  user: AuthUser;
};

# Local Authentication (On-Prem)

VANESSA backend uses local username/password authentication with JWT bearer tokens.

- No OAuth/Auth0/social login.
- No external identity provider.
- Passwords are hashed with bcrypt.

## Roles

- `superadmin`: full access (can create/activate any role)
- `admin`: admin access (can activate only `user` accounts)
- `user`: standard access

Role hierarchy: `superadmin > admin > user`.

## Auth Flow

1. `POST /auth/register`
- Public self-registration is allowed when `AUTH_ALLOW_SELF_REGISTER=true`.
- Public registration creates role `user` and `is_active=false`.
- Admin/superadmin can create users too; only superadmin can assign elevated roles.

2. `POST /auth/login`
- Accepts `identifier` (email or username) and `password`.
- Inactive users are rejected with `403 account_inactive`.
- Returns bearer token and sanitized user profile.

3. `POST /auth/logout`
- JWT is stateless in v1; endpoint is a contract helper for client-side token discard.

4. `GET /auth/me`
- Requires bearer token.
- Returns current user profile.

5. `POST /auth/users/<id>/activate`
- Requires `admin` or `superadmin`.
- `admin` can activate only `user` role accounts.
- `superadmin` can activate any role.

## Environment Variables

Required / important backend auth settings (see `infra/.env.example`):

- `AUTH_JWT_SECRET`: JWT signing secret. Must be non-empty outside development.
- `AUTH_JWT_ALGORITHM`: default `HS256`.
- `AUTH_ACCESS_TOKEN_TTL_SECONDS`: default `28800` (8 hours).
- `AUTH_ALLOW_SELF_REGISTER`: default `true`.
- `AUTH_BOOTSTRAP_SUPERADMIN_EMAIL`
- `AUTH_BOOTSTRAP_SUPERADMIN_USERNAME`
- `AUTH_BOOTSTRAP_SUPERADMIN_PASSWORD`

## First Superadmin Bootstrap

On a fresh deployment with no users:

1. Set bootstrap env vars:
- `AUTH_BOOTSTRAP_SUPERADMIN_EMAIL`
- `AUTH_BOOTSTRAP_SUPERADMIN_USERNAME`
- `AUTH_BOOTSTRAP_SUPERADMIN_PASSWORD`
2. Start backend once.
3. Backend migrates schema and creates the first `superadmin` automatically.
4. Remove bootstrap password from env after first successful startup.

## Security Notes

- Passwords are never stored in plaintext.
- API responses never include `password_hash`.
- JWT secret must not be hardcoded in source code.
- Keep token lifetime short enough for your operational risk model.

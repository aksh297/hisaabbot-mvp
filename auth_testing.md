# Auth Testing Playbook

## MongoDB Verification
```
mongosh
use hisaabbot
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```
Verify: bcrypt hash starts with `$2b$`, indexes exist on users.email (unique), login_attempts.identifier, password_reset_tokens.expires_at (TTL).

## API Testing
```
API_URL=<REACT_APP_BACKEND_URL>
curl -c cookies.txt -X POST $API_URL/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@hisaabbot.in","password":"admin123"}'
cat cookies.txt
curl -b cookies.txt $API_URL/api/auth/me
```

Login should return the user object and set `access_token` + `refresh_token` cookies. `/me` should return the same user using those cookies.

## Test User
Seeded demo vendor:
- Email: `ramesh@hisaabbot.in`
- Password: `demo123`
- Business: Sharma Textiles, Jaipur
- GSTIN: 08AABCU9603R1ZM

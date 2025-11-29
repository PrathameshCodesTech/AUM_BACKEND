Great question! Let me clear this confusion step-by-step:

## 1. **Database Setup (One-Time Admin Work)**

### Step 1: Create Permissions (Admin does this ONCE)
```
Permission 1: "investments.create"
Permission 2: "investments.approve"  
Permission 3: "properties.create"
Permission 4: "kyc.approve"
...etc
```

### Step 2: Create Roles (Admin does this ONCE)
```
Role 1: "Customer" 
Role 2: "Channel Partner"
Role 3: "Admin"
Role 4: "Developer"
```

### Step 3: Map Roles to Permissions (Admin does this ONCE)
```
RolePermission mapping:
- Customer role → "investments.create" permission
- Admin role → "investments.approve" permission
- Developer role → "properties.create" permission
```

### Step 4: Create User and Assign Role
```
User: John (phone: 1234567890)
Assign: role = "Customer"
```

**Now John has access to ALL permissions linked to "Customer" role!**

***

## 2. **Runtime: How Permission Checking Works**

### When User Logs In:

**Step 1: User sends OTP, verifies, gets JWT token**
```
POST /api/auth/verify-otp/
Response:
{
  "access": "eyJhbGc...",  ← JWT token
  "user": {
    "id": 5,
    "username": "john",
    "role": "Customer"  ← Role is in token
  }
}
```

**The JWT token contains:**
- user_id
- username
- role information (indirectly through user_id)

***

### When User Makes Request:

**Step 2: User sends request with token**
```
POST /api/investments/create/
Headers:
  Authorization: Bearer eyJhbGc...

Body:
  { "property_id": 10, "amount": 50000 }
```

**Step 3: Django validates token and loads user**
```
Django automatically:
1. Reads JWT token
2. Extracts user_id from token
3. Loads User object from database
4. Loads User's role
5. Sets request.user = User object
```

**Step 4: View checks permission**
```python
# In your view
def create_investment(request):
    # request.user is automatically set by JWT
    
    # Check permission
    if not request.user.role.has_permission('investments.create'):
        return Response({'error': 'No permission'}, status=403)
    
    # User has permission, proceed...
```

***

## 3. **Where Permission Checking Happens**

### Option A: In Views (Manual Check)
```python
# investments/views.py
class CreateInvestmentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check permission manually
        if not request.user.has_permission('investments.create'):
            return Response({
                'error': 'You do not have permission to create investments'
            }, status=403)
        
        # User has permission, create investment
        ...
```

### Option B: Custom Permission Class (Reusable)
```python
# accounts/permissions.py
from rest_framework.permissions import BasePermission

class HasInvestmentCreatePermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_permission('investments.create')

# In view:
class CreateInvestmentView(APIView):
    permission_classes = [HasInvestmentCreatePermission]
    
    def post(self, request):
        # Permission already checked by DRF
        # Just proceed with logic
        ...
```

### Option C: Decorator (For function views)
```python
from functools import wraps

def require_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_permission(permission_code):
                return Response({'error': 'No permission'}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage:
@require_permission('investments.create')
def create_investment(request):
    ...
```

***

## 4. **Complete Flow Diagram**

```
1. ADMIN SETUP (One-time)
   ├─ Create Permissions in DB
   ├─ Create Roles in DB  
   ├─ Map Roles ↔ Permissions (RolePermission table)
   └─ Assign Role to User


2. USER LOGIN
   ├─ User sends phone + OTP
   ├─ System verifies OTP
   ├─ System generates JWT token (contains user_id)
   └─ Returns token to user


3. USER MAKES REQUEST
   ├─ User sends: Authorization: Bearer <token>
   ├─ Django JWT middleware validates token
   ├─ Django loads User from DB using user_id in token
   ├─ Django loads User's Role
   └─ Sets request.user = User object (with role)


4. VIEW CHECKS PERMISSION
   ├─ View accesses: request.user
   ├─ Calls: request.user.has_permission('investments.create')
   ├─ System checks: User → Role → RolePermission → Permission
   └─ Returns: True/False


5. SYSTEM RESPONSE
   ├─ If has permission → Execute view logic
   └─ If no permission → Return 403 Forbidden
```

***

## 5. **How `has_permission()` Works Internally**

In your User model, you already have this method:

```python
class User(AbstractUser, TimestampedModel):
    role = models.ForeignKey('Role', ...)
    
    def has_permission(self, permission_code):
        """Check if user has specific permission"""
        if not self.role:
            return False
        
        # Query: User → Role → RolePermission → Permission
        return Permission.objects.filter(
            role_assignments__role=self.role,  # RolePermission table
            code_name=permission_code
        ).exists()
```

**Database query happens:**
```sql
SELECT EXISTS(
    SELECT 1 FROM permissions p
    INNER JOIN role_permissions rp ON rp.permission_id = p.id
    WHERE rp.role_id = <user's role id>
    AND p.code_name = 'investments.create'
)
```

***

## 6. **Real Example**

### Scenario: John wants to create investment

**Database State:**
```
Users table:
id=5, username="john", role_id=1

Roles table:
id=1, name="Customer"

Permissions table:
id=10, code_name="investments.create"

RolePermissions table:
role_id=1, permission_id=10  ← Customer can create investments
```

**Request:**
```
POST /api/investments/create/
Authorization: Bearer eyJ... (John's token)
```

**Flow:**
1. JWT middleware extracts user_id=5 from token
2. Loads User(id=5) → role_id=1
3. View calls: `request.user.has_permission('investments.create')`
4. System queries: RolePermission where role_id=1 AND permission='investments.create'
5. Finds match → Returns True
6. View proceeds to create investment

**If John was "Guest" role (not mapped to permission):**
1-4. Same steps
5. No match found → Returns False
6. View returns 403 Forbidden

***

## 7. **JWT Token Does NOT Contain Permissions**

**Important:** JWT token is lightweight, it only contains:
- user_id
- expiry time
- Maybe role_id

**It does NOT contain the full list of permissions!**

Permissions are checked **on every request** by querying the database:
```
Token → user_id → User table → Role table → RolePermission table → Permission table
```

This ensures:
- If admin changes user's role → Next request will reflect new permissions
- If admin revokes permission from role → Users with that role lose access immediately

***

## Summary:

✅ **Setup (Admin):** Create Permissions → Roles → Map them → Assign role to user

✅ **Login:** User gets JWT token (contains user_id)

✅ **Request:** User sends token → Django loads User → User has Role

✅ **Permission Check:** View checks `request.user.has_permission(code)` → Queries DB → Returns True/False

✅ **Where to check:** In views (before executing business logic)

✅ **How it knows user:** From JWT token → extracts user_id → loads User from DB

Clear now? 😊